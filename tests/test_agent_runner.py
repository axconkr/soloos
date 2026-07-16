"""Agent runner seam tests."""
from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))

    import soloos.config as cfg_mod

    cfg_mod.reset_config()
    from soloos.db import migrate

    migrate()
    yield data_dir
    cfg_mod.reset_config()


def test_deterministic_agent_runner_renders_content_draft():
    from soloos.agent_runner import DeterministicAgentRunner, DraftContentRequest

    result = DeterministicAgentRunner().draft_content(
        DraftContentRequest(
            workflow_id="WF-0001",
            step_id="WS-0001",
            step_order=1,
            actor="agent:growth",
            title="Blog draft 1",
            content_type="blog",
            period="this_week",
            source_action_id="A-0001",
        )
    )

    assert result.runner == "deterministic"
    assert result.summary == "Draft written: Blog draft 1 (blog)"
    assert "runner: deterministic" in result.markdown
    assert "# Blog draft 1" in result.markdown
    assert "This is a deterministic smoke draft for Blog draft 1." in result.markdown


def test_default_agent_runner_is_deterministic_fallback_without_live_llm(monkeypatch):
    from soloos.agent_runner import DeterministicAgentRunner, default_agent_runner

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SOLOOS_AGENT_RUNNER", raising=False)

    assert isinstance(default_agent_runner(), DeterministicAgentRunner)


def test_default_agent_runner_requires_opt_in_before_using_live_llm(monkeypatch):
    from soloos.agent_runner import DeterministicAgentRunner, default_agent_runner

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("SOLOOS_AGENT_RUNNER", raising=False)

    assert isinstance(default_agent_runner(), DeterministicAgentRunner)


def test_default_agent_runner_uses_deterministic_when_opted_in_without_key(monkeypatch):
    from soloos.agent_runner import DeterministicAgentRunner, default_agent_runner

    monkeypatch.setenv("SOLOOS_AGENT_RUNNER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert isinstance(default_agent_runner(), DeterministicAgentRunner)


def test_default_agent_runner_can_use_openrouter_key(monkeypatch):
    from soloos.agent_runner import FallbackAgentRunner, default_agent_runner

    monkeypatch.setenv("SOLOOS_AGENT_RUNNER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("SOLOOS_OPENROUTER_MODEL", "openai/gpt-5-mini")

    runner = default_agent_runner()

    assert isinstance(runner, FallbackAgentRunner)
    assert runner.name == "openrouter+fallback"


def test_opted_in_live_runner_is_wrapped_with_deterministic_fallback(monkeypatch):
    from soloos.agent_runner import FallbackAgentRunner, default_agent_runner

    monkeypatch.setenv("SOLOOS_AGENT_RUNNER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    runner = default_agent_runner()

    assert isinstance(runner, FallbackAgentRunner)
    assert runner.name == "anthropic+fallback"


def test_anthropic_agent_runner_calls_messages_api_and_wraps_markdown():
    from soloos.agent_runner import AnthropicAgentRunner, DraftContentRequest

    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)

            class Response:
                content = [type("TextBlock", (), {"text": "실제 초안 본문입니다."})()]

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            self.api_key = api_key
            self.messages = FakeMessages()

    result = AnthropicAgentRunner(
        api_key="test-key",
        model="claude-sonnet-4-5",
        client_factory=FakeClient,
    ).draft_content(
        DraftContentRequest(
            workflow_id="WF-0001",
            step_id="WS-0001",
            step_order=1,
            actor="agent:growth",
            title="Blog draft 1",
            content_type="blog",
            period="this_week",
            source_action_id="A-0001",
        )
    )

    assert result.runner == "anthropic"
    assert result.summary == "Anthropic draft written: Blog draft 1 (blog)"
    assert "runner: anthropic" in result.markdown
    assert "model: claude-sonnet-4-5" in result.markdown
    assert "# Blog draft 1" in result.markdown
    assert "실제 초안 본문입니다." in result.markdown
    assert calls == [
        {
            "model": "claude-sonnet-4-5",
            "max_tokens": 1200,
            "temperature": 0.3,
            "system": "You are SoloOS agent:growth. Produce concise, useful Markdown drafts for a solopreneur CEO.",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Draft a blog artifact titled 'Blog draft 1'.\n"
                        "Content type: blog\n"
                        "Period: this_week\n"
                        "Workflow: WF-0001 / Step: WS-0001\n"
                        "Source action: A-0001\n\n"
                        "Return only the Markdown body."
                    ),
                }
            ],
        }
    ]


def test_openai_compatible_agent_runner_calls_responses_api_and_wraps_markdown():
    from soloos.agent_runner import DraftContentRequest, OpenAICompatibleAgentRunner

    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)

            class Response:
                output_text = "OpenAI 초안 본문입니다."

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            self.api_key = api_key
            self.responses = FakeResponses()

    result = OpenAICompatibleAgentRunner(
        api_key="test-key",
        model="gpt-5-mini",
        client_factory=FakeClient,
    ).draft_content(
        DraftContentRequest(
            workflow_id="WF-0001",
            step_id="WS-0001",
            step_order=1,
            actor="agent:growth",
            title="Blog draft 1",
            content_type="blog",
            period="this_week",
            source_action_id="A-0001",
        )
    )

    assert result.runner == "openai-compatible"
    assert result.summary == "OpenAI-compatible draft written: Blog draft 1 (blog)"
    assert "runner: openai-compatible" in result.markdown
    assert "model: gpt-5-mini" in result.markdown
    assert "# Blog draft 1" in result.markdown
    assert "OpenAI 초안 본문입니다." in result.markdown
    assert calls == [
        {
            "model": "gpt-5-mini",
            "temperature": 0.3,
            "max_output_tokens": 1200,
            "instructions": "You are SoloOS agent:growth. Produce concise, useful Markdown drafts for a solopreneur CEO.",
            "input": (
                "Draft a blog artifact titled 'Blog draft 1'.\n"
                "Content type: blog\n"
                "Period: this_week\n"
                "Workflow: WF-0001 / Step: WS-0001\n"
                "Source action: A-0001\n\n"
                "Return only the Markdown body."
            ),
        }
    ]


