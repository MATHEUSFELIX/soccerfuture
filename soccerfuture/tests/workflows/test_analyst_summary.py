"""Unit tests for src/workflows/analyst_summary.py."""

from src.workflows.analyst_summary import render_analyst_summary


class TestRenderAnalystSummary:
    """Analyst summary rendering."""

    def test_basic_summary_is_string(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=None,
        )
        assert isinstance(result, str)

    def test_contains_scenario_id(self):
        result = render_analyst_summary(
            scenario_id="my_scenario",
            source_type="structured",
            pipeline_report=None,
        )
        assert "my_scenario" in result

    def test_contains_source_type(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="video",
            pipeline_report=None,
        )
        assert "video" in result

    def test_no_pipeline_report_shows_message(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=None,
        )
        assert "did not produce results" in result

    def test_with_ranked_branches(self):
        report = {
            "ranked_branches": [
                {
                    "branch_id": "branch_001",
                    "composite_score": 0.85,
                    "evaluation_report": {
                        "ranking_explanation": {
                            "promoted_factors": ["Physical Speed"],
                            "penalized_factors": [],
                            "top_scoring_block": "Physical Speed",
                            "bottom_scoring_block": "Turnover Risk",
                        }
                    },
                }
            ],
            "metadata": {},
        }
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=report,
        )
        assert "branch_001" in result
        assert "0.850" in result

    def test_extraction_notes_included(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="video",
            pipeline_report=None,
            extraction_notes=["Low confidence on player p3"],
        )
        assert "Low confidence on player p3" in result

    def test_confidence_notes_included(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=None,
            confidence_notes=["Partial tracking data"],
        )
        assert "Partial tracking data" in result

    def test_context_applied_noted(self):
        report = {"ranked_branches": [], "metadata": {}}
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=report,
            context_applied=True,
        )
        assert "Context applied" in result or "context was applied" in result.lower()

    def test_priors_applied_noted(self):
        report = {"ranked_branches": [], "metadata": {"priors_influence_level": "light"}}
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=report,
            priors_applied=True,
        )
        assert "priors" in result.lower()

    def test_artifact_references_included(self):
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=None,
            artifact_references={"report": "pipeline_report.json"},
        )
        assert "pipeline_report.json" in result

    def test_empty_ranked_branches_shows_message(self):
        report = {"ranked_branches": [], "metadata": {}}
        result = render_analyst_summary(
            scenario_id="s1",
            source_type="structured",
            pipeline_report=report,
        )
        assert "No branches passed gating" in result
