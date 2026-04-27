"""Property-based tests for benchmark manifest round-trip serialization.

Feature: pipeline-maturity-baseline
- Property 1: Benchmark manifest round-trip serialization

Validates: Requirements 13.1, 13.3, 13.4
"""

import json
import os
import re
import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.utils.manifest import load_manifest, save_manifest, validate_manifest
from tests.strategies import manifest_strategy


class TestManifestRoundTripProperty:
    """Property 1: Benchmark manifest round-trip serialization.

    For any valid manifest dict, save_manifest → load_manifest round-trip
    SHALL produce an equivalent dict.
    """

    @given(manifest=manifest_strategy())
    @settings(max_examples=100, deadline=None)
    def test_round_trip_serialization(self, manifest: dict) -> None:
        """**Validates: Requirements 13.1, 13.3, 13.4**

        Feature: pipeline-maturity-baseline, Property 1: Manifest round-trip serialization
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            save_manifest(manifest, tmp_path)
            restored = load_manifest(tmp_path)

            assert restored == manifest
        finally:
            os.unlink(tmp_path)


class TestInvalidManifestRaisesDescriptiveError:
    """Property 2: Invalid manifest raises descriptive error.

    For any dict missing required top-level keys, validate_manifest
    raises ValueError identifying the missing key.
    """

    @given(
        manifest=manifest_strategy(),
        key_to_remove=st.sampled_from(["version", "pipeline_config", "scenarios"]),
    )
    @settings(max_examples=100)
    def test_missing_top_level_key_raises_value_error(
        self, manifest: dict, key_to_remove: str
    ) -> None:
        """**Validates: Requirements 13.2**

        Feature: pipeline-maturity-baseline, Property 2: Invalid manifest raises descriptive error
        """
        invalid_manifest = {k: v for k, v in manifest.items() if k != key_to_remove}

        with pytest.raises(ValueError, match=re.escape(key_to_remove)):
            validate_manifest(invalid_manifest)
