"""SoloOS CLI — `soloos <command>`."""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .actions import ActionsService
from .agents import AgentsService
from .approvals import ApprovalsService
from .briefing import morning_brief, status_summary
from .command_deck import CommandDeck
from .config import get_config
from .db import connect
from .db import migrate as run_migrations
from .mission_control import decide_approval, submit_ceo_request
from .policy import PolicyEngine
from .workflow import WorkflowService

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
    try:
        for name in (
            "agents",
            "actions",
            "workflows",
            "workflow_steps",
            "approvals",
            "audit_events",
            "sessions",
            "intents",
        ):
            try:
                n = conn.execute(f"SELECT COUNT(*) c FROM {name}").fetchone()["c"]
            except Exception:
                n = "?"
            console.print(f"  {name:16s} {n}")
    finally:
        conn.close()


# ─── policy ────────────────────────────────────────────
@main.group()
def policy() -> None:
    """Policy engine commands."""


@policy.command("show")
def policy_show() -> None:
    p = PolicyEngine()
    t = Table(title=f"Policy rules ({len(p.rules)})")
    for col in ("id", "verdict", "risk", "when"):
        t.add_column(col)
    for r in p.rules:
        t.add_row(r.get("id", "?"), r.get("verdict", "?"), r.get("risk", "-"), r.get("when", "-"))
    console.print(t)


