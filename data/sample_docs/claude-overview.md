# Claude API — overview

The Claude 4 family includes Opus 4.7 (`claude-opus-4-7`), Sonnet 4.6 (`claude-sonnet-4-6`),
and Haiku 4.5 (`claude-haiku-4-5-20251001`). Sonnet is the default workhorse for production
RAG workloads: high quality at moderate cost, 200K context window, native streaming, and
prompt caching support.

Authentication uses the `x-api-key` request header. The required `anthropic-version` header
pins the API version (currently `2023-06-01`).

The Messages API (`POST /v1/messages`) supports streaming via Server-Sent Events when
`stream=true`. The default temperature is `1.0`. Responses include a `stop_reason` field with
values such as `end_turn`, `max_tokens`, or `tool_use`.
