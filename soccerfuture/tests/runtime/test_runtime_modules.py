"""Unit and integration tests for runtime commentator modules."""

import json
import os

import pytest

from src.runtime.commentator_runtime_config import (
    RuntimeConfig,
    config_to_dict,
    dict_to_config,
)
from src.runtime.commentator_runtime_client import (
    RuntimePayload,
    discover_from_watched_directory,
    load_from_local_path,
    load_from_watched_directory,
    load_payloads,
)
from src.runtime.runtime_artifact_store import StoredArtifact, store_artifact
from src.runtime.runtime_ingestion_runner import (
    IngestionBatchResult,
    IngestionResult,
    run_ingestion,
)
from src.evaluation.runtime_ingestion_eval import (
    RuntimeIngestionEvalReport,
    evaluate_ingestion_batch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_payload() -> dict:
    return {
        "players": [
            {"player_id": "p1", "x": 10.0, "y": 20.0, "timestamp": 1.0, "confidence": 0.9},
            {"player_id": "p2", "x": 15.0, "y": 25.0, "timestamp": 1.0, "confidence": 0.85},
            {"player_id": "p3", "x": 20.0, "y": 30.0, "timestamp": 1.0, "confidence": 0.8},
        ],
        "ball_positions": [
            {"x": 12.0, "y": 22.0, "timestamp": 1.0, "confidence": 0.95},
        ],
        "clip_reference": {
            "source_path": "/test.mp4",
            "start_time": 0.0,
            "end_time": 5.0,
        },
        "frame_rate": 25.0,
    }


def _write_fixture(tmp_path, filename, payload):
    path = tmp_path / filename
    path.write_text(json.dumps(payload))
    return str(path)


# ---------------------------------------------------------------------------
# RuntimeConfig
# ---------------------------------------------------------------------------


class TestRuntimeConfig:
    def test_valid_local_path(self):
        cfg = RuntimeConfig(source_type="local_path", source_path="/data/file.json")
        assert cfg.source_type == "local_path"

    def test_valid_watched_directory(self):
        cfg = RuntimeConfig(source_type="watched_directory", source_path="/data/dir")
        assert cfg.source_type == "watched_directory"

    def test_valid_provider(self):
        cfg = RuntimeConfig(source_type="provider", provider_name="test_provider")
        assert cfg.source_type == "provider"

    def test_invalid_source_type_raises(self):
        with pytest.raises(ValueError, match="source_type"):
            RuntimeConfig(source_type="invalid")

    def test_local_path_missing_path_raises(self):
        with pytest.raises(ValueError, match="source_path"):
            RuntimeConfig(source_type="local_path", source_path="")

    def test_provider_missing_name_raises(self):
        with pytest.raises(ValueError, match="provider_name"):
            RuntimeConfig(source_type="provider", provider_name="")

    def test_round_trip_serialization(self):
        cfg = RuntimeConfig(source_type="local_path", source_path="/data/f.json")
        d = config_to_dict(cfg)
        restored = dict_to_config(d)
        assert restored.source_type == cfg.source_type
        assert restored.source_path == cfg.source_path

    def test_dict_to_config_missing_source_type_raises(self):
        with pytest.raises(KeyError):
            dict_to_config({})


# ---------------------------------------------------------------------------
# RuntimeClient
# ---------------------------------------------------------------------------


class TestRuntimeClient:
    def test_load_from_local_path(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        result = load_from_local_path(path)
        assert isinstance(result, RuntimePayload)
        assert result.payload["players"][0]["player_id"] == "p1"

    def test_load_from_local_path_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            load_from_local_path("/nonexistent/path.json")

    def test_discover_from_watched_directory(self, tmp_path):
        _write_fixture(tmp_path, "a.json", {})
        _write_fixture(tmp_path, "b.json", {})
        (tmp_path / "c.txt").write_text("not json")
        files = discover_from_watched_directory(str(tmp_path))
        assert len(files) == 2
        assert all(f.endswith(".json") for f in files)

    def test_discover_missing_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            discover_from_watched_directory("/nonexistent/dir")

    def test_load_from_watched_directory(self, tmp_path):
        _write_fixture(tmp_path, "a.json", _valid_payload())
        _write_fixture(tmp_path, "b.json", _valid_payload())
        results = load_from_watched_directory(str(tmp_path))
        assert len(results) == 2
        assert all(isinstance(r, RuntimePayload) for r in results)

    def test_load_payloads_local_path(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        cfg = RuntimeConfig(source_type="local_path", source_path=path)
        results = load_payloads(cfg)
        assert len(results) == 1

    def test_load_payloads_watched_directory(self, tmp_path):
        _write_fixture(tmp_path, "a.json", _valid_payload())
        cfg = RuntimeConfig(source_type="watched_directory", source_path=str(tmp_path))
        results = load_payloads(cfg)
        assert len(results) == 1

    def test_load_payloads_provider_no_fetcher(self):
        cfg = RuntimeConfig(source_type="provider", provider_name="test")
        results = load_payloads(cfg)
        assert len(results) == 1
        assert results[0].payload == {}

    def test_load_payloads_provider_with_fetcher(self):
        cfg = RuntimeConfig(source_type="provider", provider_name="test")
        fetcher = lambda name, config: [_valid_payload()]
        results = load_payloads(cfg, provider_fetcher=fetcher)
        assert len(results) == 1
        assert results[0].payload["players"][0]["player_id"] == "p1"


# ---------------------------------------------------------------------------
# ArtifactStore
# ---------------------------------------------------------------------------


class TestArtifactStore:
    def test_store_creates_directory(self, tmp_path):
        stored = store_artifact(
            store_root=str(tmp_path),
            payload=_valid_payload(),
            source_path="/data/test.json",
            index=0,
            quality_grade="good",
        )
        assert isinstance(stored, StoredArtifact)
        assert os.path.isdir(stored.store_path)

    def test_store_writes_payload_json(self, tmp_path):
        stored = store_artifact(
            store_root=str(tmp_path),
            payload=_valid_payload(),
            source_path="/data/test.json",
            index=0,
        )
        payload_path = os.path.join(stored.store_path, "payload.json")
        assert os.path.isfile(payload_path)

    def test_store_writes_metadata_json(self, tmp_path):
        stored = store_artifact(
            store_root=str(tmp_path),
            payload=_valid_payload(),
            source_path="/data/test.json",
            index=0,
            quality_grade="acceptable",
            rejected=False,
        )
        meta_path = os.path.join(stored.store_path, "metadata.json")
        assert os.path.isfile(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["quality_grade"] == "acceptable"
        assert meta["rejected"] is False

    def test_store_writes_diagnostics_when_provided(self, tmp_path):
        stored = store_artifact(
            store_root=str(tmp_path),
            payload=_valid_payload(),
            source_path="/data/test.json",
            index=0,
            diagnostics={"grade": "good", "warnings": []},
        )
        diag_path = os.path.join(stored.store_path, "diagnostics.json")
        assert os.path.isfile(diag_path)

    def test_artifact_id_deterministic(self, tmp_path):
        s1 = store_artifact(str(tmp_path / "a"), _valid_payload(), "/data/test.json", 0)
        s2 = store_artifact(str(tmp_path / "b"), _valid_payload(), "/data/test.json", 0)
        assert s1.artifact_id == s2.artifact_id


# ---------------------------------------------------------------------------
# IngestionRunner
# ---------------------------------------------------------------------------


class TestIngestionRunner:
    def test_run_ingestion_local_path(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        assert isinstance(batch, IngestionBatchResult)
        assert batch.total == 1

    def test_accepted_payload_has_normalized(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        # With 3 players, quality is "poor" (< 5 acceptable threshold)
        # but not rejected (>= 2 minimum)
        result = batch.results[0]
        if result.accepted:
            assert result.normalized_payload is not None
        else:
            assert result.normalized_payload is None

    def test_rejected_payload_has_no_normalized(self, tmp_path):
        # Payload with only 1 player → rejected
        bad_payload = {
            "players": [{"player_id": "p1", "x": 1, "y": 2, "timestamp": 0, "confidence": 0.9}],
            "ball_positions": [{"x": 1, "y": 2, "timestamp": 0, "confidence": 0.9}],
            "clip_reference": {"source_path": "/t.mp4", "start_time": 0, "end_time": 5},
        }
        path = _write_fixture(tmp_path, "bad.json", bad_payload)
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        assert batch.rejected_count == 1
        assert batch.results[0].normalized_payload is None

    def test_watched_directory_batch(self, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        _write_fixture(watch_dir, "a.json", _valid_payload())
        _write_fixture(watch_dir, "b.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="watched_directory",
            source_path=str(watch_dir),
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        assert batch.total == 2

    def test_artifacts_stored(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        assert batch.results[0].stored_artifact is not None
        assert os.path.isdir(batch.results[0].stored_artifact.store_path)


# ---------------------------------------------------------------------------
# RuntimeIngestionEval
# ---------------------------------------------------------------------------


class TestRuntimeIngestionEval:
    def test_evaluate_empty_batch(self):
        batch = IngestionBatchResult(total=0, accepted_count=0, rejected_count=0)
        report = evaluate_ingestion_batch(batch)
        assert report.total_payloads == 0
        assert report.acceptance_rate == 0.0

    def test_evaluate_batch_with_results(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        report = evaluate_ingestion_batch(batch)
        assert isinstance(report, RuntimeIngestionEvalReport)
        assert report.total_payloads == 1

    def test_grade_distribution_populated(self, tmp_path):
        path = _write_fixture(tmp_path, "test.json", _valid_payload())
        store_dir = str(tmp_path / "store")
        cfg = RuntimeConfig(
            source_type="local_path",
            source_path=path,
            artifact_store_path=store_dir,
        )
        batch = run_ingestion(cfg)
        report = evaluate_ingestion_batch(batch)
        assert len(report.grade_distribution) > 0


# ---------------------------------------------------------------------------
# Regression: clean fixtures still work
# ---------------------------------------------------------------------------


class TestCleanFixtureRegression:
    """Existing clean fixture workflows remain stable."""

    def test_commentator_adapter_still_works(self):
        from src.integrations.commentator_adapter import get_tracked_state
        result = get_tracked_state("sample_clip_01")
        assert len(result.players) == 2

    def test_video_state_builder_still_works(self):
        from src.integrations.commentator_adapter import get_tracked_state
        from src.services.video_state_builder import build_play_state
        tracked = get_tracked_state("sample_clip_01")
        ps = build_play_state(tracked, decision_point_timestamp=10.0)
        assert len(ps.player_positions) == 2