@policy.command("test")
@click.option("--actor", required=True)
@click.option("--action-type", required=True)
@click.option("--target", default="test")
@click.option("--target-env", default="production")
@click.option("--params", default="{}", help="JSON")
@click.option("--audience", default="ceo")
@click.option("--channel", default=None)
def policy_test(
    actor: str, action_type: str, target: str, target_env: str,
    params: str, audience: str, channel: str | None,
) -> None:
    p = PolicyEngine()
    params_dict = json.loads(params)
    ctx = {
        "actor": actor,
        "action": {"type": action_type, "contains_secret": False},
        "target": {"env": target_env, "ref": target},
        "params": params_dict,
        "audience": audience,
        "channel": channel,
        "template": {"id": params_dict.get("template_id")},
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


@deck.command("dispatch")
@click.argument("text")
@click.option("--platform", type=click.Choice(["telegram", "discord", "local"]), default="local")
@click.option("--chat-id", default="local")
@click.option("--thread-id", default=None)
def deck_dispatch(text: str, platform: str, chat_id: str, thread_id: str | None) -> None:
    """Dispatch freeform text through the Command Deck classifier."""
    response = CommandDeck().handle_text(
        platform=platform,
        chat_id=chat_id,
        thread_id=thread_id,
        text=text,
    )
    console.print(response.markdown)


# ─── mission control ───────────────────────────────────
@main.group(name="mission-control")
def mission_control_group() -> None:
    """CEO Mission Control operations."""


@mission_control_group.command("ask")
@click.argument("text")
@click.option("--platform", default="web")
@click.option("--chat-id", default="ceo")
@click.option("--thread-id", default=None)
@click.option("--snapshot-path", type=click.Path(path_type=str), default="apps/web/public/soloos-snapshot.json")
def mission_control_ask(
    text: str,
    platform: str,
    chat_id: str,
    thread_id: str | None,
    snapshot_path: str,
) -> None:
    """Route a CEO request and refresh the web dashboard snapshot."""
    result = submit_ceo_request(
        text=text,
        platform=platform,
        chat_id=chat_id,
        thread_id=thread_id,
        snapshot_path=Path(snapshot_path),
    )
    routed = f"agent:{result.routed_to}" if result.routed_to else "clarification_required"
    console.print(
        f"intent={result.intent} routed_to={routed} action_id={result.action_id or '-'} "
        f"snapshot={result.snapshot_path}"
    )


@mission_control_group.command("decide")
@click.argument("approval_id")
@click.argument("verdict", type=click.Choice(["approved", "rejected", "deferred"]))
@click.option("--by", default="ceo:web")
@click.option("--comment", default=None)
@click.option("--snapshot-path", type=click.Path(path_type=str), default="apps/web/public/soloos-snapshot.json")
def mission_control_decide(
    approval_id: str,
    verdict: str,
    by: str,
    comment: str | None,
    snapshot_path: str,
) -> None:
    """Record a CEO approval decision and refresh the web dashboard snapshot."""
    result = decide_approval(
        approval_id,
        verdict,
        by=by,
        comment=comment,
        snapshot_path=Path(snapshot_path),
    )
    console.print(f"approval={result.approval_id} status={result.status} snapshot={result.snapshot_path}")


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
def approvals_request(
    agent_id: str, action_type: str, target: str, params: str,
    cost_krw: int, audience: str, channel: str | None,
) -> None:
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


# ─── agents ─────────────────────────────────────────────
@main.group()
def agents() -> None:
    """Agent roster commands."""


@agents.command("seed")
def agents_seed() -> None:
    inserted = AgentsService().seed_defaults()
    console.print(f"[green]✓[/green] seeded {inserted} default agents")


@agents.command("list")
def agents_list() -> None:
    roster = AgentsService().list_agents()
    if not roster:
        console.print("[yellow]agent roster 비어 있음. `soloos agents seed`를 먼저 실행하세요.[/yellow]")
        return
    t = Table(title=f"Agents ({len(roster)})")
    for col in ("id", "name", "tier", "status", "skills"):
        t.add_column(col)
    for agent in roster:
        t.add_row(agent.id, agent.name, agent.tier, agent.status, ", ".join(agent.skills))
    console.print(t)


# ─── workflows ──────────────────────────────────────────
@main.group()
def workflows() -> None:
    """Workflow Engine commands."""


@workflows.command("list")
@click.option("--limit", default=20, type=int)
def workflows_list(limit: int) -> None:
    rows = WorkflowService().list_workflows(limit=limit)
    if not rows:
        console.print("[green]workflow 없음.[/green]")
        return
    t = Table(title=f"Workflows ({len(rows)})")
    for col in ("id", "type", "status", "actor", "steps", "source"):
        t.add_column(col)
    for row in rows:
        t.add_row(
            row.id,
            row.workflow_type,
            row.status,
            row.actor,
            str(row.step_count),
            row.source_action_id or "-",
        )
    console.print(t)


@workflows.command("steps")
@click.argument("workflow_id")
def workflows_steps(workflow_id: str) -> None:
    rows = WorkflowService().list_steps(workflow_id)
    if not rows:
        console.print("[yellow]workflow step 없음.[/yellow]")
        return
    t = Table(title=f"Workflow steps ({workflow_id})")
    for col in ("order", "id", "action", "status", "target", "output"):
        t.add_column(col)
    for row in rows:
        t.add_row(
            str(row.step_order),
            row.id,
            row.action_type,
            row.status,
            row.target or "-",
            row.output_ref or "-",
        )
    console.print(t)


@workflows.command("run-step")
@click.argument("workflow_id")
def workflows_run_step(workflow_id: str) -> None:
    result = WorkflowService().run_next_step(workflow_id)
    if result is None:
        console.print("[green]pending workflow step 없음.[/green]")
        return
    console.print(
        f"[green]✓[/green] {result.step_id} → [bold]{result.status}[/bold] "
        f"{result.output_ref} {result.output}"
    )


@workflows.command("retry-step")
@click.argument("workflow_id")
@click.argument("step_id")
def workflows_retry_step(workflow_id: str, step_id: str) -> None:
    step = WorkflowService().retry_step(workflow_id, step_id)
    if step is None:
        console.print("[yellow]failed workflow step 없음.[/yellow]")
        return
    console.print(f"[green]✓[/green] {step.id} → [bold]{step.status}[/bold] retry queued")


# ─── actions ───────────────────────────────────────────
@main.group()
def actions() -> None:
    """Actions queue and executor."""


@actions.command("next")
def actions_next() -> None:
    action = ActionsService().next_pending()
    if action is None:
        console.print("[green]pending action 없음.[/green]")
        return
    console.print(
        f"{action.id} {action.status} {action.actor}/{action.action_type} "
        f"target={action.target or '-'}"
    )


@actions.command("run-one")
def actions_run_one() -> None:
    result = ActionsService().run_one()
    if result is None:
        console.print("[green]pending action 없음.[/green]")
        return
    console.print(
        f"[green]✓[/green] {result.id} → [bold]{result.status}[/bold] "
        f"({result.latency_ms}ms) {result.output}"
    )


# ─── audit ─────────────────────────────────────────────
@main.group(name="audit")
def audit_group() -> None:
    """Audit log inspection."""


@audit_group.command("search")
@click.option("--actor", default=None)
@click.option("--action-type", default=None)
@click.option("--limit", default=20)
def audit_search(actor: str | None, action_type: str | None, limit: int) -> None:
    from . import audit as audit_mod
    rows = audit_mod.search(actor=actor, action_type=action_type, limit=limit)
    t = Table(title=f"Audit events ({len(rows)})")
    for col in ("id", "ts", "actor", "action_type", "target", "status", "policy_rule"):
        t.add_column(col)
    for r in rows:
        t.add_row(
            r["id"], str(r["ts"]), r["actor"] or "-", r["action_type"] or "-",
            r["target"] or "-", r["status"] or "-", r["policy_rule"] or "-",
        )
    console.print(t)


@audit_group.command("show")
@click.argument("event_id")
def audit_show(event_id: str) -> None:
    from . import audit as audit_mod
    record = audit_mod.get_event(event_id)
    if record is None:
        console.print(f"[yellow]audit event 없음:[/yellow] {event_id}")
        raise SystemExit(1)
    console.print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))


