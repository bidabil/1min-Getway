"""Catalog of chat models: native models, legacy (Chat with AI) models and aliases.

Both lists are fetched from 1min.ai and cached; each refreshes independently so that one
failing source never hides the other.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field, replace

from ..domain.errors import GatewayError
from ..domain.models import Backend, ModelInfo
from ..domain.services.routing import ModelAlias, ModelDirectorySnapshot, short_name_index
from .ports import ModelCatalogPort, NativeModelSource

logger = logging.getLogger(__name__)

LEGACY_CHAT_FEATURE = "UNIFY_CHAT_WITH_AI"
_RETRY_AFTER_FAILURE_S = 30.0


@dataclass
class _CachedList:
    name: str
    loader: Callable[[], Awaitable[Sequence[ModelInfo]]]
    models: tuple[ModelInfo, ...] = ()
    known: bool = False
    next_refresh: float | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def refresh_if_due(self, clock: Callable[[], float], ttl: float) -> None:
        if self.next_refresh is not None and clock() < self.next_refresh:
            return
        async with self.lock:
            if self.next_refresh is not None and clock() < self.next_refresh:
                return
            try:
                models = await self.loader()
            except GatewayError as exc:
                logger.warning(
                    "Could not refresh the %s model list: %s",
                    self.name,
                    exc.message,
                    extra={"error_code": exc.code},
                )
                self.next_refresh = clock() + _RETRY_AFTER_FAILURE_S
                return
            self.models = tuple(models)
            self.known = True
            self.next_refresh = clock() + ttl


class ModelDirectory:
    def __init__(
        self,
        native_source: NativeModelSource,
        catalog: ModelCatalogPort,
        *,
        extra_legacy_models: Sequence[str],
        aliases: Sequence[ModelAlias],
        ttl_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._native = _CachedList("native", native_source.list_models)
        self._legacy = _CachedList("legacy", lambda: catalog.models_for(LEGACY_CHAT_FEATURE))
        self._extra_legacy = tuple(dict.fromkeys(extra_legacy_models))
        self._aliases = tuple(aliases)
        self._ttl = ttl_s
        self._clock = clock

    async def snapshot(self) -> ModelDirectorySnapshot:
        await asyncio.gather(
            self._native.refresh_if_due(self._clock, self._ttl),
            self._legacy.refresh_if_due(self._clock, self._ttl),
        )
        native = frozenset(model.id for model in self._native.models)
        legacy = frozenset(model.id for model in self._legacy.models) | frozenset(
            self._extra_legacy
        )
        return ModelDirectorySnapshot(
            native=native,
            legacy=legacy,
            aliases=self._aliases,
            native_known=self._native.known,
            legacy_known=self._legacy.known,
            text_only=frozenset(model.id for model in self._legacy.models if model.vision is False),
            short_names=short_name_index(native | legacy),
        )

    async def list_models(self) -> list[ModelInfo]:
        snapshot = await self.snapshot()
        legacy_by_id = {model.id: model for model in self._legacy.models}
        models: list[ModelInfo] = []
        for model in self._native.models:
            legacy = legacy_by_id.get(model.id)
            # Images are always served by the legacy API: report its vision capability.
            models.append(replace(model, vision=legacy.vision if legacy else False))
        models.extend(model for model in self._legacy.models if model.id not in snapshot.native)
        known = {model.id for model in models}
        models.extend(
            ModelInfo(id=model_id, backend=Backend.LEGACY)
            for model_id in self._extra_legacy
            if model_id not in known
        )
        known.update(self._extra_legacy)
        for alias in self._aliases:
            if alias.is_pattern or alias.pattern in known:
                continue
            backend = Backend.NATIVE if alias.target in snapshot.native else Backend.LEGACY
            models.append(
                ModelInfo(
                    id=alias.pattern,
                    backend=backend,
                    owned_by="1min-gateway",
                    alias_of=alias.target,
                )
            )
        return models
