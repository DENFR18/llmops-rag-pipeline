# Streaming and tool use

Streaming uses Server-Sent Events on the standard `/v1/messages` endpoint when `stream`
is set to `true`. The Python SDK exposes `AsyncAnthropic.messages.stream` as an async
context manager that yields incremental text via `text_stream`.

When Claude invokes a tool, the response `stop_reason` is `tool_use`. Tool results are sent
back as user messages whose content includes `tool_result` blocks referencing the
`tool_use_id`. `tool_choice` supports `auto`, `any`, `none`, and a specific tool selection
via `{type: "tool", name: "<tool_name>"}`.

Rate-limit headers include `anthropic-ratelimit-requests-limit` and
`anthropic-ratelimit-requests-remaining`. When throttled the API returns HTTP 429; clients
should retry with exponential backoff on 429 and 5xx errors. The Message Batches API allows
asynchronous processing of up to 10,000 requests per batch; results are retained for 29
days.