def test_openrouter_agent_runner_calls_chat_completions_with_base_url_and_wraps_markdown():
    from soloos.agent_runner import DraftContentRequest, OpenRouterAgentRunner

    calls = []
    factory_kwargs = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)

            class Message:
                content = "OpenRouter 초안 본문입니다."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            factory_kwargs.append(kwargs)
            self.chat = FakeChat()

    result = OpenRouterAgentRunner(
        api_key="test-key",
        model="openai/gpt-5-mini",
        base_url="https://openrouter.ai/api/v1",
        client_factory=FakeClient,
    ).draft_content(
        DraftContentRequest(
            workflow_id="WF-0001",
            step_id="WS-0001",
            step_order=1,
            actor="agent:growth",
            title="Blog draft 1",
            content_type="blog",
            period="this_week",
            source_action_id="A-0001",
        )
    )

    assert factory_kwargs == [
        {"api_key": "test-key", "base_url": "https://openrouter.ai/api/v1"}
    ]
    assert result.runner == "openrouter"
    assert result.summary == "OpenRouter draft written: Blog draft 1 (blog)"
    assert "runner: openrouter" in result.markdown
    assert "model: openai/gpt-5-mini" in result.markdown
    assert "OpenRouter 초안 본문입니다." in result.markdown
    assert calls == [
        {
            "model": "openai/gpt-5-mini",
            "temperature": 0.3,
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "system",
                    "content": "You are SoloOS agent:growth. Produce concise, useful Markdown drafts for a solopreneur CEO.",
                },
                {
                    "role": "user",
                    "content": (
                        "Draft a blog artifact titled 'Blog draft 1'.\n"
                        "Content type: blog\n"
                        "Period: this_week\n"
                        "Workflow: WF-0001 / Step: WS-0001\n"
                        "Source action: A-0001\n\n"
                        "Return only the Markdown body."
                    ),
                },
            ],
        }
    ]


def test_fallback_agent_runner_uses_deterministic_when_primary_fails():
    from soloos.agent_runner import (
        DeterministicAgentRunner,
        DraftContentRequest,
        FallbackAgentRunner,
    )

    class BrokenRunner:
        name = "anthropic"

        def draft_content(self, request):
            raise RuntimeError("network down")

    result = FallbackAgentRunner(
        primary=BrokenRunner(),
        fallback=DeterministicAgentRunner(),
    ).draft_content(
        DraftContentRequest(
            workflow_id="WF-0001",
            step_id="WS-0001",
            step_order=1,
            actor="agent:growth",
            title="Blog draft 1",
            content_type="blog",
            period="this_week",
        )
    )

    assert result.runner == "deterministic"
    assert result.warning == "anthropic failed: network down; used deterministic fallback"
    assert "runner_warning: anthropic failed" in result.markdown


def test_workflow_audit_records_runner_warning_when_fallback_is_used(isolated_env):
    from soloos import audit
    from soloos.agent_runner import DeterministicAgentRunner, FallbackAgentRunner
    from soloos.workflow import WorkflowService

    class BrokenRunner:
        name = "anthropic"

        def draft_content(self, request):
            raise RuntimeError("network down")

    svc = WorkflowService(
        agent_runner=FallbackAgentRunner(
            primary=BrokenRunner(),
            fallback=DeterministicAgentRunner(),
        )
    )
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )

    result = svc.run_next_step(workflow.id)

    assert result is not None
    assert result.status == "success"
    event = audit.get_event("STEP-WS-0001")
    assert event is not None
    assert event["extras"]["runner"] == "deterministic"
    assert event["extras"]["runner_warning"] == (
        "anthropic failed: network down; used deterministic fallback"
    )


def test_workflow_uses_injected_agent_runner_for_draft_output(isolated_env):
    from soloos import audit
    from soloos.agent_runner import DraftContentResult
    from soloos.workflow import WorkflowService

    class FakeRunner:
        def draft_content(self, request):
            return DraftContentResult(
                markdown=(
                    "---\n"
                    "runner: fake\n"
                    f"workflow_id: {request.workflow_id}\n"
                    "---\n\n"
                    "# Custom runner output\n"
                ),
                summary="Fake runner wrote content",
                runner="fake",
            )

    svc = WorkflowService(agent_runner=FakeRunner())
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )

    result = svc.run_next_step(workflow.id)

    assert result is not None
    assert result.status == "success"
    assert result.output == "Fake runner wrote content"
    output_path = result.output_ref.removeprefix("file://")
    with open(output_path, encoding="utf-8") as f:
        assert "# Custom runner output" in f.read()

    event = audit.get_event("STEP-WS-0001")
    assert event is not None
    assert event["extras"]["runner"] == "fake"
