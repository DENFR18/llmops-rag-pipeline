from collections.abc import AsyncIterator
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from src.config import Settings, get_settings

SYSTEM_PROMPT = (
    "You are a precise technical assistant. Answer ONLY using the provided context. "
    "If the context is insufficient, reply exactly: \"I don't have enough information.\" "
    "Cite sources inline as [doc_id]. Never invent facts, URLs, or APIs."
)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        cached = self.cache_read_input_tokens
        total_input = cached + self.cache_creation_input_tokens + self.input_tokens
        return cached / total_input if total_input else 0.0


@dataclass
class LLMResponse:
    text: str
    usage: TokenUsage
    model: str


def _build_messages(question: str) -> list[dict]:
    return [{"role": "user", "content": question}]


def _build_system_blocks(context: str) -> list[dict]:
    """Two cache breakpoints: stable system prompt + (often) reused RAG context.

    Anthropic prompt caching keys on the prefix of the system blocks, so the
    static instructions are cached separately from the retrieved context. When
    the same context is retrieved twice in a session, the second call reads
    the second block from cache as well.
    """
    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<retrieved_context>\n{context}\n</retrieved_context>",
            "cache_control": {"type": "ephemeral"},
        },
    ]


class ClaudeClient:
    def __init__(self, settings: Settings | None = None, client: AsyncAnthropic | None = None):
        self.settings = settings or get_settings()
        self.client = client or AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    async def complete(self, question: str, context: str) -> LLMResponse:
        resp = await self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.anthropic_max_tokens,
            system=_build_system_blocks(context),
            messages=_build_messages(question),
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            cache_creation_input_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
        )
        return LLMResponse(text=text, usage=usage, model=resp.model)

    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.anthropic_max_tokens,
            system=_build_system_blocks(context),
            messages=_build_messages(question),
        ) as stream:
            async for text in stream.text_stream:
                yield text
