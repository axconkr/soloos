"""Runtime config loader (env + defaults)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # graceful if dotenv missing
    pass


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("SOLOOS_DATA_DIR", "./data")).resolve())
    db_path: Path = field(default_factory=lambda: Path(os.getenv("SOLOOS_DB_PATH", "./data/soloos.sqlite")).resolve())
    timezone: str = os.getenv("SOLOOS_TIMEZONE", "Asia/Seoul")
    log_level: str = os.getenv("SOLOOS_LOG_LEVEL", "INFO")

    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key: str = os.getenv("OPENAI_API_KEY", "")

    model_reasoning: str = os.getenv("SOLOOS_MODEL_REASONING", "claude-sonnet-4-5")
    model_bulk: str = os.getenv("SOLOOS_MODEL_BULK", "claude-haiku-4-5")
    model_embedding: str = os.getenv("SOLOOS_MODEL_EMBEDDING", "text-embedding-3-small")

    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_ceo_chat_id: str = os.getenv("TELEGRAM_CEO_CHAT_ID", "")

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


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_dirs()
    return _config
