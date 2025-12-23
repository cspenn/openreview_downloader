# start openreview_downloader/config.py
"""Configuration management for OpenReview Downloader."""

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class OpenReviewCredentials(BaseModel):
    """Credentials for OpenReview API authentication."""

    username: Optional[str] = None
    password: Optional[str] = None


class DownloaderConfig(BaseModel):
    """General configuration for the paper downloader."""

    venue_id: str = "NeurIPS.cc/2025/Conference"
    decisions: List[str] = Field(
        default_factory=lambda: ["oral", "spotlight", "accepted"]
    )
    out_dir: Path = Path("downloads")
    db_path: Path = Path("data/ordl.db")
    retry_attempts: int = 5
    retry_backoff_factor: float = 2.0
    theme: str = "dark"  # "light" or "dark"


class Config(BaseModel):
    """Main configuration container."""

    downloader: DownloaderConfig = Field(default_factory=DownloaderConfig)
    credentials: OpenReviewCredentials = Field(default_factory=OpenReviewCredentials)

    @classmethod
    def load(cls, config_path: Path, credentials_path: Path) -> "Config":
        """Load configuration from YAML files.

        Args:
            config_path (Path): Path to general config.
            credentials_path (Path): Path to credentials config.

        Returns:
            Config: The loaded configuration object.
        """
        data = {}
        if config_path.exists():
            with config_path.open("r") as f:
                data["downloader"] = yaml.safe_load(f) or {}

        if credentials_path.exists():
            with credentials_path.open("r") as f:
                data["credentials"] = yaml.safe_load(f) or {}

        return cls.model_validate(data)

    def save_config(self, config_path: Path):
        """Save general configuration to a YAML file.

        Args:
            config_path (Path): Path to the output configuration file.
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as f:
            yaml.safe_dump(self.downloader.model_dump(mode="json"), f)

    def save_credentials(self, credentials_path: Path):
        """Save credentials to a YAML file.

        Args:
            credentials_path (Path): Path to the output credentials file.
        """
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with credentials_path.open("w") as f:
            yaml.safe_dump(self.credentials.model_dump(mode="json"), f)


# end openreview_downloader/config.py
