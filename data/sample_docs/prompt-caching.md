# Prompt caching

Prompt caching is enabled per content block by adding `cache_control` of type `ephemeral`.
A single request can include up to **four** `cache_control` breakpoints across its content
blocks. Cache blocks must meet a minimum size (1024 tokens for Sonnet-class models, 2048 for
Haiku-class models). Ephemeral cache entries expire approximately five minutes after the
last hit.

Cache writes (`cache_creation_input_tokens`) are billed at **1.25x** the base input rate.
Cache reads (`cache_read_input_tokens`) are billed at **0.1x** the base input rate.

Prompt caching graduated from beta and no longer requires the `prompt-caching-2024-07-31`
beta header. The `usage` object on responses exposes `input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, and `cache_read_input_tokens`.
