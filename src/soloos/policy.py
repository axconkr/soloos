"""Policy Engine: rule evaluation → verdict {auto, approval, deny, escalate}."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from simpleeval import EvalWithCompoundTypes, InvalidExpression

VERDICTS = {"auto", "approval", "deny", "escalate"}
import os

_ENV_POL = os.getenv("SOLOOS_POLICY_FILE")
POLICY_FILE = Path(_ENV_POL) if _ENV_POL else Path(__file__).resolve().parents[2] / "policy" / "rules.yaml"


@dataclass
class Verdict:
    verdict: str
    rule_id: str
    reason: str = ""
    risk: str = "LOW"
    template: str | None = None
    escalate_to: str | None = None


class PolicyEngine:
    def __init__(self, rules_path: Path = POLICY_FILE):
        self.rules_path = rules_path
        self.rules: list[dict[str, Any]] = []
        self.default_verdict = "approval"
        self.load()

    def load(self) -> None:
        if not self.rules_path.exists():
            self.rules = []
            return
        with self.rules_path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        self.rules = doc.get("rules", [])
        self.default_verdict = doc.get("default_verdict", "approval")

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        """Apply rules top-to-bottom; first match wins."""
        # Hard guardrail: >5M KRW spend always requires approval regardless of rules
        params = context.get("params") or {}
        try:
            amt = int(params.get("amount_krw", 0) or 0)
        except (TypeError, ValueError):
            amt = 0
        if amt > 5_000_000:
            return Verdict("approval", "guardrail:two_key_5M", risk="HIGH",
                           reason="Amount over ₩5,000,000 requires CEO approval by hard rule.")

        evaluator = EvalWithCompoundTypes(names=_flatten(context))
        for rule in self.rules:
            expr = rule.get("when")
            if not expr:
                continue
            try:
                if not evaluator.eval(expr):
                    continue
            except (InvalidExpression, Exception):  # noqa: BLE001
                continue
            # exempt_if allows immediate downgrade to auto
            exempt = rule.get("exempt_if")
            if exempt:
                try:
                    if evaluator.eval(exempt):
                        return Verdict("auto", rule.get("id", "?"), reason="exempt_if matched",
                                       risk=rule.get("risk", "LOW"))
                except Exception:  # noqa: BLE001
                    pass
            verdict = rule.get("verdict", self.default_verdict)
            if verdict not in VERDICTS:
                verdict = self.default_verdict
            return Verdict(
                verdict=verdict,
                rule_id=rule.get("id", "?"),
                reason=rule.get("reason", ""),
                risk=rule.get("risk", "LOW"),
                template=rule.get("template"),
                escalate_to=rule.get("to"),
            )
        return Verdict(self.default_verdict, "default", reason="no rule matched")


def _flatten(ctx: dict[str, Any]) -> dict[str, Any]:
    """Expose top-level keys AND their sub-dicts as attribute-accessible names."""
    out: dict[str, Any] = {}
    for k, v in ctx.items():
        out[k] = _AttrDict(v) if isinstance(v, dict) else v
    return out


class _AttrDict(dict):
    """Dict with attribute access for simpleeval expressions like `action.type`."""
    def __getattr__(self, key: str) -> Any:
        v = self.get(key)
        if isinstance(v, dict):
            return _AttrDict(v)
        return v
