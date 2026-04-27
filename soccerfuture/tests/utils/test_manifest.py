"""Unit tests for the benchmark manifest loader.

Tests load_manifest, validate_manifest, and save_manifest against
valid manifests, missing keys, missing files, and invalid JSON.

Requirements: 13.1, 13.2, 13.3
"""

import json

import pytest

from src.utils.manifest import load_manifest, save_manifest, validate_manifest


def _make_valid_manifest() -> dict:
    """Build a minimal valid manifest dict with all required keys."""
    return {
        "version": "v1.0-baseline",
        "pipeline_config": {
            "n": 20,
            "k": 5,
            "seed": 42,
            "validity_weight": 0.5,
            "opportunity_weight": 0.5,
        },
        "scenarios": [
            {
                "scenario_file": "first_and_ten_midfield.json",
                "gating_pass_count": 14,
                "top_branch_min_score": 0.55,
                "bottom_branch_max_score": 0.35,
                "strategy_counts": {"route_variation": 7},
                "expected_top_k": [
                    {"branch_id": "gen-001", "composite_score": 0.62},
                ],
            },
        ],
    }


class TestLoadManifest:
    """Tests for load_manifest."""

    def test_valid_file_returns_dict_with_required_keys(self, tmp_path) -> None:
        manifest = _make_valid_manifest()
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")

        result = load_manifest(str(path))

        assert isinstance(result, dict)
        assert "version" in result
        assert "pipeline_config" in result
        assert "scenarios" in result

    def test_raises_file_not_found_on_missing_file(self, tmp_path) -> None:
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            load_manifest(str(missing))

    def test_raises_json_decode_error_on_invalid_json(self, tmp_path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_manifest(str(path))


class TestValidateManifest:
    """Tests for validate_manifest."""

    @pytest.mark.parametrize("missing_key", ["version", "pipeline_config", "scenarios"])
    def test_raises_on_missing_top_level_key(self, missing_key: str) -> None:
        data = _make_valid_manifest()
        del data[missing_key]
        with pytest.raises(ValueError, match=missing_key):
            validate_manifest(data)

    @pytest.mark.parametrize(
        "missing_key",
        ["scenario_file", "gating_pass_count", "top_branch_min_score",
         "bottom_branch_max_score", "strategy_counts", "expected_top_k"],
    )
    def test_raises_on_missing_scenario_key(self, missing_key: str) -> None:
        data = _make_valid_manifest()
        del data["scenarios"][0][missing_key]
        with pytest.raises(ValueError, match=missing_key):
            validate_manifest(data)

    @pytest.mark.parametrize(
        "missing_key",
        ["n", "k", "seed", "validity_weight", "opportunity_weight"],
    )
    def test_raises_on_missing_pipeline_config_key(self, missing_key: str) -> None:
        data = _make_valid_manifest()
        del data["pipeline_config"][missing_key]
        with pytest.raises(ValueError, match=missing_key):
            validate_manifest(data)


class TestSaveManifest:
    """Tests for save_manifest."""

    def test_writes_valid_json_readable_by_load_manifest(self, tmp_path) -> None:
        manifest = _make_valid_manifest()
        path = tmp_path / "out.json"

        save_manifest(manifest, str(path))
        loaded = load_manifest(str(path))

        assert loaded == manifest
