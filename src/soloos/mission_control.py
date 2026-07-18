"""CEO-facing Mission Control service helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import AgentsService
from .approvals import ApprovalsService
from .command_deck import CommandDeck
from .mission_control_snapshot import export_snapshot


@dataclass(frozen=True)
class MissionControlRequestResult:
    intent: str
    routed_to: str | None
    action_id: str | None
    snapshot_path: Path


@dataclass(frozen=True)
class MissionControlApprovalResult:
    approval_id: str
    status: str
    snapshot_path: Path


def submit_ceo_request(
    *,
    text: str,
    platform: str = "web",
    chat_id: str = "ceo",
    thread_id: str | None = None,
    snapshot_path: Path | None = None,
) -> MissionControlRequestResult:
    """Route a CEO request through Command Deck and refresh the web snapshot."""
    AgentsService().seed_defaults()
    response = CommandDeck().handle_text(
        platform=platform,
        chat_id=chat_id,
        thread_id=thread_id,
        text=text,
    )
    out_path = Path(snapshot_path or "apps/web/public/soloos-snapshot.json")
    export_snapshot(out_path=out_path)
    return MissionControlRequestResult(
        intent=response.intent,
        routed_to=response.routed_to,
        action_id=response.action_id,
        snapshot_path=out_path,
    )


def decide_approval(
    approval_id: str,
    verdict: str,
    *,
    by: str = "ceo:web",
    comment: str | None = None,
    snapshot_path: Path | None = None,
) -> MissionControlApprovalResult:
    """Record a CEO approval decision and refresh the web snapshot."""
    record = ApprovalsService().decide(approval_id, verdict, by=by, comment=comment)
    out_path = Path(snapshot_path or "apps/web/public/soloos-snapshot.json")
    export_snapshot(out_path=out_path)
    return MissionControlApprovalResult(
        approval_id=record.id,
        status=record.status,
        snapshot_path=out_path,
    )
