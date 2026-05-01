import pytest
import json
from narrative_warehouse.llm_client import (
    ExtractionResult,
    MinimaxCloudClient,
    OllamaClient,
    make_llm_client,
)


class TestExtractionResult:
    def test_creation(self):
        result = ExtractionResult(
            user_state="Stuck in analysis",
            conflict_node="analysis-paralysis",
            desired_outcome="Break through and ship",
            the_bridge="Daily writing practice",
            thematic_tags=["productivity", "creativity"],
            worth_score=0.85,
            narrative_flag="Normal",
        )
        assert result.worth_score == 0.85
        assert result.narrative_flag == "Normal"
        assert result.conflict_node == "analysis-paralysis"


class TestMakeLlmClient:
    def test_ollama_default(self, monkeypatch):
        monkeypatch.setenv("NARRATIVE_LLM_PROVIDER", "")
        from narrative_warehouse import config as cfg_module
        monkeypatch.setattr(cfg_module, "_config", {"ollama": {"base_url": "http://localhost:11434", "default_model": "gemma4"}})
        client = make_llm_client("ollama", None)
        assert isinstance(client, OllamaClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            make_llm_client("unknown")