"""Unit tests for API handlers and schemas."""

import json
import os

import pytest

from src.api.schemas import (
    FeedbackSubmitRequest,
    WorkflowSubmitRequest,
    WorkflowSubmitResponse,
    response_to_dict,
)
from src.api.handlers import (
    handle_feedback_submit,
    handle_run_status,
    handle_workflow_submit,
)
from src.models.play_state import dict_to_play_state, play_state_to_dict


@pytest.fixture(scope="module")
def play_state_dict():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_workflow_request_valid(self, play_state_dict):
        req = WorkflowSubmitRequest(scenario_id="s1", play_state=play_state_dict)
        assert req.scenario_id == "s1"

    def test_workflow_request_empty_id_raises(self, play_state_dict):
        with pytest.raises(ValueError, match="scenario_id"):
            WorkflowSubmitRequest(scenario_id="", play_state=play_state_dict)

    def test_workflow_request_invalid_play_state_raises(self):
        with pytest.raises(ValueError, match="play_state"):
            WorkflowSubmitRequest(scenario_id="s1", play_state="not a dict")

    def test_feedback_request_valid(self):
        req = FeedbackSubmitRequest(scenario_id="s1", reviewer_id="r1")
        assert req.scenario_id == "s1"

    def test_feedback_request_empty_reviewer_raises(self):
        with pytest.raises(ValueError, match="reviewer_id"):
            FeedbackSubmitRequest(scenario_id="s1", reviewer_id="")

    def test_response_to_dict(self):
        resp = WorkflowSubmitResponse(scenario_id="s1", status="success")
        d = response_to_dict(resp)
        assert isinstance(d, dict)
        assert d["scenario_id"] == "s1"


# ---------------------------------------------------------------------------
# Workflow Submit Handler
# ---------------------------------------------------------------------------


class TestHandleWorkflowSubmit:
    def test_success(self, play_state_dict, tmp_path):
        req = WorkflowSubmitRequest(
            scenario_id="api_test",
            play_state=play_state_dict,
            pipeline_config={"n": 10, "k": 3, "seed": 42},
        )
        resp = handle_workflow_submit(req, output_root=str(tmp_path))
        assert resp.status in ("success", "partial")
        assert resp.errors == []
        assert os.path.isdir(os.path.join(str(tmp_path), "api_test"))

    def test_invalid_play_state(self, tmp_path):
        req = WorkflowSubmitRequest(scenario_id="bad", play_state={"invalid": True})
        resp = handle_workflow_submit(req, output_root=str(tmp_path))
        assert resp.status == "failed"
        assert len(resp.errors) > 0


# ---------------------------------------------------------------------------
# Run Status Handler
# ---------------------------------------------------------------------------


class TestHandleRunStatus:
    def test_not_found(self, tmp_path):
        resp = handle_run_status("nonexistent", output_root=str(tmp_path))
        assert resp.overall_status == "not_found"

    def test_found(self, play_state_dict, tmp_path):
        # First create a run
        req = WorkflowSubmitRequest(
            scenario_id="status_test",
            play_state=play_state_dict,
            pipeline_config={"n": 10, "k": 3, "seed": 42},
        )
        handle_workflow_submit(req, output_root=str(tmp_path))

        # Then query status
        resp = handle_run_status("status_test", output_root=str(tmp_path))
        assert resp.overall_status in ("success", "partial")
        assert resp.scenario_id == "status_test"


# ---------------------------------------------------------------------------
# Feedback Submit Handler
# ---------------------------------------------------------------------------


class TestHandleFeedbackSubmit:
    def test_success(self, tmp_path):
        fb_dir = str(tmp_path / "feedback")
        req = FeedbackSubmitRequest(
            scenario_id="s1",
            reviewer_id="r1",
            feedback={"notes": "looks good"},
        )
        resp = handle_feedback_submit(req, feedback_dir=fb_dir)
        assert resp.accepted is True
        assert os.path.isfile(os.path.join(fb_dir, "s1_r1.json"))

    def test_feedback_file_content(self, tmp_path):
        fb_dir = str(tmp_path / "feedback")
        req = FeedbackSubmitRequest(
            scenario_id="s2",
            reviewer_id="r2",
            feedback={"summary_clarity": 4},
        )
        handle_feedback_submit(req, feedback_dir=fb_dir)
        with open(os.path.join(fb_dir, "s2_r2.json")) as f:
            data = json.load(f)
        assert data["scenario_id"] == "s2"
        assert data["summary_clarity"] == 4
