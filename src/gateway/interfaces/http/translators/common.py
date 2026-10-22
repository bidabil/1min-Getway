"""Helpers shared by the wire translators."""

import json
from collections.abc import Mapping
from typing import Any, NoReturn

from ....domain.errors import InvalidRequestError


def invalid(message: str, param: str | None = None) -> NoReturn:
    raise InvalidRequestError(message, param=param)


def as_str(value: Any, param: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            invalid(f"'{param}' is required.", param)
        return None
    if not isinstance(value, str):
        invalid(f"'{param}' must be a string.", param)
    return value


def as_float(value: Any, param: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        invalid(f"'{param}' must be a number.", param)
    return float(value)


def as_int(value: Any, param: str, *, minimum: int | None = None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        invalid(f"'{param}' must be an integer.", param)
    if minimum is not None and value < minimum:
        invalid(f"'{param}' must be >= {minimum}.", param)
    return value


def as_bool(value: Any, param: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        invalid(f"'{param}' must be a boolean.", param)
    return value


def as_mapping(value: Any, param: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        invalid(f"'{param}' must be an object.", param)
    return value


def as_stop(value: Any, param: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    invalid(f"'{param}' must be a string or a list of strings.", param)


def json_arguments(value: Any) -> str:
    """Tool arguments as JSON text (clients sometimes send an object instead of a string)."""
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def json_object(arguments: str) -> dict[str, Any]:
    try:
        value = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def sse_frame(data: Any, event: str | None = None) -> str:
    payload = (
        data
        if isinstance(data, str)
        else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {payload}\n\n"
