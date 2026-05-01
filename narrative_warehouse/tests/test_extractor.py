import pytest


class TestExtractionResultCreation:
    def test_extraction_result_fields(self):
        from narrative_warehouse.llm_client import ExtractionResult
        result = ExtractionResult(
            user_state="Test state",
            conflict_node="test-conflict",
            desired_outcome="Test outcome",
            the_bridge="Test bridge",
            thematic_tags=["test"],
            worth_score=0.75,
            narrative_flag="Normal",
        )
        assert result.worth_score == 0.75
        assert result.narrative_flag == "Normal"


class TestSentimentDeltaLogic:
    def test_positive_delta(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta
        nodes = [
            {"created_time": "2026-04-20T09:00:00Z", "worth_score": 0.4},
            {"created_time": "2026-04-20T10:00:00Z", "worth_score": 0.5},
            {"created_time": "2026-04-20T11:00:00Z", "worth_score": 0.6},
            {"created_time": "2026-04-20T12:00:00Z", "worth_score": 0.7},
        ]
        delta = compute_sentiment_delta(nodes)
        assert delta > 0

    def test_single_node_returns_zero(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta
        assert compute_sentiment_delta([{"created_time": "2026-04-20T09:00:00Z", "worth_score": 0.8}]) == 0.0

    def test_empty_returns_zero(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta
        assert compute_sentiment_delta([]) == 0.0