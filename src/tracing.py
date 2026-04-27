from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from langfuse import Langfuse

from src.config import get_settings


@lru_cache(maxsize=1)
def get_langfuse() -> Langfuse | None:
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key,
        host=s.langfuse_host,
    )


@contextmanager
def trace_query(user_id: str, session_id: str, question: str):
    """Yields a generation handle. Caller fills it in with the LLM result.

    The handle exposes `.update(...)` so the API layer can attach the response
    text, token usage (including cache_read/cache_write), and latency.
    """
    lf = get_langfuse()
    if lf is None:
        yield _NullGeneration()
        return

    trace = lf.trace(name="rag-query", user_id=user_id, session_id=session_id, input=question)
    generation = trace.generation(name="claude-completion", input=question)
    try:
        yield generation
    finally:
        generation.end()
        lf.flush()


class _NullGeneration:
    def update(self, **_: Any) -> None: ...
    def end(self, **_: Any) -> None: ...
    def score(self, **_: Any) -> None: ...
