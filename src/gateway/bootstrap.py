"""Composition root: builds the adapters and services from the settings."""

from dataclasses import dataclass

import httpx

from . import __version__
from .application.access import ClientAccess
from .application.chat_service import ChatService, ChatSettings
from .application.feature_service import FeatureService
from .application.media_service import AudioService, FileService, ImageService
from .application.model_directory import ModelDirectory
from .config import Settings
from .domain.services.sampling import SamplingPolicy
from .infrastructure.observability.metrics import GatewayMetrics
from .infrastructure.one_min.assets import AssetStore
from .infrastructure.one_min.catalog import StaticFeatureCatalog
from .infrastructure.one_min.downloads import ResultDownloader
from .infrastructure.one_min.features import FeatureClient
from .infrastructure.one_min.http import OneMinHttp
from .infrastructure.one_min.legacy_chat import LegacyChatBackend
from .infrastructure.one_min.model_catalog import PublicModelCatalog
from .infrastructure.one_min.native_chat import NativeChatBackend, NativeModelList
from .infrastructure.security.api_keys import StaticApiKeyVerifier, load_key_entries
from .infrastructure.security.rate_limit import TokenBucketLimiter


class ConfigurationError(RuntimeError):
    """The gateway cannot start with the current configuration."""


@dataclass
class Container:
    settings: Settings
    access: ClientAccess
    models: ModelDirectory
    chat: ChatService
    features: FeatureService
    images: ImageService
    audio: AudioService
    files: FileService
    metrics: GatewayMetrics
    http_client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def build_container(
    settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
) -> Container:
    api_key = settings.one_min_api_key.get_secret_value().strip()
    if not api_key:
        raise ConfigurationError(
            "ONE_MIN_API_KEY is not set: the gateway needs your 1min.ai API key."
        )
    try:
        key_entries = load_key_entries(settings.gateway_api_keys, settings.gateway_api_keys_file)
        aliases = settings.aliases()
        output_caps = settings.output_caps()
    except (OSError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc
    if not key_entries:
        raise ConfigurationError(
            "No gateway API key configured. Create one with `python -m gateway.cli create-key <name>` "
            "and set GATEWAY_API_KEYS."
        )

    http_client = httpx.AsyncClient(
        transport=transport,
        headers={"User-Agent": f"1min-gateway/{__version__}"},
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=40),
        follow_redirects=False,
        trust_env=False,
    )
    one_min = OneMinHttp(
        http_client,
        base_url=settings.one_min_base_url,
        api_key=api_key,
        connect_timeout_s=settings.connect_timeout_s,
    )
    catalog = PublicModelCatalog(one_min, ttl_s=settings.models_cache_ttl_s)
    models = ModelDirectory(
        NativeModelList(one_min),
        catalog,
        extra_legacy_models=settings.legacy_models(),
        aliases=aliases,
        ttl_s=settings.models_cache_ttl_s,
    )
    assets = AssetStore(one_min, timeout_s=settings.feature_timeout_s)
    features = FeatureService(
        FeatureClient(one_min, timeout_s=settings.feature_timeout_s),
        StaticFeatureCatalog.load_default(),
        model_catalog=catalog,
        poll_interval_s=settings.feature_poll_interval_s,
    )
    downloader = ResultDownloader(
        http_client, allowed_host_suffixes=settings.download_host_suffixes()
    )
    chat = ChatService(
        native=NativeChatBackend(one_min, timeout_s=settings.chat_timeout_s),
        legacy=LegacyChatBackend(one_min, timeout_s=settings.chat_timeout_s),
        models=models,
        assets=assets,
        policy=SamplingPolicy(
            drop_restricted=settings.drop_unsupported_sampling_params,
            restricted_patterns=settings.restricted_models(),
            output_caps=output_caps,
            default_output_cap=settings.default_max_output_tokens_cap,
        ),
        settings=ChatSettings(
            web_search_suffix=settings.web_search_suffix,
            max_inline_bytes=settings.max_inline_file_bytes,
            max_legacy_images=settings.legacy_max_images,
            strip_crawl_notices=settings.strip_crawl_notices,
        ),
    )
    return Container(
        settings=settings,
        access=ClientAccess(
            StaticApiKeyVerifier(key_entries), TokenBucketLimiter(settings.rate_limit_rpm)
        ),
        models=models,
        chat=chat,
        features=features,
        images=ImageService(
            features,
            downloader,
            timeout_s=settings.feature_timeout_s,
            max_download_bytes=settings.max_download_bytes,
        ),
        audio=AudioService(
            features,
            downloader,
            timeout_s=settings.feature_timeout_s,
            max_download_bytes=settings.max_download_bytes,
        ),
        files=FileService(assets, max_bytes=settings.max_file_bytes),
        metrics=GatewayMetrics(),
        http_client=http_client,
    )
