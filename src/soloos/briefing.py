"""Briefing generator — daily / on-demand summary for CEO."""
from __future__ import annotations

import time
from datetime import datetime

from .approvals import ApprovalsService
from .db import connect


def morning_brief() -> str:
    """Render a Markdown morning brief for Telegram."""
    now = datetime.now()
    ap = ApprovalsService()
    pending = ap.list_pending()

    conn = connect()
    since = int(time.time()) - 24 * 3600
    actions_24h = conn.execute(
        "SELECT COUNT(*) c FROM audit_events WHERE ts >= ?", (since,)
    ).fetchone()["c"]
    by_actor = conn.execute(
        "SELECT actor, COUNT(*) c FROM audit_events WHERE ts >= ? GROUP BY actor ORDER BY c DESC LIMIT 5",
        (since,),
    ).fetchall()
    conn.close()

    lines = [
        f"📊 *SoloOS Morning Brief · {now.strftime('%Y-%m-%d')}*",
        "",
        "*🎯 오늘의 결재 대기*",
    ]
    if pending:
        for a in pending[:10]:
            lines.append(f"  • `{a.id}` {a.agent_id}/{a.action_type} — {a.target} ({a.risk})")
    else:
        lines.append("  _대기 없음 — 편안한 아침_")

    lines += [
        "",
        f"*⚙️ 지난 24h 자동 액션*: {actions_24h}건",
    ]
    if by_actor:
        for r in by_actor:
            lines.append(f"  • {r['actor']}: {r['c']}")

    lines += [
        "",
        "_M5(Revenue) / M6(Ledger) 지표는 Week 4–5 구현 예정._",
    ]
    return "\n".join(lines)


def status_summary() -> str:
    ap = ApprovalsService()
    pending = ap.list_pending()
    conn = connect()
    running = conn.execute(
        "SELECT COUNT(*) c FROM actions WHERE status='running'"
    ).fetchone()["c"]
    conn.close()
    return (
        f"🖥 *SoloOS Status*\n"
        f"• 결재 대기: {len(pending)}건\n"
        f"• 실행 중 액션: {running}건\n"
        f"• 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
