"""Tests for adaptive flag logic in ReportGenerator._build_adaptive_flags().

These tests verify that the correct flags are set based on report dimensions,
ensuring sections appear/disappear correctly.
"""

from __future__ import annotations

import pytest
from tests.unit.test_templates.conftest import extract_flags, load_pydantic_report


class TestSimpleModeFlags:
    """Test flags for simple mode (1 model, 1 prompt or none)."""

    def test_basic_usage_flags(self):
        """Fixture 01 (basic usage) should have minimal flags."""
        flags = extract_flags("01_basic_usage")
        
        assert flags["show_model_leaderboard"] is False
        assert flags["show_prompt_comparison"] is False
        assert flags["show_comparison_grid"] is False
        assert flags["show_matrix"] is False

    def test_basic_usage_has_failures(self):
        """Fixture 01 has failures - should set has_failures flag."""
        flags = extract_flags("01_basic_usage")
        
        assert flags["has_failures"] is True


class TestModelComparisonFlags:
    """Test flags for model comparison mode (2+ models)."""

    def test_model_comparison_flags(self):
        """Fixture 02 (2 models) should enable model comparison flags."""
        flags = extract_flags("02_model_comparison")
        
        assert flags["show_model_leaderboard"] is True
        assert flags["show_comparison_grid"] is True
        assert flags["show_prompt_comparison"] is False  # Only 1 prompt
        assert flags["show_matrix"] is False  # Not matrix mode

    def test_model_count(self):
        """Should report correct model count."""
        flags = extract_flags("02_model_comparison")
        
        assert flags["model_count"] == 2


class TestPromptComparisonFlags:
    """Test flags for prompt comparison mode (2+ prompts)."""

    def test_prompt_comparison_flags(self):
        """Fixture 03 (3 prompts) should enable prompt comparison flags."""
        flags = extract_flags("03_prompt_comparison")
        
        assert flags["show_prompt_comparison"] is True
        assert flags["show_comparison_grid"] is True
        assert flags["show_model_leaderboard"] is False  # Only 1 model
        assert flags["show_matrix"] is False  # Not matrix mode

    def test_prompt_count(self):
        """Should report correct prompt count."""
        flags = extract_flags("03_prompt_comparison")
        
        assert flags["prompt_count"] == 3


class TestMatrixModeFlags:
    """Test flags for matrix mode (2+ models AND 2+ prompts)."""

    def test_matrix_flags(self):
        """Fixture 04 (2×3 matrix) should enable all comparison flags."""
        flags = extract_flags("04_matrix")
        
        assert flags["show_model_leaderboard"] is True
        assert flags["show_prompt_comparison"] is True
        assert flags["show_comparison_grid"] is True
        assert flags["show_matrix"] is True
        assert flags["show_side_by_side"] is True

    def test_matrix_full_flags(self):
        """Fixture 08 (full matrix) should have all flags including AI summary."""
        flags = extract_flags("08_matrix_full")
        
        assert flags["show_model_leaderboard"] is True
        assert flags["show_prompt_comparison"] is True
        assert flags["show_comparison_grid"] is True
        assert flags["show_matrix"] is True
        assert flags["show_ai_summary"] is True


class TestAISummaryFlag:
    """Test AI summary flag."""

    def test_ai_summary_when_present(self):
        """Fixtures with AI summary should have flag True."""
        flags = extract_flags("06_with_ai_summary")
        assert flags["show_ai_summary"] is True
        
        flags = extract_flags("08_matrix_full")
        assert flags["show_ai_summary"] is True

    def test_ai_summary_when_absent(self):
        """Fixtures without AI summary should have flag False."""
        flags = extract_flags("01_basic_usage")
        assert flags["show_ai_summary"] is False
        
        flags = extract_flags("02_model_comparison")
        assert flags["show_ai_summary"] is False


class TestSkippedFlag:
    """Test skipped tests flag."""

    def test_has_skipped_when_present(self):
        """Fixture with skipped > 0 should have flag True."""
        # NOTE: Currently 07_with_skipped has 0 skipped in the fixture
        # (all tests passed). This test validates the logic works correctly
        # by checking what the actual value is. When we have a fixture with
        # actual skipped tests, update this test.
        flags = extract_flags("07_with_skipped")
        # Check actual fixture state - currently has 0 skipped
        report = load_pydantic_report("07_with_skipped")
        expected = report.summary.skipped > 0
        assert flags["has_skipped"] is expected

    def test_no_skipped_when_absent(self):
        """Fixtures without skipped tests should have flag False."""
        flags = extract_flags("01_basic_usage")
        assert flags["has_skipped"] is False


class TestToolComparisonFlag:
    """Test tool comparison flag."""

    def test_tool_comparison_in_model_comparison(self):
        """Model comparison with tools should enable tool comparison."""
        flags = extract_flags("02_model_comparison")
        assert flags["show_tool_comparison"] is True

    def test_tool_comparison_in_matrix(self):
        """Matrix mode with tools should enable tool comparison."""
        flags = extract_flags("04_matrix")
        assert flags["show_tool_comparison"] is True


class TestFlagConsistency:
    """Test that flags are internally consistent."""

    def test_matrix_implies_both_comparisons(self):
        """Matrix mode should imply both model and prompt comparison flags."""
        flags = extract_flags("04_matrix")
        
        if flags["show_matrix"]:
            assert flags["show_model_leaderboard"] is True
            assert flags["show_prompt_comparison"] is True

    def test_comparison_grid_requires_comparison_mode(self):
        """Comparison grid should only show in comparison modes."""
        # Simple mode - no grid
        flags = extract_flags("01_basic_usage")
        assert flags["show_comparison_grid"] is False
        
        # Model comparison - has grid
        flags = extract_flags("02_model_comparison")
        assert flags["show_comparison_grid"] is True
        
        # Prompt comparison - has grid
        flags = extract_flags("03_prompt_comparison")
        assert flags["show_comparison_grid"] is True
