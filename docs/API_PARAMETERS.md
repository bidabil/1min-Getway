## Paramètres Supportés

### Pour Image Generation

- `content_type: "IMAGE_GENERATOR"`
- `n: 1-4` (nombre d'images)
- `size: "1024x1024"` (ou "512x512", "256x256")
- `aspect_ratio: "1:1"` (ou "16:9", "9:16", "4:3")
- `output_format: "webp"` (ou "png", "jpg")
- `style: "anime"` (style artistique)
- `negative_prompt: "blurry, ugly"` (ce qu'il ne faut pas faire)

### Pour Chat avec Images

- `image_detail: "auto"` (ou "low", "high")
- `max_tokens: 300` (limite de réponse)

### Pour Multi-AI Chat

- `message_group: "timestamp_id"` (groupe les messages)
- `is_mixed: true` (mélange les modèles)
