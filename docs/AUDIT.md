# Audit status

The previous audit report in this file (April 2026, "8.6/10, production ready") described code
that has since been replaced and was not accurate: several features it validated were not wired
(per-key rate limiting, webhooks, metrics), and it missed security issues found by the
independent audit of 2026-10-20 (SSRF through image URLs, unauthenticated admin endpoints,
client-triggerable circuit breaker, prompts in logs, broken conversation history, a CD pipeline
that could not succeed).

Version 2.0 is a rewrite that addresses these points:

| 2026-10-20 finding | 2.0 |
|--------------------|-----|
| SSRF through `image_url` | Client URLs are never fetched by the gateway; inline images go through the 1min.ai Asset API |
| Unauthenticated admin endpoints | Removed; every API route requires a gateway key, `/metrics` a token |
| Global DoS through the circuit breaker / blocking I/O | No shared breaker; fully async I/O; POSTs never retried |
| Conversation history lost with a system prompt | Stateless: the full conversation is sent on every call |
| Prompts and keys in logs | JSON logs with metadata only |
| `/health/detailed` always 503, `/metrics` unreadable | `/health`, `/ready`, `/v1/version`, Prometheus text `/metrics` |
| Ignored parameters, non-OpenAI error format | Parameters forwarded to native models; OpenAI and Anthropic error formats |
| Streaming dropped line breaks | Spec-compliant SSE parsing; tested |
| Tests hitting the real 1min.ai | Hermetic tests against an in-memory fake; sockets blocked |

See the README for the current architecture, configuration and limitations.
