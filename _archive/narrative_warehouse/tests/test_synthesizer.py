import pytest
import json
from unittest.mock import MagicMock, patch


class TestStage1Extractor:
    def test_sentiment_delta_calculation(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta, classify_thread_status, get_week_bounds

        nodes = [
            {"created_time": "2026-04-20T09:00:00Z", "worth_score": 0.5},
            {"created_time": "2026-04-20T10:00:00Z", "worth_score": 0.6},
            {"created_time": "2026-04-20T11:00:00Z", "worth_score": 0.7},
            {"created_time": "2026-04-20T12:00:00Z", "worth_score": 0.8},
        ]
        delta = compute_sentiment_delta(nodes)
        assert delta > 0  # late avg > early avg

    def test_sentiment_delta_single_node(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta, classify_thread_status, get_week_bounds

        nodes = [{"created_time": "2026-04-20T09:00:00Z", "worth_score": 0.7}]
        delta = compute_sentiment_delta(nodes)
        assert delta == 0.0

    def test_sentiment_delta_empty(self):
        from narrative_warehouse.stage2_synthesizer import compute_sentiment_delta, classify_thread_status, get_week_bounds

        delta = compute_sentiment_delta([])
        assert delta == 0.0


class TestThreadStatusClassification:
    def test_emerging_single_occurrence(self):
        from narrative_warehouse.stage2_synthesizer import classify_thread_status

        assert classify_thread_status(1, 0.0) == "Emerging"

    def test_closing_strong_improvement(self):
        from narrative_warehouse.stage2_synthesizer import classify_thread_status

        assert classify_thread_status(3, 0.2) == "Closing"
        assert classify_thread_status(5, 0.15) == "Closing"

    def test_open_no_improvement(self):
        from narrative_warehouse.stage2_synthesizer import classify_thread_status

        assert classify_thread_status(3, 0.05) == "Open"
        assert classify_thread_status(2, -0.1) == "Open"


class TestWeekBounds:
    def test_explicit_week_start(self):
        from narrative_warehouse.stage2_synthesizer import get_week_bounds

        ws, we = get_week_bounds("2026-04-13")
        assert ws == "2026-04-13"
        assert we == "2026-04-19"

    def test_default_current_week(self):
        from narrative_warehouse.stage2_synthesizer import get_week_bounds

        ws, we = get_week_bounds(None)
        assert ws <= we
        import datetime
        start = datetime.date.fromisoformat(ws)
        end = datetime.date.fromisoformat(we)
        assert (end - start).days == 6