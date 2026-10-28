"""Settings, read from environment variables (or a .env file)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # Claude
    claude_model: str = os.getenv("IGBOT_MODEL", "claude-opus-5-5")
    claude_effort: str = os.getenv("IGBOT_EFFORT", "low")

    # Instagram / Meta
    ig_user_id: str = os.getenv("IG_USER_ID", "")
    ig_access_token: str = os.getenv("IG_ACCESS_TOKEN", "")
    ig_app_secret: str = os.getenv("IG_APP_SECRET", "")
    ig_verify_token: str = os.getenv("IG_VERIFY_TOKEN", "")
    graph_api_host: str = os.getenv("GRAPH_API_HOST", "https://graph.instagram.com")
    graph_api_version: str = os.getenv("GRAPH_API_VERSION", "v23.0")

    # Bot behaviour
    dry_run: bool = _bool("DRY_RUN", True)
    max_replies_per_hour: int = int(os.getenv("MAX_REPLIES_PER_HOUR", "60"))
    business_profile_path: str = os.getenv("BUSINESS_PROFILE_PATH", "business_profile.md")
    db_path: str = os.getenv("DB_PATH", "igbot.db")


settings = Settings()
