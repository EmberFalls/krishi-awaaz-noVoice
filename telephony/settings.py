"""Configuration for the optional live telephony server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceSettings:
    public_base_url: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    sarvam_api_key: str | None
    default_scenario_id: str
    validate_twilio_requests: bool = True
    database_url: str | None = None

    @classmethod
    def from_environment(cls) -> VoiceSettings:
        return cls(
            public_base_url=os.getenv("VOICE_PUBLIC_BASE_URL"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            sarvam_api_key=os.getenv("SARVAM_API_KEY"),
            default_scenario_id=os.getenv("VOICE_SCENARIO_ID", "nashik-onion-001"),
            validate_twilio_requests=os.getenv("VOICE_SKIP_TWILIO_VALIDATION", "").lower()
            not in {"1", "true", "yes"},
            database_url=os.getenv("DATABASE_URL"),
        )

    @property
    def missing_live_settings(self) -> list[str]:
        values = {
            "VOICE_PUBLIC_BASE_URL": self.public_base_url,
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "SARVAM_API_KEY": self.sarvam_api_key,
        }
        return [name for name, value in values.items() if not value]

    def public_url(self, path: str) -> str:
        if not self.public_base_url:
            raise RuntimeError("VOICE_PUBLIC_BASE_URL is required for live voice calls.")
        return f"{self.public_base_url.rstrip('/')}/{path.lstrip('/')}"
