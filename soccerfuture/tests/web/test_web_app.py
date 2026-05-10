"""Unit tests for the local web application routes and modules."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src.web.local_app import app
from src.web.artifact_loader import load_run_detail, load_runs_list
from src.web.test_catalog import get_test_catalog, get_catalog_summary


client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Catalog
# ---------------------------------------------------------------------------


class TestTestCatalog:
    def test_catalog_has_entries(self):
        catalog = get_test_catalog()
        assert len(catalog) >= 10

    def test_each_entry_has_required_fields(self):
        catalog = get_test_catalog()
        for entry in catalog:
            assert "id" in entry
            assert "title" in entry
            assert "purpose" in entry
            assert "why_it_matters" in entry
            assert "examples" in entry

    def test_catalog_summary(self):
        summary = get_catalog_summary()
        assert summary["total_categories"] >= 10
        assert "Domain Models" in summary["categories"]

    def test_catalog_is_json_serializable(self):
        catalog = get_test_catalog()
        j = json.dumps(catalog)
        assert isinstance(j, str)


# ---------------------------------------------------------------------------
# Artifact Loader
# ---------------------------------------------------------------------------


class TestArtifactLoader:
    def test_load_runs_list_empty(self, tmp_path):
        runs = load_runs_list(str(tmp_path))
        assert runs == []

    def test_load_runs_list_nonexistent(self):
        runs = load_runs_list("/nonexistent/path")
        assert runs == []

    def test_load_run_detail_not_found(self, tmp_path):
        detail = load_run_detail(str(tmp_path), "nonexistent")
        assert "error" in detail

    def test_load_run_detail_with_bundle(self, tmp_path):
        # Create a minimal bundle
        bundle = tmp_path / "test_run"
        bundle.mkdir()
        status = {"scenario_id": "test_run", "overall_status": "success", "source_type": "structured"}
        (bundle / "run_status.json").write_text(json.dumps(status))
        (bundle / "analyst_summary.md").write_text("# Summary")

        detail = load_run_detail(str(tmp_path), "test_run")
        assert detail["scenario_id"] == "test_run"
        assert "run_status" in detail
        assert "analyst_summary" in detail


# ---------------------------------------------------------------------------
# Web Routes
# ---------------------------------------------------------------------------


class TestWebRoutes:
    def test_home_page(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Football Tactical OS" in response.text

    def test_runs_page(self):
        response = client.get("/runs")
        assert response.status_code == 200
        assert "Runs" in response.text

    def test_healthcheck_page(self):
        response = client.get("/healthcheck")
        assert response.status_code == 200
        assert "Healthcheck" in response.text

    def test_test_catalog_page(self):
        response = client.get("/tests")
        assert response.status_code == 200
        assert "Test Health" in response.text
        assert "Domain Models" in response.text
        assert "Pipeline" in response.text

    def test_run_detail_not_found(self):
        response = client.get("/runs/nonexistent_xyz")
        assert response.status_code == 200
        assert "Not Found" in response.text

    def test_run_demo_page(self):
        response = client.get("/run-demo")
        assert response.status_code == 200
        # Should either show success or failure — both are valid HTML
        assert "Demo" in response.text


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_existing_cli_commands_still_work(self):
        from src.cli_app.commands import cmd_healthcheck
        result = cmd_healthcheck()
        assert result.status in ("ok", "warning", "error")
