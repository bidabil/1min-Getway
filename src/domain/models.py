"""
Domain models configuration for 1min-Gateway.
Strictly aligned with 1min.AI 2026 Documentation.
"""

# Complete list of available text/chat models via 1min.ai (Doc 2026)
ALL_ONE_MIN_AVAILABLE_MODELS = [
    # alibaba Models
    "qwen3-max", "qwen-plus", "qwen-max", "qwen-flash",
    
    # Anthropic Models
    "claude-sonnet-4-5-20250929", "claude-sonnet-4-20250514",
    "claude-opus-4-5-20251101", "claude-opus-4-20250514",
    "claude-opus-4-1-20250805", "claude-haiku-4-5-20251001",
    "claude-3-5-haiku-20241022",
    
    # Cohere Models
    "command-r-08-2024",
    
    # DeepSeek Models
    "deepseek-reasoner", "deepseek-chat",
    
    # GoogleAI Models
    "gemini-3-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash",
    
    # Mistral Models
    "magistral-small-latest", "magistral-medium-latest", "ministral-14b-latest",
    "open-mistral-nemo", "mistral-small-latest", "mistral-medium-latest", "mistral-large-latest",
    
    # OpenAI Models
    "gpt-5.1-codex-mini", "gpt-5.1-codex", "o4-mini", "o3-mini",
    "gpt-5.2-pro", "gpt-5.2", "gpt-5.1", "gpt-5-nano", "gpt-5-mini",
    "gpt-5-chat-latest", "gpt-5", "gpt-4o-mini", "gpt-4o",
    "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1", "gpt-4-turbo", "gpt-3.5-turbo",
    "o4-mini-deep-research", "o3-pro", "o3-deep-research", "o3",
    
    # Perplexity Models
    "sonar-reasoning-pro", "sonar-reasoning", "sonar-pro", "sonar-deep-research", "sonar",
    
    # xAI Models
    "grok-4-fast-reasoning", "grok-4-fast-non-reasoning", "grok-4-0709", "grok-3-mini", "grok-3",
    
    # Extra Models
    "meta/meta-llama-3.1-405b-instruct", "meta/meta-llama-3-70b-instruct",
    "meta/llama-4-scout-instruct", "meta/llama-4-maverick-instruct", "meta/llama-2-70b-chat",
    "openai/gpt-oss-20b", "openai/gpt-oss-120b"
]

# Models that support image input (Multimodal/Vision)
# Based on common knowledge of 2026 model capabilities listed in doc
VISION_SUPPORTED_MODELS = [
    "gpt-4o", 
    "gpt-4o-mini", 
    "gpt-4-turbo", 
    "claude-sonnet-4-5-20250929",
    "gemini-3-pro-preview",
    "gemini-2.5-flash"
]

# Models specialized in Image Generation (Text-to-Image)
# As per "Non-Streaming Features Example" and "Response Payload" in doc
IMAGE_GENERATION_MODELS = [
    "black-forest-labs/flux-schnell",
    "magic-art",
    "stable-image"
]