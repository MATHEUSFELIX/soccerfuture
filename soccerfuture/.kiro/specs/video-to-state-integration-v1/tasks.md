# Tasks

- [x] Create `src/domain/video_clip.py` with:
  - `VideoClip`
  - serialization
  - validation
  - safe defaults where appropriate

- [x] Add unit tests for `video_clip.py` covering:
  - round-trip serialization
  - required field validation
  - invalid payload failures

- [x] Create `src/domain/tracked_state.py` with:
  - `TrackedEntityState`
  - `TrackedState`
  - serialization
  - validation
  - completeness metadata

- [x] Add unit tests for `tracked_state.py` covering:
  - round-trip serialization
  - partial entity handling
  - invalid payload failures

- [x] Create `src/integrations/commentator_adapter.py`

- [x] Implement fixture-first ingestion of commentator-style outputs into:
  - `VideoClip`
  - `TrackedState`

- [x] Surface:
  - source
  - completeness
  - fallback notes
  - malformed payload errors

- [x] Create `src/services/video_state_builder.py`

- [x] Implement deterministic conversion from:
  - `VideoClip`
  - `TrackedState`
  into:
  - `PlayState`

- [x] Add builder notes for:
  - inferred assumptions
  - missing entities
  - low-confidence inputs
  - fallback alignment

- [x] Add unit tests for:
  - successful conversion
  - conservative fallback behavior
  - failure behavior for malformed tracking

- [x] Extend pipeline/report integration with optional video-derived source metadata

- [x] Extend `pipeline_report.py` with:
  - `video_source`
  - `tracked_state_summary`
  - `builder_notes`
  - `extraction_confidence_summary`

- [x] Extend `viewer_2d.py` with minimal optional metadata display for video-derived scenarios

- [x] Create `src/evaluation/video_pipeline_eval.py` to run:
  - fixture clip/tracking ingestion
  - builder conversion
  - pipeline execution
  - artifact emission

- [x] Add integration tests for:
  - fixture tracking -> PlayState -> pipeline
  - commentator-style fixture -> adapter -> builder -> pipeline
  - report stability
  - viewer compatibility

- [x] Add regression tests ensuring:
  - structured scenario workflows remain unchanged
  - fixture-based video-to-state conversion remains deterministic

- [x] Add fixture files for:
  - video clip metadata
  - tracked state
  - commentator-style artifact payloads

- [x] Document the video-to-state fixture workflow in the README
