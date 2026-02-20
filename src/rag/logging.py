from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml

from .settings import load_settings


def setup_logging() -> None:
    settings = load_settings()
    config_path = Path("config/logging.yaml")
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=settings.log_level)
