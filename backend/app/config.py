from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.1.0"
    allowed_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    allowed_uids: str = ""
    firebase_project_id: str = ""

    kite_api_key: str = ""
    gift_nifty_base_url: str = ""
    global_indices_base_url: str = ""

    score_flat_band: float = 0.15
    gap_flat_abs_percent: float = 0.15
    confidence_cap_uncalibrated: float = 0.75
    gift_session1_open: str = "05:15"
    preopen_start: str = "09:00"
    preopen_matching_start: str = "09:10"
    preopen_buffer_start: str = "09:12"
    cash_open: str = "09:15"
    or_15_end: str = "09:30"
    cash_close: str = "15:30"
    market_holidays: str = ""

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def uid_allowlist(self) -> set[str]:
        return {item.strip() for item in self.allowed_uids.split(",") if item.strip()}

    @property
    def holidays(self) -> set[str]:
        return {item.strip() for item in self.market_holidays.split(",") if item.strip()}

    @property
    def auth_disabled(self) -> bool:
        return self.app_env in {"development", "preview", "test"} and not self.firebase_project_id

    @property
    def auth_mode(self) -> str:
        if self.firebase_project_id:
            return "firebase"
        if self.app_env == "preview":
            return "public-preview"
        return "local-development"

    def validate_runtime(self) -> None:
        if self.app_env not in {"development", "test", "preview", "production"}:
            raise RuntimeError("APP_ENV must be development, test, preview, or production.")
        if self.app_env == "production" and not self.firebase_project_id:
            raise RuntimeError("Production requires Firebase Authentication.")
        if self.app_env == "production" and not self.uid_allowlist:
            raise RuntimeError("Production requires ALLOWED_UIDS.")


settings = Settings()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
