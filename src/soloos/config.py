"""Runtime config loader (env + defaults).

Tests and CLIs can call ``get_config(reload=True)`` after changing env vars.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("SOLOOS_DATA_DIR", "./data")).resolve()
    )
    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("SOLOOS_DB_PATH", "./data/soloos.sqlite")
        ).resolve()
    )
    timezone: str = field(default_factory=lambda: os.getenv("SOLOOS_TIMEZONE", "Asia/Seoul"))
    log_level: str = field(default_factory=lambda: os.getenv("SOLOOS_LOG_LEVEL", "INFO"))
    agent_runner: str = field(
        default_factory=lambda: os.getenv("SOLOOS_AGENT_RUNNER", "deterministic")
    )

    anthropic_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openrouter_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_base_url: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )

    model_reasoning: str = field(
        default_factory=lambda: os.getenv("SOLOOS_MODEL_REASONING", "claude-sonnet-4-5")
    )
    model_bulk: str = field(
        default_factory=lambda: os.getenv("SOLOOS_MODEL_BULK", "claude-haiku-4-5")
    )
    model_openrouter: str = field(
        default_factory=lambda: os.getenv(
            "SOLOOS_OPENROUTER_MODEL", os.getenv("SOLOOS_MODEL_BULK", "openai/gpt-5-mini")
        )
    )
    model_embedding: str = field(
        default_factory=lambda: os.getenv("SOLOOS_MODEL_EMBEDDING", "text-embedding-3-small")
    )

    telegram_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_ceo_chat_id: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_CEO_CHAT_ID", "")
    )

    def audit_dir(self) -> Path:
        p = self.data_dir / "audit"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def snapshots_dir(self) -> Path:
        p = self.data_dir / "snapshots"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir()
        self.snapshots_dir()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


_config: Config | None = None


def get_config(reload: bool = False) -> Config:
    global _config
    if reload or _config is None:
        _config = Config()
        _config.ensure_dirs()
    return _config


def reset_config() -> None:
    """Testing helper: force re-reading env vars on next get_config()."""
    global _config
    _config = None
