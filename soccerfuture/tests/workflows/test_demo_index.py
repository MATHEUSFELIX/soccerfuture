"""Unit tests for src/workflows/demo_index.py."""

import json
import os

from src.workflows.demo_index import (
    DemoIndexEntry,
    build_index_entry,
    generate_demo_index_json,
    generate_demo_index_markdown,
    save_demo_index,
)
from src.workflows.scenario_bundle import BundleManifest


def _make_entry(**overrides) -> DemoIndexEntry:
    defaults = dict(
        scenario_id="s1",
        source_type="structured",
        top_1_branch="branch_001",
        status="success",
        confidence_flag=False,
        context_flag=False,
        priors_flag=False,
        bundle_path="s1",
        summary_path="s1/analyst_summary.md",
    )
    defaults.update(overrides)
    return DemoIndexEntry(**defaults)


class TestDemoIndexEntry:
    """DemoIndexEntry creation."""

    def test_creation(self):
        entry = _make_entry()
        assert entry.scenario_id == "s1"
        assert entry.top_1_branch == "branch_001"


class TestBuildIndexEntry:
    """build_index_entry from BundleManifest."""

    def test_builds_from_manifest(self):
        manifest = BundleManifest(
            scenario_id="s1",
            source_type="video",
            run_timestamp="2025-01-01T00:00:00Z",
            artifact_references={"analyst_summary": "analyst_summary.md"},
            overall_status="success",
        )
        entry = build_index_entry(
            manifest, top_1_branch="b1", context_flag=True,
        )
        assert entry.scenario_id == "s1"
        assert entry.source_type == "video"
        assert entry.top_1_branch == "b1"
        assert entry.context_flag is True
        assert entry.summary_path == "s1/analyst_summary.md"


class TestGenerateDemoIndexJson:
    """JSON index generation."""

    def test_empty_entries(self):
        result = generate_demo_index_json([])
        assert result["scenarios"] == []
        assert result["summary"]["total"] == 0

    def test_single_entry(self):
        entries = [_make_entry()]
        result = generate_demo_index_json(entries)
        assert len(result["scenarios"]) == 1
        assert result["summary"]["total"] == 1
        assert result["summary"]["success"] == 1

    def test_mixed_statuses(self):
        entries = [
            _make_entry(scenario_id="s1", status="success"),
            _make_entry(scenario_id="s2", status="partial"),
            _make_entry(scenario_id="s3", status="failed"),
        ]
        result = generate_demo_index_json(entries)
        assert result["summary"]["success"] == 1
        assert result["summary"]["partial"] == 1
        assert result["summary"]["failed"] == 1

    def test_json_serializable(self):
        entries = [_make_entry()]
        result = generate_demo_index_json(entries)
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestGenerateDemoIndexMarkdown:
    """Markdown index generation."""

    def test_contains_header(self):
        entries = [_make_entry()]
        md = generate_demo_index_markdown(entries)
        assert "# Demo Index" in md

    def test_contains_table_header(self):
        entries = [_make_entry()]
        md = generate_demo_index_markdown(entries)
        assert "| Scenario |" in md

    def test_contains_scenario_id(self):
        entries = [_make_entry(scenario_id="my_scenario")]
        md = generate_demo_index_markdown(entries)
        assert "my_scenario" in md

    def test_contains_summary_counts(self):
        entries = [_make_entry(), _make_entry(scenario_id="s2", status="failed")]
        md = generate_demo_index_markdown(entries)
        assert "Total scenarios:** 2" in md


class TestSaveDemoIndex:
    """save_demo_index writes both JSON and Markdown files."""

    def test_creates_both_files(self, tmp_path):
        entries = [_make_entry()]
        json_path, md_path = save_demo_index(entries, str(tmp_path))
        assert os.path.isfile(json_path)
        assert os.path.isfile(md_path)
        assert json_path.endswith("demo_index.json")
        assert md_path.endswith("demo_index.md")

    def test_json_file_is_valid(self, tmp_path):
        entries = [_make_entry()]
        json_path, _ = save_demo_index(entries, str(tmp_path))
        with open(json_path) as f:
            data = json.load(f)
        assert "scenarios" in data
        assert "summary" in data
