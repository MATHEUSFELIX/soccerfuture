"""Input quality assessment for tracking payloads.

Grades normalized payloads on a deterministic scale:
good, acceptable, poor, or rejected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.utils.constants import VIDEO_CONFIDENCE_THRESHOLD

# ---------------------------------------------------------------------------
# Quality thresholds
# ---------------------------------------------------------------------------

MIN_PLAYERS_GOOD: int = 11
MIN_PLAYERS_ACCEPTABLE: int = 5
MIN_PLAYERS_POOR: int = 2

MIN_BALL_ENTRIES: int = 1

AVG_CONFIDENCE_GOOD: float = 0.7
AVG_CONFIDENCE_ACCEPTABLE: float = 0.5

VALID_QUALITY_GRADES = {"good", "acceptable", "poor", "rejected"}


@dataclass
class QualityAssessment:
    """Result of input quality assessment.

    Attributes:
        grade: One of "good", "acceptable", "poor", "rejected".
        player_count: Number of unique players in the payload.
        ball_entry_count: Number of ball position entries.
        avg_player_confidence: Average confidence across player entries.
        avg_ball_confidence: Average confidence across ball entries.
        issues: List of quality issues found.
        notes: Additional assessment notes.
    """

    grade: str
    player_count: int
    ball_entry_count: int
    avg_player_confidence: float
    avg_ball_confidence: float
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def assess_quality(payload: dict) -> QualityAssessment:
    """Assess the quality of a normalized payload.

    Args:
        payload: A normalized v1 payload dict (from the normalizer).

    Returns:
        A QualityAssessment with grade and diagnostics.
    """
    issues: list[str] = []
    notes: list[str] = []

    players = payload.get("players", [])
    ball_positions = payload.get("ball_positions", [])

    # Player count
    unique_player_ids = {p.get("player_id", f"anon_{i}") for i, p in enumerate(players)}
    player_count = len(unique_player_ids)

    # Ball entry count
    ball_entry_count = len(ball_positions)

    # Average confidences
    player_confidences = [
        p.get("confidence", 0.0) for p in players
        if isinstance(p.get("confidence"), (int, float))
    ]
    avg_player_confidence = (
        sum(player_confidences) / len(player_confidences)
        if player_confidences else 0.0
    )

    ball_confidences = [
        b.get("confidence", 0.0) for b in ball_positions
        if isinstance(b.get("confidence"), (int, float))
    ]
    avg_ball_confidence = (
        sum(ball_confidences) / len(ball_confidences)
        if ball_confidences else 0.0
    )

    # --- Rejection checks ---
    if player_count < MIN_PLAYERS_POOR:
        issues.append(f"Too few players ({player_count} < {MIN_PLAYERS_POOR})")
        return QualityAssessment(
            grade="rejected",
            player_count=player_count,
            ball_entry_count=ball_entry_count,
            avg_player_confidence=round(avg_player_confidence, 4),
            avg_ball_confidence=round(avg_ball_confidence, 4),
            issues=issues,
            notes=["Payload rejected: insufficient player data"],
        )

    if ball_entry_count < MIN_BALL_ENTRIES:
        issues.append(f"No ball position entries")
        return QualityAssessment(
            grade="rejected",
            player_count=player_count,
            ball_entry_count=ball_entry_count,
            avg_player_confidence=round(avg_player_confidence, 4),
            avg_ball_confidence=round(avg_ball_confidence, 4),
            issues=issues,
            notes=["Payload rejected: no ball data"],
        )

    # --- Grade determination ---
    if player_count < MIN_PLAYERS_ACCEPTABLE:
        issues.append(f"Low player count ({player_count} < {MIN_PLAYERS_ACCEPTABLE})")

    if avg_player_confidence < AVG_CONFIDENCE_ACCEPTABLE:
        issues.append(f"Low avg player confidence ({avg_player_confidence:.2f})")

    if avg_ball_confidence < AVG_CONFIDENCE_ACCEPTABLE:
        issues.append(f"Low avg ball confidence ({avg_ball_confidence:.2f})")

    # Determine grade
    if (
        player_count >= MIN_PLAYERS_GOOD
        and avg_player_confidence >= AVG_CONFIDENCE_GOOD
        and avg_ball_confidence >= AVG_CONFIDENCE_GOOD
    ):
        grade = "good"
        notes.append("High-quality input with full player coverage and strong confidence.")
    elif (
        player_count >= MIN_PLAYERS_ACCEPTABLE
        and avg_player_confidence >= AVG_CONFIDENCE_ACCEPTABLE
    ):
        grade = "acceptable"
        notes.append("Acceptable input; some quality limitations noted.")
    else:
        grade = "poor"
        notes.append("Poor quality input; results may be unreliable.")

    return QualityAssessment(
        grade=grade,
        player_count=player_count,
        ball_entry_count=ball_entry_count,
        avg_player_confidence=round(avg_player_confidence, 4),
        avg_ball_confidence=round(avg_ball_confidence, 4),
        issues=issues,
        notes=notes,
    )
