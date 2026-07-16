"""Agent runner seam for workflow executors.

The first implementation is deterministic on purpose: it gives the workflow
engine a stable interface and durable artifact format before wiring live LLMs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .config import get_config


@dataclass(frozen=True)
class DraftContentRequest:
    workflow_id: str
    step_id: str
    step_order: int
    actor: str
    title: str
    content_type: str
    period: str
    source_action_id: str | None = None


@dataclass(frozen=True)
class DraftContentResult:
    markdown: str
    summary: str
    runner: str
    warning: str | None = None


class AgentRunner(Protocol):
    """Interface implemented by deterministic and future LLM-backed runners."""

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        """Generate a draft content artifact for a workflow step."""
        raise NotImplementedError


class DeterministicAgentRunner:
    """Stable offline runner used when live agent/LLM execution is unavailable."""

    name = "deterministic"

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        markdown = render_deterministic_draft(request)
        return DraftContentResult(
            markdown=markdown,
            summary=f"Draft written: {request.title} ({request.content_type})",
            runner=self.name,
        )


class AnthropicAgentRunner:
    """Opt-in live Anthropic runner."""

    name = "anthropic"

    def __init__(self, *, api_key: str, model: str, client_factory: Any | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client_factory = client_factory

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        client = self._client()
        response = client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0.3,
            system=(
                f"You are SoloOS {request.actor}. Produce concise, useful Markdown drafts "
                "for a solopreneur CEO."
            ),
            messages=[{"role": "user", "content": _draft_prompt(request)}],
        )
        body = _extract_text_content(response).strip()
        markdown = render_llm_draft(request, runner=self.name, model=self.model, body=body)
        return DraftContentResult(
            markdown=markdown,
            summary=f"Anthropic draft written: {request.title} ({request.content_type})",
            runner=self.name,
        )

    def _client(self) -> Any:
        if self.client_factory is not None:
            return self.client_factory(api_key=self.api_key)
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package is not installed; install soloos[llm]") from exc
        return Anthropic(api_key=self.api_key)


class OpenAICompatibleAgentRunner:
    """Opt-in OpenAI-compatible runner using the Responses API."""

    name = "openai-compatible"

    def __init__(self, *, api_key: str, model: str, client_factory: Any | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client_factory = client_factory

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        client = self._client()
        response = client.responses.create(
            model=self.model,
            temperature=0.3,
            max_output_tokens=1200,
            instructions=(
                f"You are SoloOS {request.actor}. Produce concise, useful Markdown drafts "
                "for a solopreneur CEO."
            ),
            input=_draft_prompt(request),
        )
        body = _extract_openai_text(response).strip()
        markdown = render_llm_draft(request, runner=self.name, model=self.model, body=body)
        return DraftContentResult(
            markdown=markdown,
            summary=f"OpenAI-compatible draft written: {request.title} ({request.content_type})",
            runner=self.name,
        )

    def _client(self) -> Any:
        if self.client_factory is not None:
            return self.client_factory(api_key=self.api_key)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed; install soloos[llm]") from exc
        return OpenAI(api_key=self.api_key)


class OpenRouterAgentRunner:
    """Opt-in OpenRouter runner using OpenAI SDK chat completions compatibility."""

    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        client_factory: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client_factory = client_factory

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        client = self._client()
        response = client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            max_tokens=1200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are SoloOS {request.actor}. Produce concise, useful Markdown drafts "
                        "for a solopreneur CEO."
                    ),
                },
                {"role": "user", "content": _draft_prompt(request)},
            ],
        )
        body = _extract_chat_completion_text(response).strip()
        markdown = render_llm_draft(request, runner=self.name, model=self.model, body=body)
        return DraftContentResult(
            markdown=markdown,
            summary=f"OpenRouter draft written: {request.title} ({request.content_type})",
            runner=self.name,
        )

    def _client(self) -> Any:
        if self.client_factory is not None:
            return self.client_factory(api_key=self.api_key, base_url=self.base_url)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed; install soloos[llm]") from exc
        return OpenAI(api_key=self.api_key, base_url=self.base_url)


class FallbackAgentRunner:
    """Run a primary runner, then safely fall back to deterministic output."""

    def __init__(self, *, primary: AgentRunner, fallback: AgentRunner) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{getattr(primary, 'name', 'primary')}+fallback"

    def draft_content(self, request: DraftContentRequest) -> DraftContentResult:
        try:
            return self.primary.draft_content(request)
        except Exception as exc:  # noqa: BLE001 - runner boundary must catch failures
            fallback_result = self.fallback.draft_content(request)
            primary_name = getattr(self.primary, "name", "primary")
            warning = f"{primary_name} failed: {exc}; used deterministic fallback"
            return DraftContentResult(
                markdown=_add_runner_warning(fallback_result.markdown, warning),
                summary=fallback_result.summary,
                runner=fallback_result.runner,
                warning=warning,
            )


def default_agent_runner() -> AgentRunner:
    """Return the configured runner, defaulting to deterministic safety.

    Live runners are opt-in via ``SOLOOS_AGENT_RUNNER`` and are always wrapped in
    deterministic fallback. Missing keys keep the default offline runner.
    """
    cfg = get_config(reload=True)
    requested = cfg.agent_runner.strip().lower()
    deterministic = DeterministicAgentRunner()

    if requested in {"", "deterministic"}:
        return deterministic
    if requested == "anthropic":
        if not cfg.anthropic_key:
            return deterministic
        return FallbackAgentRunner(
            primary=AnthropicAgentRunner(api_key=cfg.anthropic_key, model=cfg.model_reasoning),
            fallback=deterministic,
        )
    if requested in {"openai", "openai-compatible"}:
        if not cfg.openai_key:
            return deterministic
        return FallbackAgentRunner(
            primary=OpenAICompatibleAgentRunner(api_key=cfg.openai_key, model=cfg.model_bulk),
            fallback=deterministic,
        )
    if requested == "openrouter":
        if not cfg.openrouter_key:
            return deterministic
        return FallbackAgentRunner(
            primary=OpenRouterAgentRunner(
                api_key=cfg.openrouter_key,
                model=cfg.model_openrouter,
                base_url=cfg.openrouter_base_url,
            ),
            fallback=deterministic,
        )
    return deterministic


def render_llm_draft(
    request: DraftContentRequest,
    *,
    runner: str,
    model: str,
    body: str,
) -> str:
    """Wrap live LLM output in the same durable artifact envelope."""
    lines = [
        "---",
        f"workflow_id: {request.workflow_id}",
        f"step_id: {request.step_id}",
        f"step_order: {request.step_order}",
        f"actor: {request.actor}",
        "action_type: draft_content",
        f"type: {request.content_type}",
        f"period: {request.period}",
        f"runner: {runner}",
        f"model: {model}",
    ]
    if request.source_action_id:
        lines.append(f"source_action_id: {request.source_action_id}")
    lines.extend(["---", "", f"# {request.title}", "", body, ""])
    return "\n".join(lines)


def _draft_prompt(request: DraftContentRequest) -> str:
    source = request.source_action_id or "none"
    return (
        f"Draft a {request.content_type} artifact titled '{request.title}'.\n"
        f"Content type: {request.content_type}\n"
        f"Period: {request.period}\n"
        f"Workflow: {request.workflow_id} / Step: {request.step_id}\n"
        f"Source action: {source}\n\n"
        "Return only the Markdown body."
    )


def _extract_text_content(response: Any) -> str:
    parts = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    if not parts:
        raise RuntimeError("anthropic response did not contain text content")
    return "\n\n".join(parts)


def _extract_openai_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    parts = []
    for item in getattr(response, "output", []):
        for content in getattr(item, "content", []):
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    if not parts:
        raise RuntimeError("openai-compatible response did not contain text content")
    return "\n\n".join(parts)


def _extract_chat_completion_text(response: Any) -> str:
    parts = []
    for choice in getattr(response, "choices", []):
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if content:
            parts.append(str(content))
    if not parts:
        raise RuntimeError("chat completion response did not contain text content")
    return "\n\n".join(parts)


def render_deterministic_draft(request: DraftContentRequest) -> str:
    """Render the first inspectable content artifact for a draft_content step."""
    lines = [
        "---",
        f"workflow_id: {request.workflow_id}",
        f"step_id: {request.step_id}",
        f"step_order: {request.step_order}",
        f"actor: {request.actor}",
        "action_type: draft_content",
        f"type: {request.content_type}",
        f"period: {request.period}",
        f"runner: {DeterministicAgentRunner.name}",
    ]
    if request.source_action_id:
        lines.append(f"source_action_id: {request.source_action_id}")
    lines.extend(
        [
            "---",
            "",
            f"# {request.title}",
            "",
            "## Draft Brief",
            "",
            f"- Content type: {request.content_type}",
            f"- Period: {request.period}",
            f"- Owner: {request.actor}",
            "",
            "## Draft",
            "",
            f"This is a deterministic smoke draft for {request.title}.",
            "Replace this section with real agent-generated content in the next executor increment.",
            "",
        ]
    )
    return "\n".join(lines)


def _add_runner_warning(markdown: str, warning: str) -> str:
    """Insert a fallback warning into YAML frontmatter when present."""
    marker = "runner: deterministic\n"
    if marker in markdown:
        return markdown.replace(marker, f"{marker}runner_warning: {warning}\n", 1)
    return f"<!-- runner_warning: {warning} -->\n\n{markdown}"
