"""Command Deck text dispatch and session/intent persistence.

MVP scope: deterministic local classifier + SQLite persistence. The LLM
classifier can replace ``classify()`` later without changing the public API.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from . import audit
from .briefing import status_summary
from .db import connect
from .ids import next_id


@dataclass(frozen=True)
class ClassifiedIntent:
    intent: str
    routed_to: str | None
    confidence: float
    params: dict[str, Any]
    requires_clarification: bool = False


@dataclass(frozen=True)
class DeckResponse:
    markdown: str
    intent: str
    routed_to: str | None
    action_id: str | None
    requires_clarification: bool
    session_id: str


class CommandDeck:
    """Small Command Deck service for Telegram/Discord text inputs."""

    def handle_text(
        self,
        *,
        platform: str,
        chat_id: str,
        text: str,
        thread_id: str | None = None,
    ) -> DeckResponse:
        started = time.perf_counter()
        session_id = make_session_id(platform, chat_id, thread_id)
        classified = classify(text)
        latency_ms = int((time.perf_counter() - started) * 1000)

        self._persist_session(session_id, platform, chat_id, thread_id, classified)
        self._persist_intent(session_id, text, classified, latency_ms)

        action_id = None
        if classified.routed_to and not classified.requires_clarification:
            action_id = self._enqueue_action(session_id, classified)

        markdown = render_response(classified, action_id=action_id)
        status = "clarify" if classified.requires_clarification else "routed"
        audit.emit(
            id=next_id("A"),
            actor=f"user:{platform}:{chat_id}",
            action_type="deck_dispatch",
            target=f"session:{session_id}",
            status=status,
            policy_rule="command_deck:local_classifier",
            extras={
                "intent": classified.intent,
                "routed_to": classified.routed_to,
                "action_id": action_id,
                "confidence": classified.confidence,
            },
        )

        return DeckResponse(
            markdown=markdown,
            intent=classified.intent,
            routed_to=classified.routed_to,
            action_id=action_id,
            requires_clarification=classified.requires_clarification,
            session_id=session_id,
        )

    def _enqueue_action(self, session_id: str, classified: ClassifiedIntent) -> str:
        action_id = next_id("A")
        now = int(time.time())
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO actions
                (id, ts, actor, action_type, target, params_json, policy_rule,
                 status, cost_krw, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    action_id,
                    now,
                    f"agent:{classified.routed_to}",
                    classified.intent,
                    f"command_deck:{session_id}",
                    json.dumps(classified.params, ensure_ascii=False),
                    "command_deck:local_classifier",
                    "pending",
                    0,
                    now,
                ),
            )
        finally:
            conn.close()
        return action_id

    def _persist_session(
        self,
        session_id: str,
        platform: str,
        chat_id: str,
        thread_id: str | None,
        classified: ClassifiedIntent,
    ) -> None:
        now = int(time.time())
        snapshot = json.dumps(
            {
                "last_intent": classified.intent,
                "routed_to": classified.routed_to,
                "params": classified.params,
                "requires_clarification": classified.requires_clarification,
            },
            ensure_ascii=False,
        )
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO sessions
                (session_id, platform, chat_id, thread_id, active_agent, context_snapshot, updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                  active_agent=excluded.active_agent,
                  context_snapshot=excluded.context_snapshot,
                  updated_at=excluded.updated_at""",
                (
                    session_id,
                    platform,
                    chat_id,
                    thread_id,
                    classified.routed_to,
                    snapshot,
                    now,
                ),
            )
        finally:
            conn.close()

    def _persist_intent(
        self,
        session_id: str,
        text: str,
        classified: ClassifiedIntent,
        latency_ms: int,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO intents
                (ts, session_id, raw_text, classified_intent, routed_to, confidence, latency_ms)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    int(time.time()),
                    session_id,
                    text,
                    classified.intent,
                    classified.routed_to,
                    classified.confidence,
                    latency_ms,
                ),
            )
        finally:
            conn.close()


def make_session_id(platform: str, chat_id: str, thread_id: str | None = None) -> str:
    return f"{platform}:{chat_id}:{thread_id or ''}"


def classify(text: str) -> ClassifiedIntent:
    """Deterministic MVP classifier for the Week-1 Command Deck smoke path."""
    normalized = text.strip().lower()
    compact = normalized.replace(" ", "")

    if compact in {"안녕", "안녕하세요", "hi", "hello", "hey"}:
        return ClassifiedIntent("greeting", None, 1.0, {})

    if any(token in normalized for token in ("status", "상태", "진행", "요약")):
        return ClassifiedIntent("status", None, 0.9, {})

    if any(token in normalized for token in ("queue", "결재", "승인", "대기")):
        return ClassifiedIntent("approval_queue", None, 0.9, {})

    if any(token in normalized for token in ("문의", "답장", "답변", "회신", "리드", "영업", "고객", "sales")):
        params: dict[str, Any] = {}
        if any(token in normalized for token in ("문의", "답장", "답변", "회신")):
            params["type"] = "reply_draft"
        return ClassifiedIntent("sales_task", "growth", 0.8, params)

    if any(token in normalized for token in ("블로그", "콘텐츠", "content", "blog", "글", "초안")):
        return ClassifiedIntent("content_plan", "growth", 0.82, _extract_content_params(normalized))

    if any(token in normalized for token in ("비용", "결제", "송금", "돈", "finance")):
        return ClassifiedIntent("finance_task", "cfo", 0.78, {})

    return ClassifiedIntent(
        "unknown",
        None,
        0.0,
        {},
        requires_clarification=True,
    )


def _extract_content_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {"type": "content"}
    if "블로그" in text or "blog" in text:
        params["type"] = "blog"
    if "이번 주" in text or "이번주" in text:
        params["period"] = "this_week"
    for n in range(1, 10):
        if f"{n}편" in text or f"{n}개" in text:
            params["count"] = n
            break
    return params


def render_response(classified: ClassifiedIntent, *, action_id: str | None = None) -> str:
    if classified.intent == "greeting":
        return "안녕하세요. SoloOS Command Deck 정상 응답 중입니다. `/deck status`로 상태를 볼 수 있습니다."

    if classified.intent == "status":
        return status_summary()

    if classified.intent == "approval_queue":
        return "결재 대기열은 `/deck queue`에서 확인할 수 있습니다."

    if classified.intent == "content_plan":
        count = classified.params.get("count")
        unit = f" {count}건" if count else ""
        queued = f" 큐 ID: `{action_id}`" if action_id else ""
        return f"Growth 에이전트로 콘텐츠 작업{unit}을 pending 큐에 적재했습니다.{queued}"

    if classified.intent == "sales_task":
        queued = f" 큐 ID: `{action_id}`" if action_id else ""
        kind = "문의 답장 초안" if classified.params.get("type") == "reply_draft" else "세일즈"
        return f"Growth 에이전트로 {kind} 작업을 pending 큐에 적재했습니다.{queued}"

    if classified.intent == "finance_task":
        queued = f" 큐 ID: `{action_id}`" if action_id else ""
        return f"Finance 에이전트 작업을 pending 큐에 적재했습니다.{queued} 돈 관련 작업은 정책 게이트를 거칩니다."

    return "어느 팀으로 처리할까요? 선택지: CEO Office / Engineering / Design / Growth / Finance / Legal / Ops"
