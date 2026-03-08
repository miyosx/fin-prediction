from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Paths
    root_dir: Path = Path(__file__).parent.parent
    cache_dir: Path = Path(__file__).parent.parent / "data" / "cache_store"
    manual_imports_dir: Path = Path(__file__).parent.parent / "data" / "manual_imports"

    # Cache
    cache_max_age_hours: int = 6

    # Data range
    data_start_date: str = "2000-01-01"

    # Optional API keys
    eodhd_api_key: str = ""

    def model_post_init(self, __context):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manual_imports_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
