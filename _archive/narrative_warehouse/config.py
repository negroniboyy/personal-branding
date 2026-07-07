import os
from pathlib import Path
import tomllib

_CONFIG_PATH = Path(__file__).parent.parent / "NOTION DIARY FETCHER" / "config.toml"

def _load() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

_config = _load()

class NarrativeWarehouseConfig:
    llm_provider: str = _config.get("narrative_warehouse", {}).get("llm_provider", "ollama")
    llm_model: str = _config.get("narrative_warehouse", {}).get("llm_model", "gemma4")

class OllamaConfig:
    base_url: str = _config.get("ollama", {}).get("base_url", "http://localhost:11434")
    default_model: str = _config.get("ollama", {}).get("default_model", "gemma4")

def get_llm_provider_override() -> str | None:
    return os.environ.get("NARRATIVE_LLM_PROVIDER")

def get_llm_model_override() -> str | None:
    return os.environ.get("NARRATIVE_LLM_MODEL")