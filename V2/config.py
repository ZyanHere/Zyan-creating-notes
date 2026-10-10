"""Settings, validated at import, failing loudly rather than late.

Two rules this file exists to enforce.

**Validated at startup, not at first use.** A malformed DATABASE_URL should stop the
process with a sentence naming the variable, not surface forty seconds later as a
connection error inside a 342-second plan turn. So every field is typed and every
constraint is declared; pydantic-settings raises before the app exists.

**Nothing here is a tuning knob with a shrug attached.** Where a default exists it has
a reason and the reason is in the comment, because V1's two most common confusions
were "which model is it using" and "can it render", and both were invisible until the
banner printed them.

`core/` may not import this. A pure function that reads settings is not pure, and the
boundary test enforces it — settings are passed in as values.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Database(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    url: PostgresDsn = Field(
        default=PostgresDsn("postgresql://localhost:5432/mynotes_v2"),
        description="validated as a real DSN, so a typo fails here and not at first query",
    )
    # UNKNOWN until measured on the target instance — a starting value, not a finding.
    pool_size: int = Field(default=20, ge=1, le=200)
    pool_timeout_s: float = Field(default=10.0, gt=0)


class Provider(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_", extra="ignore")

    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    # Pinned into every derivation environment, so changing it changes identity.
    # This is not a casual setting.
    model_id: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    # One section call measured ~65s. 120s is the ATTEMPT ceiling, not the total — the
    # total is a Task budget, and that distinction is what V1 lacked when one case
    # burned 11,537 seconds across four calls.
    attempt_deadline_s: int = Field(default=120, ge=5, le=600)

    # Concurrent provider calls, acquired as a FIFO slot inside MODEL_CALL. A declared
    # cap that nothing acquires is a cap in a table.
    concurrency: int = Field(default=8, ge=1, le=64)

    # Per fixed UTC hour, enforced by a conditional upsert at admission. A boundary can
    # admit up to 2x across a rolling hour; that is accepted for a coarse spend guard.
    tenant_calls_per_hour: int = Field(default=200, ge=1)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


class Server(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    # A plan turn runs for minutes. Uvicorn's default of 5s closes the connection
    # underneath it and the browser reports "Failed to fetch" — a network error for a
    # working server still thinking. This is not a tuning knob.
    timeout_keep_alive: int = Field(default=900, ge=60)

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    env: Literal["local", "ci", "staging", "production"] = "local"

    database: Database = Field(default_factory=Database)
    provider: Provider = Field(default_factory=Provider)
    server: Server = Field(default_factory=Server)

    # A shared code is NOT auth and must not be described as auth. It keeps a public
    # URL from draining the quota; nothing more. Real auth is gated on whether this
    # deployment is a portfolio link or a product.
    access_code: str = ""

    @property
    def provider_configured(self) -> bool:
        return self.provider.configured

    def require_production_ready(self) -> None:
        """Called by the entry point before binding a non-local interface.

        Fails with the whole list rather than the first problem, because discovering
        these one deploy at a time is how a Friday evening goes wrong.
        """
        if self.env == "local":
            return
        problems: list[str] = []
        if not self.provider.configured:
            problems.append("PROVIDER_API_KEY is empty")
        if not self.access_code:
            problems.append("ACCESS_CODE is empty and the interface is not local")
        if any("localhost" in origin for origin in self.server.cors_origins):
            problems.append("CORS_ORIGINS still contains localhost")
        if problems:
            raise RuntimeError(
                f"env={self.env} but the configuration is not deployable:\n  - "
                + "\n  - ".join(problems)
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Resolved once. Cached so tests can clear it: `get_settings.cache_clear()`."""
    return Settings()


settings = get_settings()
