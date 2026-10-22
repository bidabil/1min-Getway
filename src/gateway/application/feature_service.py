"""Generic access to every 1min.ai AI feature, with optional server-side waiting."""

import asyncio
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from ..domain.errors import InvalidRequestError, NotFoundError, UpstreamError, UpstreamTimeoutError
from ..domain.features import FeatureRecord, FeatureRequest, FeatureSpec, FeatureStatus
from ..domain.models import ModelInfo
from .ports import FeatureCatalogPort, FeaturePort, ModelCatalogPort

_FEATURE_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class FeatureService:
    def __init__(
        self,
        port: FeaturePort,
        catalog: FeatureCatalogPort,
        *,
        model_catalog: ModelCatalogPort | None = None,
        poll_interval_s: float = 2.0,
        max_poll_interval_s: float = 10.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._port = port
        self._catalog = catalog
        self._model_catalog = model_catalog
        self._poll_interval = poll_interval_s
        self._max_poll_interval = max_poll_interval_s
        self._sleep = sleep
        self._clock = clock

    def catalog(self) -> Sequence[FeatureSpec]:
        return self._catalog.list()

    def describe(self, feature_type: str) -> FeatureSpec:
        spec = self._catalog.get(feature_type.upper())
        if spec is None:
            raise NotFoundError(f"Unknown feature type '{feature_type}'.", param="feature_type")
        return spec

    async def models(self, feature_type: str) -> Sequence[ModelInfo]:
        """Models 1min.ai currently accepts for a feature (live catalog)."""
        feature = feature_type.strip().upper()
        if not _FEATURE_TYPE.match(feature):
            raise InvalidRequestError(
                f"Invalid feature type '{feature_type}'.", param="feature_type"
            )
        if self._model_catalog is None:
            return ()
        return await self._model_catalog.models_for(feature)

    async def run(self, request: FeatureRequest) -> FeatureRecord:
        return await self._port.run(self._normalize(request))

    async def result(self, record_id: str) -> FeatureRecord:
        record = await self._port.get_result(record_id)
        if record is None:
            raise NotFoundError(f"No feature result with id '{record_id}'.", param="id")
        return record

    async def run_and_wait(self, request: FeatureRequest, *, timeout_s: float) -> FeatureRecord:
        """Start the feature asynchronously upstream and poll until it finishes or times out.

        Returns the last known record; it is still PROCESSING when the timeout is reached.
        """
        record = await self.run(replace(request, run_async=True))
        deadline = self._clock() + timeout_s
        interval = self._poll_interval
        while not record.done:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            await self._sleep(min(interval, remaining))
            record = await self.result(record.id)
            interval = min(interval * 1.5, self._max_poll_interval)
        return record

    def _normalize(self, request: FeatureRequest) -> FeatureRequest:
        feature_type = request.type.strip().upper()
        if not _FEATURE_TYPE.match(feature_type):
            raise InvalidRequestError(
                f"Invalid feature type '{request.type}'.", param="feature_type"
            )
        if not request.model.strip():
            raise InvalidRequestError("'model' is required.", param="model")
        conversation_id = request.conversation_id
        spec = self._catalog.get(feature_type)
        if conversation_id is None and spec is not None and spec.conversation_id == "type":
            conversation_id = feature_type
        return replace(request, type=feature_type, conversation_id=conversation_id)


def require_success(record: FeatureRecord) -> FeatureRecord:
    if record.status is FeatureStatus.FAILED:
        message = "The 1min.ai feature failed."
        if record.error and isinstance(record.error.get("message"), str):
            message = f"The 1min.ai feature failed: {record.error['message']}"
        raise UpstreamError(message, code="feature_failed")
    if record.status is FeatureStatus.PROCESSING:
        raise UpstreamTimeoutError(
            f"The job is still processing. Poll GET /v1/features/results/{record.id} for the result.",
            code="feature_still_processing",
        )
    return record
