"""Runtime configuration, read from environment variables and an optional `.env` file."""

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .domain.services.routing import ModelAlias
from .domain.services.sampling import DEFAULT_RESTRICTED_PATTERNS, OutputCap


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- 1min.ai -------------------------------------------------------------------------
    one_min_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("ONE_MIN_API_KEY", "ONE_MIN_AI_API_KEY"),
    )
    one_min_base_url: str = "https://api.1min.ai"
    chat_timeout_s: float = 150.0
    feature_timeout_s: float = 300.0
    feature_poll_interval_s: float = 2.0
    connect_timeout_s: float = 10.0

    # --- Gateway clients (agents) --------------------------------------------------------
    gateway_api_keys: str = ""  # "name:sha256hex[:rpm],..." (see `python -m gateway.cli`)
    gateway_api_keys_file: str | None = None
    rate_limit_rpm: int = 60  # per client key; 0 disables

    # --- Server --------------------------------------------------------------------------
    app_env: str = "production"
    host: str = "0.0.0.0"  # noqa: S104 - container default; restrict with HOST
    port: int = 5001
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    max_request_body_mb: int = 32
    cors_origins: str = ""
    docs_enabled: bool = False
    metrics_token: SecretStr | None = None

    # --- Models and routing --------------------------------------------------------------
    models_cache_ttl_s: float = 600.0
    # Chat with AI models are read from 1min.ai's catalog; list extra ids here if needed.
    legacy_chat_models: str = ""
    model_aliases: str = ""  # "client-model=1min-model,claude-*=gpt-5.1"
    web_search_suffix: str = ":online"
    drop_unsupported_sampling_params: bool = True
    sampling_restricted_models: str = ",".join(DEFAULT_RESTRICTED_PATTERNS)
    max_output_tokens_caps: str = "gpt-4o*=16384"
    default_max_output_tokens_cap: int = 32768
    strip_crawl_notices: bool = True
    legacy_max_images: int = 10

    # --- Files and media -----------------------------------------------------------------
    max_file_mb: int = 50
    max_inline_file_mb: int = 20
    max_download_mb: int = 100
    download_allowed_hosts: str = ""  # optional host suffix allowlist for result downloads
    default_image_model: str = "gpt-image-1"
    default_tts_model: str = "tts-1"
    default_stt_model: str = "whisper-1"
    default_tool_model: str = "gpt-4o-mini"  # used by MCP tools that need a chat model

    # --- MCP -----------------------------------------------------------------------------
    mcp_enabled: bool = True
    mcp_allowed_hosts: str = ""  # Host headers accepted by /mcp (DNS-rebinding protection)

    # --- Derived values ------------------------------------------------------------------

    def legacy_models(self) -> tuple[str, ...]:
        return split_csv(self.legacy_chat_models)

    def aliases(self) -> tuple[ModelAlias, ...]:
        aliases: list[ModelAlias] = []
        for item in split_csv(self.model_aliases):
            source, separator, target = item.partition("=")
            if not separator or not source.strip() or not target.strip():
                raise ValueError(f"Invalid MODEL_ALIASES entry '{item}': expected alias=target.")
            aliases.append(ModelAlias(source.strip(), target.strip()))
        return tuple(aliases)

    def output_caps(self) -> tuple[OutputCap, ...]:
        caps: list[OutputCap] = []
        for item in split_csv(self.max_output_tokens_caps):
            pattern, separator, value = item.partition("=")
            if not separator or not value.strip().isdigit():
                raise ValueError(
                    f"Invalid MAX_OUTPUT_TOKENS_CAPS entry '{item}': expected pattern=number."
                )
            caps.append(OutputCap(pattern.strip(), int(value)))
        return tuple(caps)

    def restricted_models(self) -> tuple[str, ...]:
        return split_csv(self.sampling_restricted_models)

    def cors_origin_list(self) -> tuple[str, ...]:
        return split_csv(self.cors_origins)

    def download_host_suffixes(self) -> tuple[str, ...]:
        return tuple(host.lower().lstrip(".") for host in split_csv(self.download_allowed_hosts))

    def mcp_host_list(self) -> tuple[str, ...]:
        return split_csv(self.mcp_allowed_hosts)

    @property
    def max_request_body_bytes(self) -> int:
        return self.max_request_body_mb * 1024 * 1024

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def max_inline_file_bytes(self) -> int:
        return self.max_inline_file_mb * 1024 * 1024

    @property
    def max_download_bytes(self) -> int:
        return self.max_download_mb * 1024 * 1024


def split_csv(value: str) -> tuple[str, ...]:
    """Split a comma- or newline-separated setting, ignoring blanks and duplicates."""
    items = (item.strip() for chunk in value.splitlines() for item in chunk.split(","))
    return tuple(dict.fromkeys(item for item in items if item))
