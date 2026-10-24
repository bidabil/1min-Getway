"""Translate OpenAI image parameters into model-specific 1min.ai promptObject fields.

1min.ai image models express dimensions differently: gpt-image takes `size` ("1536x1024"),
Flux / Stable Diffusion / Ideogram take `aspect_ratio` ("16:9") and Magic Art takes
`aspect_width` / `aspect_height`. Model-specific fields can always be passed explicitly
through `extra`, which overrides anything derived here.
"""

import math
from collections.abc import Mapping
from fnmatch import fnmatchcase
from typing import Any, Literal

from ..errors import InvalidRequestError
from ..media import ImageEditRequest, ImageGenerationRequest, ImageVariationRequest

SizeStyle = Literal["size", "aspect_ratio", "aspect_wh", "none"]

_SIZE_STYLES: tuple[tuple[str, SizeStyle], ...] = (
    ("gpt-image*", "size"),
    ("dall-e*", "size"),
    ("magic-art*", "aspect_wh"),
    ("black-forest-labs/*", "aspect_ratio"),
    ("*flux*", "aspect_ratio"),
    ("*stable-diffusion*", "aspect_ratio"),
    ("stable-image*", "aspect_ratio"),
    ("*sdxl*", "aspect_ratio"),
    ("*ideogram*", "aspect_ratio"),
    ("*recraft*", "aspect_ratio"),
    ("*qwen*image*", "aspect_ratio"),
    ("*gemini*image*", "aspect_ratio"),
)

ASPECT_RATIOS = ("1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4")
MAGIC_ART_RATIOS = ((1, 1), (4, 5), (2, 3), (4, 7), (5, 4), (3, 2), (7, 4))

# Fields some models require; used when the client did not provide them.
_REQUIRED_DEFAULTS: tuple[tuple[str, Mapping[str, Any]], ...] = (
    ("gpt-image-2*", {"size": "1024x1024", "quality": "medium"}),
)
_GPT_IMAGE_QUALITY = {"standard": "medium", "hd": "high"}


def size_style(model: str) -> SizeStyle:
    lowered = model.lower()
    for pattern, style in _SIZE_STYLES:
        if fnmatchcase(lowered, pattern):
            return style
    return "none"


def generation_prompt_object(request: ImageGenerationRequest) -> dict[str, Any]:
    prompt_object: dict[str, Any] = {"prompt": request.prompt}
    style = size_style(request.model)
    prompt_object.update(_dimension_fields(request.size, style))
    lowered = request.model.lower()

    if style == "size":
        if request.n is not None:
            prompt_object["n"] = request.n
        if request.quality and request.quality != "auto":
            quality = request.quality
            if lowered.startswith("gpt-image"):
                quality = _GPT_IMAGE_QUALITY.get(quality, quality)
            prompt_object["quality"] = quality
        if request.style and (lowered.startswith("gpt-image-1") or lowered.startswith("dall-e-3")):
            prompt_object["style"] = request.style
        if request.background and lowered.startswith("gpt-image"):
            prompt_object["background"] = request.background
        if request.output_format and lowered.startswith("gpt-image"):
            prompt_object["output_format"] = request.output_format

    _apply_required_defaults(lowered, prompt_object)
    prompt_object.update(request.extra)
    return prompt_object


def edit_prompt_object(request: ImageEditRequest) -> dict[str, Any]:
    prompt_object: dict[str, Any] = {"imageUrl": request.image, "prompt": request.prompt}
    if request.mask:
        prompt_object["maskUrl"] = request.mask
    style = size_style(request.model)
    prompt_object.update(_dimension_fields(request.size, style))
    if style == "size":
        if request.n is not None:
            prompt_object["n"] = request.n
        if request.quality and request.quality != "auto":
            prompt_object["quality"] = _GPT_IMAGE_QUALITY.get(request.quality, request.quality)
    prompt_object.update(request.extra)
    return prompt_object


def variation_prompt_object(request: ImageVariationRequest) -> dict[str, Any]:
    prompt_object: dict[str, Any] = {"imageUrl": request.image}
    style = size_style(request.model)
    prompt_object.update(_dimension_fields(request.size, style))
    if request.n is not None and style in ("size", "aspect_wh"):
        prompt_object["n"] = request.n
    prompt_object.update(request.extra)
    return prompt_object


def _dimension_fields(size: str | None, style: SizeStyle) -> dict[str, Any]:
    if not size or size == "auto" or style == "none":
        return {}
    ratio = _parse_ratio(size)
    if style == "size":
        if "x" not in size.lower():
            raise InvalidRequestError(
                f"Invalid size '{size}': this model expects WIDTHxHEIGHT (e.g. 1024x1024).",
                param="size",
            )
        return {"size": size.lower()}
    if style == "aspect_ratio":
        return {"aspect_ratio": _nearest_label(ratio)}
    width, height = min(
        MAGIC_ART_RATIOS, key=lambda pair: abs(math.log(pair[0] / pair[1]) - math.log(ratio))
    )
    return {"aspect_width": width, "aspect_height": height}


def _parse_ratio(size: str) -> float:
    separator = "x" if "x" in size.lower() else ":"
    try:
        width_text, height_text = size.lower().split(separator, 1)
        width, height = float(width_text), float(height_text)
    except ValueError:
        raise InvalidRequestError(
            f"Invalid size '{size}': expected WIDTHxHEIGHT (e.g. 1024x1024) or W:H.", param="size"
        ) from None
    if width <= 0 or height <= 0:
        raise InvalidRequestError(f"Invalid size '{size}'.", param="size")
    return width / height


def _nearest_label(ratio: float) -> str:
    def distance(label: str) -> float:
        width, height = (float(value) for value in label.split(":"))
        return abs(math.log(width / height) - math.log(ratio))

    return min(ASPECT_RATIOS, key=distance)


def _apply_required_defaults(model: str, prompt_object: dict[str, Any]) -> None:
    for pattern, defaults in _REQUIRED_DEFAULTS:
        if fnmatchcase(model, pattern):
            for key, value in defaults.items():
                prompt_object.setdefault(key, value)
