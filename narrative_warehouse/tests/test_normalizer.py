import pytest
from narrative_warehouse.normalizer import normalize_conflict_node, display_name_from_conflict_node


class TestNormalizeConflictNode:
    def test_lowercase_and_hyphenate(self):
        assert normalize_conflict_node("Imposter Syndrome") == "imposter-syndrome"

    def test_strips_punctuation(self):
        assert normalize_conflict_node("Career uncertainty?!") == "career-uncertainty"

    def test_multiple_spaces_to_single_hyphen(self):
        assert normalize_conflict_node("creative  block") == "creative-block"

    def test_trims_edges(self):
        assert normalize_conflict_node("  procrastination  ") == "procrastination"

    def test_deduplicates_hyphens(self):
        assert normalize_conflict_node("self---doubt") == "self-doubt"

    def test_empty_string(self):
        assert normalize_conflict_node("") == ""

    def test_single_word(self):
        assert normalize_conflict_node("Anxiety") == "anxiety"


class TestDisplayNameFromConflictNode:
    def test_capitalizes_words(self):
        assert display_name_from_conflict_node("imposter-syndrome") == "Imposter Syndrome"

    def test_single_word(self):
        assert display_name_from_conflict_node("procrastination") == "Procrastination"

    def test_from_normalized(self):
        name = display_name_from_conflict_node(normalize_conflict_node("Career uncertainty?!"))
        assert name == "Career Uncertainty"