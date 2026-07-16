from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_agents_md_exists_and_contains_soloos_operating_rules():
    agents_md = ROOT / "AGENTS.md"

    assert agents_md.exists(), "SoloOS should expose shared project instructions via AGENTS.md"

    content = agents_md.read_text(encoding="utf-8")
    required_phrases = [
        "SoloOS Agent Operating Constitution",
        "Do not copy leaked system prompts verbatim",
        "CEO-readable output first",
        "Evidence or it did not happen",
        "Decision gates stay with Phillip",
        "TDD for behavior changes",
        "Secrets never enter artifacts",
        "When work touches the Mission Control UI",
    ]
    for phrase in required_phrases:
        assert phrase in content


def test_agent_operating_constitution_doc_exists_and_is_linked():
    agents_md = ROOT / "AGENTS.md"
    constitution = ROOT / "docs" / "AGENT_OPERATING_CONSTITUTION.md"

    assert constitution.exists(), "Detailed agent rules should live in docs/AGENT_OPERATING_CONSTITUTION.md"

    agents_content = agents_md.read_text(encoding="utf-8")
    constitution_content = constitution.read_text(encoding="utf-8")

    assert "docs/AGENT_OPERATING_CONSTITUTION.md" in agents_content
    for phrase in [
        "Plan → Execute → Verify → Report",
        "Tool discipline",
        "Mission Control translation layer",
        "Prompt-pattern borrowing policy",
        "Never claim success without a check",
    ]:
        assert phrase in constitution_content
