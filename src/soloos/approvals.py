"""Approvals service — the heart of Human-in-the-Loop."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from . import audit
from .db import connect
from .ids import next_id
from .policy import PolicyEngine, Verdict


@dataclass
class ApprovalRecord:
    id: str
    agent_id: str
    action_type: str
    target: str
    status: str
    risk: str
    policy_rule: str
    cost_krw: int
    preview_url: str | None
    created_at: int
    decided_at: int | None
    decided_by: str | None
    comment: str | None
    params: dict[str, Any]


class ApprovalsService:
    def __init__(self, policy: PolicyEngine | None = None):
        self.policy = policy or PolicyEngine()

    # ──────────── Request path ────────────
    def request(
        self,
        *,
        agent_id: str,
        action_type: str,
        target: str,
        params: dict[str, Any] | None = None,
        preview_url: str | None = None,
        cost_krw: int = 0,
        audience: str = "ceo",
        channel: str | None = None,
    ) -> tuple[Verdict, str | None]:
        """Evaluate policy; if approval needed, enqueue and return (verdict, approval_id).

        For auto/deny/escalate → approval_id is None.
        """
        ctx: dict[str, Any] = {
            "actor": f"agent:{agent_id}",
            "action": {"type": action_type, "contains_secret": False},
            "target": {"env": (params or {}).get("env", "production"), "ref": target},
            "params": params or {},
            "audience": audience,
            "channel": channel,
            "template": {"id": (params or {}).get("template_id")},
        }
        verdict = self.policy.evaluate(ctx)

        if verdict.verdict != "approval":
            audit.emit(
                id=next_id("A"),
                actor=f"agent:{agent_id}",
                action_type=action_type,
                target=target,
                status=verdict.verdict,
                policy_rule=verdict.rule_id,
                cost_krw=cost_krw,
                extras={"verdict": verdict.verdict, "reason": verdict.reason},
            )
            return verdict, None

        # enqueue approval
        ap_id = next_id("AP")
        now = int(time.time())
        approval_params = dict(params or {})
        conn = connect()
        with conn:
            conn.execute(
                """INSERT INTO approvals
                (id, created_at, agent_id, action_type, target, preview_url,
                 cost_krw, risk, policy_rule, status, params_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (ap_id, now, agent_id, action_type, target, preview_url,
                 cost_krw, verdict.risk, verdict.rule_id, "pending",
                 json.dumps(approval_params, ensure_ascii=False)),
            )
        conn.close()

        audit.emit(
            id=next_id("A"),
            actor=f"agent:{agent_id}",
            action_type="request_approval",
            target=f"approval:{ap_id}",
            status="pending",
            policy_rule=verdict.rule_id,
            cost_krw=cost_krw,
            extras={"target": target, "risk": verdict.risk},
        )
        self._deliver_telegram_card(ap_id)
        return verdict, ap_id

    # ──────────── Decision path ────────────
    def decide(self, approval_id: str, verdict: str, *, by: str = "ceo", comment: str | None = None) -> ApprovalRecord:
        if verdict not in {"approved", "rejected", "deferred"}:
            raise ValueError(f"invalid verdict: {verdict}")
        now = int(time.time())
        conn = connect()
        with conn:
            row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
            if row is None:
                raise KeyError(approval_id)
            if row["status"] != "pending":
                raise RuntimeError(f"{approval_id} already {row['status']}")
            conn.execute(
                "UPDATE approvals SET status=?, decided_at=?, decided_by=?, comment=? WHERE id=?",
                (verdict, now, by, comment, approval_id),
            )
            row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        conn.close()

        audit.emit(
            id=next_id("A"),
            actor=f"user:{by}",
            action_type=f"approval_{verdict}",
            target=f"approval:{approval_id}",
            status="success",
            policy_rule=row["policy_rule"],
            cost_krw=row["cost_krw"] or 0,
            extras={"comment": comment},
        )
        return _row_to_record(row)

    def _deliver_telegram_card(self, approval_id: str) -> None:
        """Best-effort Telegram card delivery; approval creation must not fail if Telegram is down."""
        record = self.get(approval_id)
        if record is None:
            return
        try:
            from .telegram_approvals import send_approval_card

            result = send_approval_card(record)
            params = dict(record.params)
            params["telegram"] = {
                "decision_surface": "primary",
                "delivery_status": result.delivery_status,
                "chat_ref": result.chat_ref,
                "message_ref": result.message_ref,
                "sent_at": int(time.time()),
            }
            conn = connect()
            try:
                with conn:
                    conn.execute(
                        "UPDATE approvals SET params_json=? WHERE id=?",
                        (json.dumps(params, ensure_ascii=False), approval_id),
                    )
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001 - approval enqueue must be durable even if Telegram fails.
            audit.emit(
                id=next_id("A"),
                actor="system:soloos",
                action_type="telegram_approval_card_failed",
                target=f"approval:{approval_id}",
                status="failed",
                extras={"error": type(exc).__name__},
            )


    # ──────────── Query ────────────
    def list_pending(self, limit: int = 50) -> list[ApprovalRecord]:
        conn = connect()
        rows = conn.execute(
            "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [_row_to_record(r) for r in rows]

    def get(self, approval_id: str) -> ApprovalRecord | None:
        conn = connect()
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        conn.close()
        return _row_to_record(row) if row else None

    def expire_stale(self, ttl_seconds: int = 72 * 3600) -> int:
        cutoff = int(time.time()) - ttl_seconds
        conn = connect()
        with conn:
            cur = conn.execute(
                "UPDATE approvals SET status='expired', decided_at=?, decided_by='system' "
                "WHERE status='pending' AND created_at < ?",
                (int(time.time()), cutoff),
            )
            n = cur.rowcount
        conn.close()
        return n


def _row_to_record(row: Any) -> ApprovalRecord:
    return ApprovalRecord(
        id=row["id"],
        agent_id=row["agent_id"],
        action_type=row["action_type"],
        target=row["target"],
        status=row["status"],
        risk=row["risk"] or "LOW",
        policy_rule=row["policy_rule"] or "",
        cost_krw=row["cost_krw"] or 0,
        preview_url=row["preview_url"],
        created_at=row["created_at"],
        decided_at=row["decided_at"],
        decided_by=row["decided_by"],
        comment=row["comment"],
        params=json.loads(row["params_json"] or "{}"),
    )
