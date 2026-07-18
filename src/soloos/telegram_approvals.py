"""Telegram-first approval card delivery and callback handling."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import audit
from .approvals import ApprovalRecord, ApprovalsService
from .config import get_config
from .ids import next_id
from .mission_control import decide_approval

_CALLBACK_PREFIX = "soloos:approval:"
_ACTION_TO_VERDICT = {
    "approve": "approved",
    "reject": "rejected",
    "revise": "deferred",
}
_VERDICT_TO_KOREAN = {
    "approved": "승인",
    "rejected": "반려",
    "deferred": "수정요청",
}


@dataclass(frozen=True)
class TelegramDeliveryResult:
    approval_id: str
    delivery_status: str
    chat_ref: str
    message_ref: str | None
    outbox_path: Path | None = None


@dataclass(frozen=True)
class TelegramCallbackDecision:
    approval_id: str
    action: str
    verdict: str


@dataclass(frozen=True)
class TelegramCallbackResult:
    approval_id: str
    action: str
    verdict: str
    status: str
    snapshot_path: Path
    confirmation_text: str


def build_approval_card(record: ApprovalRecord) -> dict[str, Any]:
    """Build a secret-safe Telegram approval card with CEO decision context."""
    params = record.params or {}
    text = "\n".join(
        [
            "🧾 SoloOS 대표 결재 요청",
            f"Approval ID: {record.id}",
            f"Action: {record.action_type}",
            f"Target: {record.target}",
            f"Requesting: {_first(params, 'requesting_department', 'requesting_agent', default=record.agent_id)}",
            f"Risk: {record.risk}",
            f"Policy: {record.policy_rule}",
            f"Env: {params.get('env', 'production')}",
            f"Cost: {record.cost_krw:,}원",
            f"Mission: {_first(params, 'mission', 'objective', default='-')}",
            f"Summary: {_first(params, 'artifact_summary', 'summary', default='-')}",
            f"Authority limits: {_compact(params.get('authority_limits') or params.get('authority') or '-')}",
            f"KPI / success: {_compact(params.get('kpi') or params.get('success_criteria') or '-')}",
            f"Preview: {record.preview_url or params.get('preview_url') or '-'}",
            f"Evidence: {_first(params, 'evidence_ref', 'audit_ref', default=f'audit:approval:{record.id}')}",
        ]
    )
    return {
        "approval_id": record.id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "승인", "callback_data": f"{_CALLBACK_PREFIX}{record.id}:approve"},
                {"text": "반려", "callback_data": f"{_CALLBACK_PREFIX}{record.id}:reject"},
                {"text": "수정요청", "callback_data": f"{_CALLBACK_PREFIX}{record.id}:revise"},
            ]]
        },
    }


def send_approval_card(record: ApprovalRecord) -> TelegramDeliveryResult:
    """Send a Telegram approval card, or write a local outbox entry when no bot token is configured.

    The outbox path is intentionally used in tests and local dev. It preserves the exact
    Telegram payload without exposing the CEO chat id in DB params or public snapshots.
    """
    cfg = get_config(reload=True)
    card = build_approval_card(record)
    safe_payload = {
        **card,
        "created_at": int(time.time()),
        "delivery_status": "outbox",
        "chat_ref": "ceo_telegram",
    }
    if cfg.telegram_token and cfg.telegram_ceo_chat_id:
        try:
            message_ref = _send_to_telegram_api(cfg.telegram_token, cfg.telegram_ceo_chat_id, card)
            result = TelegramDeliveryResult(record.id, "sent", "ceo_telegram", message_ref, None)
            _audit_delivery(record, result)
            return result
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            safe_payload["delivery_status"] = "send_failed_outbox"

    outbox = cfg.data_dir / "telegram-approval-outbox.jsonl"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    with outbox.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe_payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = TelegramDeliveryResult(record.id, safe_payload["delivery_status"], "ceo_telegram", f"outbox:{outbox.name}", outbox)
    _audit_delivery(record, result)
    return result


def parse_telegram_callback(callback_data: str) -> TelegramCallbackDecision:
    if not callback_data.startswith(_CALLBACK_PREFIX):
        raise ValueError("invalid telegram approval callback")
    tail = callback_data.removeprefix(_CALLBACK_PREFIX)
    approval_id, sep, action = tail.rpartition(":")
    if not sep or not approval_id or action not in _ACTION_TO_VERDICT:
        raise ValueError("invalid telegram approval callback")
    return TelegramCallbackDecision(approval_id=approval_id, action=action, verdict=_ACTION_TO_VERDICT[action])


def handle_telegram_approval_callback(
    callback_data: str,
    *,
    by: str = "ceo:telegram",
    snapshot_path: Path | None = None,
) -> TelegramCallbackResult:
    parsed = parse_telegram_callback(callback_data)
    decision = decide_approval(
        parsed.approval_id,
        parsed.verdict,
        by=by,
        comment=f"Telegram inline decision: {parsed.action}",
        snapshot_path=snapshot_path,
    )
    audit.emit(
        id=next_id("A"),
        actor=f"user:{by}",
        action_type="telegram_approval_callback_decided",
        target=f"approval:{parsed.approval_id}",
        status=decision.status,
        extras={"action": parsed.action, "verdict": parsed.verdict, "snapshot": decision.snapshot_path.name},
    )
    label = _VERDICT_TO_KOREAN[parsed.verdict]
    return TelegramCallbackResult(
        approval_id=parsed.approval_id,
        action=parsed.action,
        verdict=parsed.verdict,
        status=decision.status,
        snapshot_path=decision.snapshot_path,
        confirmation_text=f"{label} 처리 완료 · {parsed.approval_id} · Mission Control snapshot 갱신됨",
    )


def _send_to_telegram_api(token: str, chat_id: str, card: dict[str, Any]) -> str:
    payload = json.dumps({
        "chat_id": chat_id,
        "text": card["text"],
        "reply_markup": card["reply_markup"],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310 - Telegram API endpoint is fixed above.
        data = json.loads(response.read().decode("utf-8"))
    if not data.get("ok"):
        raise ValueError("telegram_send_failed")
    message = data.get("result") or {}
    return f"telegram_message:{message.get('message_id', 'unknown')}"


def _audit_delivery(record: ApprovalRecord, result: TelegramDeliveryResult) -> None:
    audit.emit(
        id=next_id("A"),
        actor="system:soloos",
        action_type="telegram_approval_card_sent",
        target=f"approval:{record.id}",
        status=result.delivery_status,
        policy_rule=record.policy_rule,
        cost_krw=record.cost_krw,
        extras={"chat_ref": result.chat_ref, "message_ref": result.message_ref, "decision_surface": "primary"},
    )


def _first(values: dict[str, Any], *keys: str, default: str) -> str:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _compact(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={val}" for key, val in value.items())
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
