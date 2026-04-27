from src.rag import RetrievedChunk, format_context


def test_format_context_empty_returns_placeholder():
    assert format_context([]) == "(no context available)"


def test_format_context_includes_source_score_and_index():
    chunks = [
        RetrievedChunk(text="alpha", source="a.md", score=0.91),
        RetrievedChunk(text="beta", source="b.md", score=0.42),
    ]

    out = format_context(chunks)

    assert "[1] source=a.md score=0.910" in out
    assert "[2] source=b.md score=0.420" in out
    assert "alpha" in out and "beta" in out


def test_llm_response_cache_hit_ratio():
    from src.llm import TokenUsage

    usage = TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=900,
    )
    assert usage.cache_hit_ratio == 0.9


def test_llm_response_cache_hit_ratio_zero_when_no_input():
    from src.llm import TokenUsage

    assert TokenUsage().cache_hit_ratio == 0.0
