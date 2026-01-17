"""
Domain models configuration for 1min-Gateway.
Defines supported AI models for Chat, Vision, and Image Generation.
"""

# Complete list of available text/chat models via 1min.ai
ALL_ONE_MIN_AVAILABLE_MODELS = [
    # OpenAI Next-Gen & Standard
    "gpt-5-nano", "gpt-5", "gpt-5-mini", "o3-mini", "o1-preview", "o1-mini", 
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    
    # DeepSeek
    "deepseek-chat", "deepseek-reasoner",
    
    # Anthropic Claude
    "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20240620", 
    "claude-3-opus-20240229", "claude-3-sonnet-20240229", 
    "claude-3-haiku-20240307", "claude-2.1", "claude-instant-1.2",
    
    # Google Gemini
    "gemini-1.0-pro", "gemini-1.5-pro", "gemini-1.5-flash",
    
    # Mistral AI
    "mistral-large-latest", "mistral-small-latest", "mistral-nemo",
    "open-mistral-7b",
    
    # Meta Llama
    "meta/llama-2-70b-chat", "meta/meta-llama-3-70b-instruct", 
    "meta/meta-llama-3.1-405b-instruct",
    
    # Others & Experimental
    "command", "gpt-o1-pro", "gpt-o4-mini", "gpt-4.1-nano", "gpt-4.1-mini"
]

# Models that support image input (Multimodal/Vision)
VISION_SUPPORTED_MODELS = [
    "gpt-4o", 
    "gpt-4o-mini", 
    "gpt-4-turbo", 
    "claude-3-5-sonnet-20240620",
    "gemini-1.5-pro",
    "gemini-1.5-flash"
]

# Models specialized in Image Generation (Text-to-Image)
IMAGE_GENERATION_MODELS = [
    # Stable Diffusion & Variants
    "stable-image", "stable-diffusion-xl-1024-v1-0", "stable-diffusion-v1-6",
    
    # Specialized Tools
    "esrgan-v1-x2plus", "clipdrop", "midjourney", "midjourney_6_1",
    
    # Leonardo AI (UUID Identifiers)
    "6b645e3a-d64f-4341-a6d8-7a3690fbf042", # LEONARDO_PHOENIX
    "b24e16ff-06e3-43eb-8d33-4416c2d75876", # LEONARDO_LIGHTNING_XL
    "e71a1c2f-4f80-4800-934f-2c68979d8cc8", # LEONARDO_ANIME_XL
    "1e60896f-3c26-4296-8ecc-53e2afecc132", # LEONARDO_DIFFUSION_XL
    "aa77f04e-3eec-4034-9c07-d0f619684628", # LEONARDO_KINO_XL
    "2067ae52-33fd-4a82-bb92-c2c55e7d2786", # LEONARDO_ALBEDO_BASE_XL
    
    # Flux
    "black-forest-labs/flux-schnell"
]