"""Generic access to every 1min.ai AI feature (image, audio, video, writing, code tools)."""

import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ....bootstrap import Container
from ....domain.clients import ClientIdentity
from ....domain.errors import InvalidRequestError, NotFoundError
from ....domain.features import FeatureRecord, FeatureRequest, FeatureSpec, FeatureStatus
from ..dependencies import client_identity, get_container, json_body
from ..translators.common import as_mapping, as_str

router = APIRouter(tags=["Features"])

_RECORD_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/v1/features")
async def list_features(
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    return {"object": "list", "data": [spec_body(spec) for spec in container.features.catalog()]}


@router.get("/v1/features/results/{record_id}")
async def get_feature_result(
    record_id: str,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> JSONResponse:
    if not _RECORD_ID.match(record_id):
        raise InvalidRequestError("Invalid result id.", param="record_id")
    return record_response(await container.features.result(record_id))


@router.get("/v1/features/{feature_type}/models")
async def feature_models(
    feature_type: str,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    """Models 1min.ai currently accepts for this feature (live catalog)."""
    models = await container.features.models(feature_type)
    return {
        "object": "list",
        "data": [
            {
                "id": model.id,
                "name": model.name,
                "provider": model.owned_by,
                "vision": model.vision,
                "max_output_tokens": model.max_output_tokens,
                "deprecation_date": model.deprecation_date,
            }
            for model in models
        ],
    }


@router.get("/v1/features/{feature_type}")
async def describe_feature(
    feature_type: str,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    return spec_body(container.features.describe(feature_type))


@router.post("/v1/features/{feature_type}")
async def run_feature(
    feature_type: str,
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> JSONResponse:
    body = await json_body(request)
    mode = body.get("mode", "wait")
    if mode not in ("sync", "async", "wait"):
        raise InvalidRequestError("'mode' must be 'sync', 'async' or 'wait'.", param="mode")
    prompt_object = as_mapping(body.get("prompt_object"), "prompt_object")
    if prompt_object is None:
        raise InvalidRequestError("'prompt_object' is required.", param="prompt_object")
    model = as_str(body.get("model"), "model") or _default_model(container, feature_type)
    feature = FeatureRequest(
        type=feature_type,
        model=model,
        prompt_object=dict(prompt_object),
        run_async=mode == "async",
        conversation_id=as_str(body.get("conversation_id"), "conversation_id"),
        extra=dict(as_mapping(body.get("extra"), "extra") or {}),
    )
    if mode == "wait":
        timeout = body.get("timeout_s", container.settings.feature_timeout_s)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int | float)
            or not 1 <= timeout <= 3600
        ):
            raise InvalidRequestError(
                "'timeout_s' must be a number between 1 and 3600.", param="timeout_s"
            )
        record = await container.features.run_and_wait(feature, timeout_s=float(timeout))
    else:
        record = await container.features.run(feature)
    return record_response(record)


def _default_model(container: Container, feature_type: str) -> str:
    try:
        spec: FeatureSpec | None = container.features.describe(feature_type)
    except NotFoundError:
        spec = None
    if spec is None or not spec.models:
        raise InvalidRequestError("'model' is required for this feature.", param="model")
    return spec.models[0]


def record_body(record: FeatureRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "object": "feature.result",
        "type": record.type,
        "model": record.model,
        "status": record.status.value,
        "results": list(record.results),
        "temporary_url": record.temporary_url,
        "created_at": record.created_at,
        "error": dict(record.error) if record.error else None,
    }


def record_response(record: FeatureRecord) -> JSONResponse:
    status = 202 if record.status is FeatureStatus.PROCESSING else 200
    return JSONResponse(record_body(record), status_code=status)


def spec_body(spec: FeatureSpec) -> dict[str, Any]:
    return {
        "type": spec.type,
        "object": "feature",
        "category": spec.category,
        "title": spec.title,
        "description": spec.description,
        "models": list(spec.models),
        "long_running": spec.long_running,
        "docs_url": spec.docs_url,
        "fields": [
            {
                key: value
                for key, value in (
                    ("name", field.name),
                    ("type", field.type),
                    ("required", field.required),
                    ("description", field.description),
                    ("enum", list(field.enum) or None),
                    ("default", field.default),
                )
                if value is not None
            }
            for field in spec.fields
        ],
    }
