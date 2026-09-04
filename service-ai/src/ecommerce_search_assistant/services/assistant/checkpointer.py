from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from ecommerce_search_assistant.core.config import Settings


@dataclass(frozen=True)
class CheckpointerHandle:
    saver: Any
    context_manager: AbstractContextManager[Any] | None = None


def build_checkpointer(settings: Settings) -> CheckpointerHandle:
    if settings.checkpoint_backend == "sqlite":
        checkpoint_path = Path(settings.sqlite_checkpoint_path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
        from langgraph.checkpoint.sqlite import SqliteSaver

        saver = SqliteSaver(connection)
        saver.setup()
        return CheckpointerHandle(saver=saver)

    if settings.checkpoint_backend == "postgres":
        if not settings.postgres_dsn:
            raise ValueError("POSTGRES_DSN is required when CHECKPOINT_BACKEND=postgres")
        from langgraph.checkpoint.postgres import PostgresSaver

        context_manager = PostgresSaver.from_conn_string(settings.postgres_dsn)
        saver = context_manager.__enter__()
        saver.setup()
        return CheckpointerHandle(saver=saver, context_manager=context_manager)

    if settings.checkpoint_backend == "redis":
        if not settings.redis_url:
            raise ValueError("REDIS_URL is required when CHECKPOINT_BACKEND=redis")
        from langgraph.checkpoint.redis import RedisSaver

        context_manager = RedisSaver.from_conn_string(settings.redis_url)
        saver = context_manager.__enter__()
        saver.setup()
        return CheckpointerHandle(saver=saver, context_manager=context_manager)

    raise ValueError(f"Unsupported CHECKPOINT_BACKEND={settings.checkpoint_backend}")