@audit_group.command("reindex")
def audit_reindex() -> None:
    from . import audit as audit_mod
    n = audit_mod.reindex()
    console.print(f"[green]✓ reindexed {n} audit events[/green]")


# ─── doctor ─────────────────────────────────────────────
@main.command("doctor")
def doctor() -> None:
    """Preflight check for env, DB, policy, LLM keys."""
    cfg = get_config()
    problems: list[str] = []
    warnings: list[str] = []

    console.print("[bold]SoloOS Doctor[/bold]")
    console.print(f"  data_dir: {cfg.data_dir}  {'✓' if cfg.data_dir.exists() else '✗'}")
    console.print(f"  db_path : {cfg.db_path}  {'✓' if cfg.db_path.exists() else '✗ (run: soloos db migrate)'}")

    # Policy
    p = PolicyEngine()
    console.print(f"  policy  : {len(p.rules)} rules loaded from {p.rules_path.name}")
    if not p.rules:
        problems.append("no policy rules loaded")

    # DB schema
    if cfg.db_path.exists():
        conn = connect()
        try:
            versions = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()]
            console.print(f"  schema  : migrations applied = {versions}")
        except Exception as e:
            problems.append(f"schema query failed: {e}")
        finally:
            conn.close()

    # Secrets (warn only)
    if not cfg.anthropic_key:
        warnings.append("ANTHROPIC_API_KEY missing (Reasoning tier will not work)")
    if not cfg.openai_key and not cfg.openrouter_key:
        warnings.append("OPENAI_API_KEY or OPENROUTER_API_KEY missing (Bulk/live fallback)")
    if cfg.openrouter_key:
        console.print(f"  openrouter: configured model={cfg.model_openrouter}")
    if not cfg.telegram_token:
        warnings.append("TELEGRAM_BOT_TOKEN missing (Command Deck TG channel disabled)")

    for w in warnings:
        console.print(f"  [yellow]⚠ {w}[/yellow]")
    for e in problems:
        console.print(f"  [red]✗ {e}[/red]")

    if problems:
        raise SystemExit(1)
    console.print("[green]✓ ready[/green]")


if __name__ == "__main__":
    main()
