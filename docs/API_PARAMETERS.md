# API Reference - 1min-Gateway

Complete reference for all endpoints exposed by 1min-Gateway.

## 📋 Table of Contents

- [Authentication](#authentication)
- [Core OpenAI-Compatible Endpoints](#core-openai-compatible-endpoints)
- [Health Endpoints](#health-endpoints)
- [Metrics](#metrics)
- [Cache](#cache)
- [Rate Limiting](#rate-limiting)

---

## 🔑 Authentication

All requests to `/v1/*` endpoints require a valid 1min.ai API key in the `Authorization` header:

```
Authorization: Bearer sk-your-1min-ai-key
```

---

## 🤖 Core OpenAI-Compatible Endpoints

### List Models

```
GET /v1/models
```

Returns the list of available models in OpenAI format.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-4o-mini", "object": "model", "created": 1700000000, "owned_by": "1min-ai"},
    {"id": "deepseek-chat", "object": "model", "created": 1700000000, "owned_by": "1min-ai"}
  ]
}
```

---

### Chat Completions

```
POST /v1/chat/completions
```

Main endpoint. Fully OpenAI-compatible.

**Request body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model ID (e.g. `gpt-4o-mini`, `deepseek-chat`) |
| `messages` | array | Yes | Conversation history |
| `stream` | boolean | No | Enable SSE streaming (default: `false`) |
| `max_tokens` | integer | No | Maximum tokens in response |
| `temperature` | float | No | Sampling temperature `0.0–2.0` |
| `top_p` | float | No | Nucleus sampling `0.0–1.0` |
| `n` | integer | No | Number of completions to generate |
| `web_search` | boolean | No | Enable web search augmentation |

**Message format:**

```json
{
  "role": "user",
  "content": "Hello!"
}
```

For **vision** (image input):

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What is in this image?"},
    {"type": "image_url", "image_url": {"url": "https://...", "detail": "auto"}}
  ]
}
```

**Minimal example:**

```bash
curl http://localhost:5001/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Streaming example:**

```bash
curl http://localhost:5001/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

**Response (non-streaming):**

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello! How can I help?"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

---

## 🏥 Health Endpoints

### Basic Health Check

```
GET /
```

**Response:**
```json
{
  "status": "ok",
  "architecture": "FastAPI + Clean Architecture",
  "circuit_breaker": {"state": "closed", "failures": 0}
}
```

---

### Detailed Health Check

```
GET /health/detailed
```

Checks connectivity to 1min.ai API, Memcached status, and circuit breaker state.

---

### Circuit Breaker Status

```
GET /health/circuit-breaker
```

Returns detailed circuit breaker statistics.

---

### Reset Circuit Breaker

```
POST /health/circuit-breaker/reset
```

Manually resets the circuit breaker to `closed` state.

---

## 📊 Metrics

### Prometheus Metrics

```
GET /metrics
```

Exposes metrics in Prometheus text format:
- HTTP request counters and histograms
- Circuit breaker state
- Cache usage
- Requests per model

---

## 🗄 Cache

### Cache Statistics

```
GET /cache/stats
```

Returns model cache statistics (hit rate, size, etc.).

---

### Invalidate Cache

```
POST /cache/invalidate
```

Clears the model list cache.

---

## 🚦 Rate Limiting

### Rate Limit Statistics

```
GET /rate-limit/stats
```

Returns global rate limiting statistics.

---

### Usage by API Key

```
GET /rate-limit/usage/{api_key}
```

Returns rate limit usage for a specific API key.

---

### Reset Rate Limit

```
POST /rate-limit/reset/{api_key}
```

Resets rate limit counters for a specific API key.

---

## 🔔 Webhooks

### List Webhooks

```
GET /webhooks
```

Returns all registered webhook endpoints.

### Register Webhook

```
POST /webhooks/register
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Unique name for the webhook |
| `url` | string | Yes | Endpoint URL to deliver events to |
| `secret` | string | Yes | Secret for HMAC signature verification |
| `events` | array | No | List of event types to subscribe to (default: all) |

### Unregister Webhook

```
DELETE /webhooks/{name}
```

### Webhook Delivery History

```
GET /webhooks/history
```

Returns the last 20 delivery attempts.

### Webhook Statistics

```
GET /webhooks/stats
```

Returns total sent, successful, failed, and retry counts.

---

## ⚠️ Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| `401` | Invalid or missing API key |
| `429` | Rate limit exceeded |
| `500` | Internal error or 1min.ai API unreachable |
| `503` | Circuit breaker open (too many upstream failures) |
