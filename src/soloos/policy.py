"""Policy Engine: rule evaluation → verdict {auto, approval, deny, escalate}.

Design:
- Rules evaluated top-to-bottom, first match wins.
- Expressions parsed by simpleeval (safe subset).
- Rule expression *syntax* errors are surfaced (logged as ERROR) so YAML
  typos don't silently ignore rules.
- Rule *runtime* errors (missing keys against a valid context) are logged
  DEBUG and treated as no-match — allows optional context keys.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from simpleeval import EvalWithCompoundTypes, InvalidExpression

log = logging.getLogger(__name__)

VERDICTS = {"auto", "approval", "deny", "escalate"}

_ENV_POL = os.getenv("SOLOOS_POLICY_FILE")
POLICY_FILE = (
    Path(_ENV_POL) if _ENV_POL else Path(__file__).resolve().parents[2] / "policy" / "rules.yaml"
)

HARD_GUARDRAIL_KRW = 5_000_000


@dataclass
class Verdict:
    verdict: str
    rule_id: str
    reason: str = ""
    risk: str = "LOW"
    template: str | None = None
    escalate_to: str | None = None


class PolicyRuleError(ValueError):
    """Raised when a policy rule expression is invalid and cannot be trusted."""


class PolicyEngine:
    def __init__(self, rules_path: Path = POLICY_FILE):
        self.rules_path = rules_path
        self.rules: list[dict[str, Any]] = []
        self.default_verdict = "approval"
        self.load()

    def load(self) -> None:
        if not self.rules_path.exists():
            log.warning("policy file not found: %s", self.rules_path)
            self.rules = []
            return
        with self.rules_path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        rules = doc.get("rules", [])
        # Validate rule shapes at load time (fail fast on typos).
        for r in rules:
            if not isinstance(r, dict):
                raise ValueError(f"policy rule not a mapping: {r!r}")
            if "id" not in r:
                raise ValueError(f"policy rule missing 'id': {r!r}")
            v = r.get("verdict")
            if v not in VERDICTS:
                raise ValueError(f"policy rule {r['id']} has invalid verdict: {v!r}")
        self.rules = rules
        self.default_verdict = doc.get("default_verdict", "approval")

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        """Apply rules top-to-bottom; first match wins.

        Hard guardrail: any amount_krw > HARD_GUARDRAIL_KRW forces approval
        regardless of matched rule (§Policy Engine §5.1 hardcoded).
        """
        params = context.get("params") or {}
        try:
            amt = int(params.get("amount_krw", 0) or 0)
        except (TypeError, ValueError):
            amt = 0
        if amt > HARD_GUARDRAIL_KRW:
            return Verdict(
                "approval",
                "guardrail:two_key_5M",
                risk="HIGH",
                reason=f"Amount ₩{amt:,} exceeds ₩{HARD_GUARDRAIL_KRW:,} hard rule.",
            )

        evaluator = EvalWithCompoundTypes(names=_flatten(context))
        for rule in self.rules:
            expr = rule.get("when")
            if not expr:
                continue
            try:
                matched = bool(evaluator.eval(expr))
            except (InvalidExpression, SyntaxError) as exc:
                log.error(
                    "policy rule %s expression invalid: %s (%s)",
                    rule.get("id"), expr, exc,
                )
                raise PolicyRuleError(
                    f"policy rule {rule.get('id')} expression invalid: {expr!r}"
                ) from exc
            except (NameError, KeyError, AttributeError, TypeError) as exc:
                log.debug(
                    "policy rule %s did not match (missing ctx): %s",
                    rule.get("id"), exc,
                )
                continue
            if not matched:
                continue

            exempt = rule.get("exempt_if")
            if exempt:
                try:
                    if bool(evaluator.eval(exempt)):
                        return Verdict(
                            "auto", rule["id"],
                            reason="exempt_if matched",
                            risk=rule.get("risk", "LOW"),
                        )
                except Exception as exc:  # noqa: BLE001
                    log.debug("exempt_if eval failed for %s: %s", rule["id"], exc)

            return Verdict(
                verdict=rule["verdict"],
                rule_id=rule["id"],
                reason=rule.get("reason", ""),
                risk=rule.get("risk", "LOW"),
                template=rule.get("template"),
                escalate_to=rule.get("to"),
            )
        return Verdict(self.default_verdict, "default", reason="no rule matched")


def _flatten(ctx: dict[str, Any]) -> dict[str, Any]:
    return {k: _wrap(v) for k, v in ctx.items()}


def _wrap(v: Any) -> Any:
    if isinstance(v, dict):
        return _AttrDict({k: _wrap(sub) for k, sub in v.items()})
    return v


class _AttrDict(dict):
    """Dict with attribute access for expressions like `action.type`."""

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        return self.get(key)
