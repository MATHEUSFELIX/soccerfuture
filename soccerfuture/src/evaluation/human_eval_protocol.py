"""Structured human evaluation protocol models and serialization.

Defines dataclasses for human evaluation questions, scenarios, and
protocols. Includes serialization helpers for JSON round-tripping.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HumanEvalQuestion:
    """A single evaluation question for a human reviewer.

    Attributes:
        question_id: Unique identifier for this question.
        text: The question text presented to the evaluator.
        scale_min: Minimum rating value (inclusive).
        scale_max: Maximum rating value (inclusive).
        category: Question category for grouping and aggregation.
            One of "ranking_quality", "explanation_clarity",
            "physical_plausibility", "tactical_coherence", or "general".
    """

    question_id: str
    text: str
    scale_min: int = 1
    scale_max: int = 5
    category: str = "general"


STANDARD_QUESTIONS: list[HumanEvalQuestion] = [
    HumanEvalQuestion(
        "q_ranking",
        "Is the top-ranked branch the most tactically sound?",
        category="ranking_quality",
    ),
    HumanEvalQuestion(
        "q_explanation",
        "Are the ranking explanations clear and useful?",
        category="explanation_clarity",
    ),
    HumanEvalQuestion(
        "q_plausibility",
        "Do the top branches look physically plausible?",
        category="physical_plausibility",
    ),
    HumanEvalQuestion(
        "q_tactical",
        "Is the tactical formation coherent across top branches?",
        category="tactical_coherence",
    ),
    HumanEvalQuestion(
        "q_overall",
        "Overall, how trustworthy is this ranking output?",
        category="general",
    ),
]


@dataclass
class HumanEvalScenario:
    """A scenario prepared for human evaluation.

    Attributes:
        scenario_id: Unique identifier for this scenario.
        play_state_file: Path or identifier for the play state source.
        pipeline_report: Serialized PipelineReport as a dict.
        questions: List of evaluation questions for this scenario.
        metadata: Additional scenario metadata.
    """

    scenario_id: str
    play_state_file: str
    pipeline_report: dict
    questions: list[HumanEvalQuestion]
    metadata: dict = field(default_factory=dict)


@dataclass
class HumanEvalProtocol:
    """Complete evaluation protocol with multiple scenarios.

    Attributes:
        protocol_id: Unique identifier for this protocol.
        scenarios: List of evaluation scenarios.
        evaluator_instructions: Instructions text for human evaluators.
        created_at: ISO-8601 timestamp of protocol creation.
        metadata: Additional protocol metadata.
    """

    protocol_id: str
    scenarios: list[HumanEvalScenario]
    evaluator_instructions: str
    created_at: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _question_to_dict(q: HumanEvalQuestion) -> dict:
    """Convert a HumanEvalQuestion to a JSON-serializable dict.

    Args:
        q: The question to serialize.

    Returns:
        Plain dict representation.
    """
    return {
        "question_id": q.question_id,
        "text": q.text,
        "scale_min": q.scale_min,
        "scale_max": q.scale_max,
        "category": q.category,
    }


def _dict_to_question(data: dict) -> HumanEvalQuestion:
    """Reconstruct a HumanEvalQuestion from a dict.

    Args:
        data: Dict previously produced by ``_question_to_dict``.

    Returns:
        Reconstructed HumanEvalQuestion.
    """
    return HumanEvalQuestion(
        question_id=data["question_id"],
        text=data["text"],
        scale_min=data.get("scale_min", 1),
        scale_max=data.get("scale_max", 5),
        category=data.get("category", "general"),
    )


def _scenario_to_dict(s: HumanEvalScenario) -> dict:
    """Convert a HumanEvalScenario to a JSON-serializable dict.

    Args:
        s: The scenario to serialize.

    Returns:
        Plain dict representation.
    """
    return {
        "scenario_id": s.scenario_id,
        "play_state_file": s.play_state_file,
        "pipeline_report": s.pipeline_report,
        "questions": [_question_to_dict(q) for q in s.questions],
        "metadata": s.metadata,
    }


def _dict_to_scenario(data: dict) -> HumanEvalScenario:
    """Reconstruct a HumanEvalScenario from a dict.

    Args:
        data: Dict previously produced by ``_scenario_to_dict``.

    Returns:
        Reconstructed HumanEvalScenario.
    """
    return HumanEvalScenario(
        scenario_id=data["scenario_id"],
        play_state_file=data["play_state_file"],
        pipeline_report=data["pipeline_report"],
        questions=[_dict_to_question(q) for q in data.get("questions", [])],
        metadata=data.get("metadata", {}),
    )


def protocol_to_dict(protocol: HumanEvalProtocol) -> dict:
    """Convert a HumanEvalProtocol to a JSON-serializable dict.

    Args:
        protocol: The protocol to serialize.

    Returns:
        Plain dict suitable for ``json.dumps``.
    """
    return {
        "protocol_id": protocol.protocol_id,
        "scenarios": [_scenario_to_dict(s) for s in protocol.scenarios],
        "evaluator_instructions": protocol.evaluator_instructions,
        "created_at": protocol.created_at,
        "metadata": protocol.metadata,
    }


def dict_to_protocol(data: dict) -> HumanEvalProtocol:
    """Reconstruct a HumanEvalProtocol from a JSON-deserialized dict.

    Args:
        data: Dict previously produced by ``protocol_to_dict``
            or loaded from a JSON file.

    Returns:
        Reconstructed HumanEvalProtocol.
    """
    return HumanEvalProtocol(
        protocol_id=data["protocol_id"],
        scenarios=[_dict_to_scenario(s) for s in data.get("scenarios", [])],
        evaluator_instructions=data.get("evaluator_instructions", ""),
        created_at=data.get("created_at", ""),
        metadata=data.get("metadata", {}),
    )
