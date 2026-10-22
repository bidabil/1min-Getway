# API Reference – 1min-Gateway 2.x

Base URL in the examples: `http://127.0.0.1:5001`.

## Authentication

Every endpoint except `/`, `/health`, `/ready` and `/v1/version` requires a **gateway key**
(created with `python -m gateway.cli create-key NAME`), sent as one of:

```
Authorization: Bearer gw-...      (OpenAI clients, MCP)
x-api-key: gw-...                 (Anthropic clients)
api-key: gw-...
```

Errors use the format of the API family that received the request:

```json
{"error": {"message": "Invalid API key.", "type": "authentication_error", "param": null, "code": "invalid_api_key"}}
{"type": "error", "error": {"type": "authentication_error", "message": "Invalid API key."}}
```

| Status | Meaning |
|--------|---------|
| 400 | Invalid request (the `param` field names the offending field) |
| 401 | Missing or invalid gateway key |
| 403 / 404 | Refused by 1min.ai / unknown model, endpoint or result |
| 413 | Body or file too large |
| 429 | Gateway rate limit, 1min.ai rate limit or insufficient credits (`Retry-After` when known) |
| 502 | 1min.ai error (including an invalid server-side `ONE_MIN_API_KEY`) |
| 504 | 1min.ai timeout, or a job still processing |

Every response carries an `X-Request-ID` header (an incoming one is reused).

---

## OpenAI-compatible API

### `POST /v1/chat/completions`

Standard Chat Completions request. Supported:

| Field | Notes |
|-------|-------|
| `model`, `messages` | Roles `system`, `developer`, `user`, `assistant`, `tool`. Content: string or parts `text`, `image_url` (https URL, `data:` URI or asset key), `file` (`file_data` data URI or `file_id`). |
| `stream`, `stream_options.include_usage` | Server-sent events, `chat.completion.chunk`, ends with `data: [DONE]`. |
| `tools`, `tool_choice`, `parallel_tool_calls` | Function tools. Legacy `functions` / `function_call` are converted. |
| `response_format` | `text`, `json_object`, `json_schema` (native models). |
| `max_completion_tokens` / `max_tokens` | Capped to the model maximum. |
| `temperature`, `top_p`, `stop`, `presence_penalty`, `frequency_penalty`, `seed`, `reasoning_effort` | Forwarded to native models; dropped for models that reject them (configurable). |
| `n` | Only `1`. |

Gateway extensions:

| Field | Notes |
|-------|-------|
| `web_search` | `true` or `{"sites": 3, "max_words": 1000}`. Also: model suffix `:online`. |
| `file_ids` | 1min.ai file ids (from `POST /v1/files`) attached to the request. |
| `upstream_extra` | Object merged into the native 1min.ai request (advanced). |

Routing: models listed by 1min.ai's OpenAI-compatible API are served natively (real function
calling). Requests with images, files or web search, and models such as Claude, Gemini or Grok,
use the *Chat with AI* API: the conversation is sent in full, tool calls are emulated, usage is
estimated, and sampling parameters are not applied.

### `GET /v1/models`, `GET /v1/models/{id}`

OpenAI list format, built from 1min.ai (`/openai/v1/models` for native models, the public catalog
`/models?feature=UNIFY_CHAT_WITH_AI` for the others), cached for `MODELS_CACHE_TTL_S`. Each model
also has `backend` (`native` or `legacy`), `vision` (accepts images), and when known `name`,
`max_output_tokens`, `deprecation_date`; aliases have `alias_of`. With an `anthropic-version`
header the Anthropic list format is returned.

Model ids are resolved in this order: exact alias, known id, wildcard alias, then short Claude
names (`claude-haiku-4-5-20251001` → `us.anthropic.claude-haiku-4-5-20251001-v1:0`). Sending an
image to a model whose `vision` is `false` returns `400 model_not_vision_capable`.

### `POST /v1/images/generations`

`prompt`, `model` (default `gpt-image-1`), `n`, `size` (`1024x1024`…), `quality`, `style`,
`background`, `output_format`, `response_format` (`url` or `b64_json`), and `prompt_object` for
model-specific fields (e.g. `{"seed": 42, "negativePrompt": "..."}`). The size is converted for the
model: `size` for gpt-image, `aspect_ratio` for Flux/Stable Diffusion/Ideogram, `aspect_width` /
`aspect_height` for Magic Art.

Response: `{"created", "data": [{"url", "b64_json"?, "asset_key"}], "record_id"}`.
1min.ai signs one URL per job: with `n > 1` only the first item has a `url`.

