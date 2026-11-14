"""Configuration from environment variables. Never logs secret values."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import VbeeConfigError

DEFAULT_API_BASE = "https://api.vbee.vn"
VOICES_BASE = "https://vbee.vn/api/public/v1"


@dataclass(frozen=True)
class Settings:
    app_id: str | None
    token: str | None
    api_base: str
    webhook_url: str | None

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.token)


def load_settings() -> Settings:
    return Settings(
        app_id=os.environ.get("VBEE_APP_ID") or None,
        token=os.environ.get("VBEE_TOKEN") or None,
        api_base=(os.environ.get("VBEE_API_BASE") or DEFAULT_API_BASE).rstrip("/"),
        webhook_url=os.environ.get("VBEE_WEBHOOK_URL") or None,
    )


def require_credentials(settings: Settings) -> Settings:
    missing = []
    if not settings.app_id:
        missing.append("VBEE_APP_ID")
    if not settings.token:
        missing.append("VBEE_TOKEN")
    if missing:
        raise VbeeConfigError(
            code="MISSING_CREDENTIALS",
            message=(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them before calling vbee tools."
            ),
        )
    return settings
