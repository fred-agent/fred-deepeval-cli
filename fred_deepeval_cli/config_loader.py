from __future__ import annotations

import logging

from fred_core.common import ConfigFiles, load_configuration_with_config_files
from pydantic import BaseModel


class JudgeConfig(BaseModel):
    provider: str = "litellm"
    model: str = "mistral/mistral-large-latest"
    api_base: str | None = None


class Configuration(BaseModel):
    judge: JudgeConfig


def parse_configuration(config_file: str) -> Configuration:
    import yaml

    with open(config_file, encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    if payload is None:
        raise ValueError(f"Configuration file is empty: {config_file}")
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration file must be a mapping object: {config_file}")

    return Configuration.model_validate(payload)


_config_files = ConfigFiles(logger=logging.getLogger(__name__))


def load_configuration() -> Configuration:
    return load_configuration_with_config_files(
        _config_files,
        parse_configuration,
    )