### `POST /v1/images/edits` · `POST /v1/images/variations`

Multipart: `image` (file), `prompt` (edits), optional `mask`, `model` (defaults `gpt-image-2` /
`magic-art`), `n`, `size`, `quality`, `response_format`, `prompt_object` (JSON string).

### `POST /v1/audio/speech`

JSON: `input`, `voice` (OpenAI voice or ElevenLabs voice id), `model` (default `tts-1`; also
`tts-1-hd`, `elevenlabs-tts`), `response_format` (`mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`),
`speed`, `prompt_object`. Returns the audio bytes.

### `POST /v1/audio/transcriptions`

Multipart: `file`, `model` (default `whisper-1`), `language`, `prompt`, `temperature`,
`response_format` (`json`, `text`, `srt`, `vtt`, `verbose_json`).

### `POST /v1/files`

Multipart `file`, optional `purpose`. Uploads to the 1min.ai Asset API and returns an OpenAI file
object whose `id` is the asset key (use it as `imageUrl` / `audioUrl` in features), plus
`file_id` (use it in `file_ids` for chat).

---

## Anthropic-compatible API

### `POST /v1/messages`

`model`, `max_tokens`, `messages`, `system`, `tools` (`input_schema`), `tool_choice`
(`auto`, `any`, `tool`, `none`, `disable_parallel_tool_use`), `temperature`, `top_p`,
`stop_sequences`, `stream`, `metadata.user_id`. Content blocks: `text`, `image` (base64 or URL),
`document` (base64 or text), `tool_use`, `tool_result`. The server tool `web_search_*` enables
1min.ai web search. `thinking` blocks are ignored.

Streaming emits `message_start`, `content_block_start/delta/stop`, `message_delta`,
`message_stop`. Text streams live; tool_use blocks are sent complete at the end.

### `POST /v1/messages/count_tokens`

Returns `{"input_tokens": n}` (estimate: characters / 4, plus 1000 per image).

---

## 1min.ai features

Every 1min.ai AI feature (`IMAGE_GENERATOR`, `TEXT_TO_VIDEO`, `MUSIC_GENERATOR`,
`BACKGROUND_REMOVER`, `YOUTUBE_SUMMARIZER`, `CONTENT_TRANSLATOR`, `SUMMARIZER`, `CODE_GENERATOR`, …).
Field names come from the [1min.ai documentation](https://docs.1min.ai/docs/api/ai-feature-api).

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/features` | Catalog: types, categories, example models, documented fields |
| `GET /v1/features/{type}` | One catalog entry |
| `GET /v1/features/{type}/models` | Models 1min.ai currently accepts for this feature (live) |
| `POST /v1/features/{type}` | Run a feature (any documented type, even outside the catalog) |
| `GET /v1/features/results/{id}` | Status and result of a job |

```json
POST /v1/features/TEXT_TO_VIDEO
{
  "model": "kling",
  "prompt_object": {"prompt": "a lighthouse at dawn", "duration": 5, "version": "1.6", "mode": "std"},
  "mode": "async"
}
```

`mode`: `wait` (default: the gateway starts the job and polls until it ends or `timeout_s`
expires), `async` (returns `202` with the job id immediately) or `sync` (single upstream call).
Optional: `conversation_id`, `extra` (top-level fields merged into the 1min.ai request),
`timeout_s`. Response: `{"id", "type", "model", "status": "succeeded|processing|failed",
"results", "temporary_url", "created_at", "error"}` (HTTP 202 while processing).

---

## MCP server – `/mcp`

Streamable HTTP (stateless, JSON responses), authenticated with a gateway key. Tools:

| Tool | Purpose |
|------|---------|
| `web_search` | Answer a question with live web search |
| `analyze_image` | Ask a vision model about an image (URL, data URI or asset key) |
| `generate_image` | Text to image |
| `text_to_speech` / `transcribe_audio` | Speech synthesis / transcription |
| `upload_file` | Upload base64 content, returns an asset key |
| `summarize_youtube`, `translate_text` | Common writing/video features |
| `list_features`, `run_feature`, `get_feature_result` | Any 1min.ai feature |

---

## Operations

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health` | none | Liveness (never calls 1min.ai) |
| `GET /ready` | none | 200 when the 1min.ai model list is reachable (cached), else 503 |
| `GET /v1/version` | none | Version and commit |
| `GET /metrics` | `METRICS_TOKEN` | Prometheus metrics (requests, latency, chat outcomes, tokens) |
| `GET /docs` | – | OpenAPI UI, only when `DOCS_ENABLED=true` |
