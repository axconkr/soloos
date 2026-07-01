"""SoloOS CLI — `soloos <command>`."""
from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .approvals import ApprovalsService
from .briefing import morning_brief, status_summary
from .config import get_config
from .db import connect, migrate as run_migrations
from .policy import PolicyEngine

console = Console()


@click.group()
@click.version_option(__version__, prog_name="soloos")
def main() -> None:
    """SoloOS — AI-Native OS for Solopreneur CEOs."""


# ─── db ────────────────────────────────────────────────
@main.group()
def db() -> None:
    """Database commands."""


@db.command("migrate")
def db_migrate() -> None:
    """Apply pending SQL migrations."""
    applied = run_migrations()
    if applied:
        console.print(f"[green]✓ applied migrations:[/green] {applied}")
    else:
        console.print("[cyan]nothing to migrate[/cyan]")


@db.command("info")
def db_info() -> None:
    cfg = get_config()
    console.print(f"DB: [bold]{cfg.db_path}[/bold]")
    conn = connect()
    for name in ("agents", "actions", "approvals", "audit_events", "sessions"):
        try:
            n = conn.execute(f"SELECT COUNT(*) c FROM {name}").fetchone()["c"]
        except Exception:
            n = "?"
        console.print(f"  {name:16s} {n}")
    conn.close()


# ─── policy ────────────────────────────────────────────
@main.group()
def policy() -> None:
    """Policy engine commands."""


@policy.command("show")
def policy_show() -> None:
    p = PolicyEngine()
    t = Table(title=f"Policy rules ({len(p.rules)})")
    t.add_column("id"); t.add_column("verdict"); t.add_column("risk"); t.add_column("when")
    for r in p.rules:
        t.add_row(r.get("id", "?"), r.get("verdict", "?"), r.get("risk", "-"), r.get("when", "-"))
    console.print(t)


@policy.command("test")
@click.option("--actor", required=True)
@click.option("--action-type", required=True)
@click.option("--target", default="test")
@click.option("--params", default="{}", help="JSON")
@click.option("--audience", default="ceo")
@click.option("--channel", default=None)
def policy_test(actor: str, action_type: str, target: str, params: str, audience: str, channel: str | None) -> None:
    p = PolicyEngine()
    ctx = {
        "actor": actor,
        "action": {"type": action_type, "contains_secret": False},
        "target": {"env": "production", "ref": target},
        "params": json.loads(params),
        "audience": audience,
        "channel": channel,
        "template": {"id": json.loads(params).get("template_id")},
    }
    v = p.evaluate(ctx)
    console.print(f"[bold]{v.verdict}[/bold]  rule={v.rule_id} risk={v.risk} reason={v.reason}")


# ─── deck (Command Deck) ───────────────────────────────
@main.group()
def deck() -> None:
    """Command Deck operations."""


@deck.command("status")
def deck_status() -> None:
    console.print(status_summary())


@deck.command("brief")
@click.option("--period", type=click.Choice(["today", "week"]), default="today")
def deck_brief(period: str) -> None:
    console.print(morning_brief())


@deck.command("queue")
def deck_queue() -> None:
    ap = ApprovalsService()
    pending = ap.list_pending()
    if not pending:
        console.print("[green]결재 대기 없음.[/green]")
        return
    t = Table(title=f"Pending approvals ({len(pending)})")
    for col in ("id", "agent", "action", "target", "risk", "policy"):
        t.add_column(col)
    for a in pending:
        t.add_row(a.id, a.agent_id, a.action_type, a.target, a.risk, a.policy_rule)
    console.print(t)


# ─── approvals ─────────────────────────────────────────
@main.group()
def approvals() -> None:
    """Approvals lifecycle."""


@approvals.command("request")
@click.option("--agent", "agent_id", required=True)
@click.option("--action", "action_type", required=True)
@click.option("--target", required=True)
@click.option("--params", default="{}")
@click.option("--cost", "cost_krw", type=int, default=0)
@click.option("--audience", default="ceo")
@click.option("--channel", default=None)
def approvals_request(agent_id: str, action_type: str, target: str, params: str, cost_krw: int, audience: str, channel: str | None) -> None:
    svc = ApprovalsService()
    v, ap_id = svc.request(
        agent_id=agent_id,
        action_type=action_type,
        target=target,
        params=json.loads(params),
        cost_krw=cost_krw,
        audience=audience,
        channel=channel,
    )
    console.print(f"verdict=[bold]{v.verdict}[/bold] rule={v.rule_id} approval_id={ap_id or '-'}")


@approvals.command("decide")
@click.argument("approval_id")
@click.argument("verdict", type=click.Choice(["approved", "rejected", "deferred"]))
@click.option("--comment", default=None)
@click.option("--by", default="ceo")
def approvals_decide(approval_id: str, verdict: str, comment: str | None, by: str) -> None:
    svc = ApprovalsService()
    rec = svc.decide(approval_id, verdict, by=by, comment=comment)
    console.print(f"[green]✓[/green] {rec.id} → [bold]{rec.status}[/bold] by {rec.decided_by}")


@approvals.command("expire")
def approvals_expire() -> None:
    n = ApprovalsService().expire_stale()
    console.print(f"expired {n} stale approvals")


# ─── audit ─────────────────────────────────────────────
@main.command("audit")
@click.option("--actor", default=None)
@click.option("--action-type", default=None)
@click.option("--limit", default=20)
def audit_cmd(actor: str | None, action_type: str | None, limit: int) -> None:
    from . import audit as audit_mod
    rows = audit_mod.search(actor=actor, action_type=action_type, limit=limit)
    t = Table(title=f"Audit events ({len(rows)})")
    for col in ("id", "ts", "actor", "action_type", "target", "status", "policy_rule"):
        t.add_column(col)
    for r in rows:
        t.add_row(r["id"], str(r["ts"]), r["actor"] or "-", r["action_type"] or "-", r["target"] or "-", r["status"] or "-", r["policy_rule"] or "-")
    console.print(t)


if __name__ == "__main__":
    main()
