"""Translate OpenAI speech parameters into the TEXT_TO_SPEECH promptObject of each provider."""

from typing import Any

from ..media import SpeechRequest


def speech_prompt_object(request: SpeechRequest) -> dict[str, Any]:
    if request.model.lower().startswith("elevenlabs"):
        prompt_object: dict[str, Any] = {"text": request.text, "voice_id": request.voice}
    else:
        prompt_object = {
            "text": request.text,
            "voice": request.voice,
            "response_format": request.response_format,
        }
        if request.speed is not None:
            prompt_object["speed"] = request.speed
    prompt_object.update(request.extra)
    return prompt_object
