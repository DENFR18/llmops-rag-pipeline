# Architecture

```
                            ┌──────────────────────────────────────┐
                            │           CI / CD (GitHub)           │
                            │                                      │
   commit ──► PR ──► ci.yml ─┼─► lint ─► test ─► sonarcloud         │
                            │           │                          │
                            │           └─► build ─► trivy ───┐     │
                            │                  └─► checkov ───┤     │
                            │                                  ▼     │
                            │                            push GHCR   │
                            │                                  │     │
                            │   eval.yml ─► Ragas + Promptfoo ─┤     │
                            │       (gates: 0.85/0.80/0.75)    │     │
                            │                                  ▼     │
                            │                  deploy-scaleway.yml   │
                            └──────────────────────────────┼────────┘
                                                            ▼
                                  ┌─────────────────────────────────────────┐
                                  │      Scaleway Serverless Container       │
                                  │      (FastAPI + Uvicorn, /query SSE)     │
                                  └───────┬───────────────┬──────────────────┘
                                          │               │
                          ┌───────────────▼─────┐   ┌─────▼─────────────┐
                          │   Anthropic API     │   │   Neon Postgres   │
                          │   Sonnet 4.6        │   │   + pgvector      │
                          │   prompt caching    │   │                   │
                          └─────────┬───────────┘   └─────▲─────────────┘
                                    │                     │
                                    │  trace             ingest (LlamaIndex
                                    ▼                     SentenceSplitter +
                          ┌───────────────────┐           Voyage embeddings)
                          │     Langfuse      │
                          │  (cost, latency,  │
                          │  cache_read/write)│
                          └───────────────────┘
```

## Request flow (`POST /query`)

1. **Guard** — `LLM Guard PromptInjection` rejects malicious inputs before any token is spent.
2. **Retrieve** — `LlamaIndex` queries `pgvector` over Neon, returning top-K chunks.
3. **Generate** — `ClaudeClient.stream()` calls `messages.stream` with two cached system
   blocks: a static instruction block and the retrieved context block.
4. **Stream** — Tokens are emitted to the client over SSE as they arrive.
5. **Redact** — Final accumulated answer goes through `LLM Guard Anonymize` before the
   `done` event is sent.
6. **Trace** — `Langfuse` records prompt, response, latency, and the
   `cache_read_input_tokens` / `cache_creation_input_tokens` ratio.

## Why prompt caching matters here

The system instruction (~400 tokens) and the retrieved context (typically 2-5K tokens) are
identical across follow-up turns in a session and across users hitting the same hot
documents. Marking both as `cache_control: ephemeral` makes Claude charge those tokens at
**0.1x** on every cache hit instead of **1x** — the same lever that turns a cost-prohibitive
RAG demo into a viable product.
