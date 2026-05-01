"""Unit tests for human evaluation protocol models and serialization."""

from __future__ import annotations

from src.evaluation.human_eval_protocol import (
    STANDARD_QUESTIONS,
    HumanEvalProtocol,
    HumanEvalQuestion,
    HumanEvalScenario,
    dict_to_protocol,
    protocol_to_dict,
)

VALID_CATEGORIES = {
    "ranking_quality",
    "explanation_clarity",
    "physical_plausibility",
    "tactical_coherence",
    "general",
}


def test_standard_questions_count():
    """STANDARD_QUESTIONS has exactly 5 questions."""
    assert len(STANDARD_QUESTIONS) == 5


def test_question_categories():
    """Each standard question has a valid category."""
    for q in STANDARD_QUESTIONS:
        assert q.category in VALID_CATEGORIES, (
            f"Question {q.question_id} has invalid category: {q.category}"
        )


def test_protocol_round_trip():
    """protocol_to_dict → dict_to_protocol preserves all fields."""
    questions = [
        HumanEvalQuestion("q1", "Is it good?", category="general"),
    ]
    scenario = HumanEvalScenario(
        scenario_id="s1",
        play_state_file="test.json",
        pipeline_report={"ranked_branches": []},
        questions=questions,
        metadata={"tag": "test"},
    )
    protocol = HumanEvalProtocol(
        protocol_id="p1",
        scenarios=[scenario],
        evaluator_instructions="Rate 1-5",
        created_at="2025-01-01T00:00:00Z",
        metadata={"version": 1},
    )

    data = protocol_to_dict(protocol)
    restored = dict_to_protocol(data)

    assert restored.protocol_id == protocol.protocol_id
    assert restored.evaluator_instructions == protocol.evaluator_instructions
    assert restored.created_at == protocol.created_at
    assert restored.metadata == protocol.metadata
    assert len(restored.scenarios) == 1

    rs = restored.scenarios[0]
    assert rs.scenario_id == "s1"
    assert rs.play_state_file == "test.json"
    assert rs.pipeline_report == {"ranked_branches": []}
    assert rs.metadata == {"tag": "test"}
    assert len(rs.questions) == 1
    assert rs.questions[0].question_id == "q1"
    assert rs.questions[0].text == "Is it good?"
    assert rs.questions[0].category == "general"


def test_scenario_questions_preserved():
    """Questions survive serialization round-trip."""
    questions = [
        HumanEvalQuestion("qa", "Question A", category="ranking_quality"),
        HumanEvalQuestion("qb", "Question B", category="explanation_clarity"),
    ]
    scenario = HumanEvalScenario(
        scenario_id="s_q",
        play_state_file="f.json",
        pipeline_report={},
        questions=questions,
    )
    protocol = HumanEvalProtocol(
        protocol_id="pq",
        scenarios=[scenario],
        evaluator_instructions="",
        created_at="2025-01-01T00:00:00Z",
    )

    data = protocol_to_dict(protocol)
    restored = dict_to_protocol(data)

    restored_qs = restored.scenarios[0].questions
    assert len(restored_qs) == 2
    assert restored_qs[0].question_id == "qa"
    assert restored_qs[0].category == "ranking_quality"
    assert restored_qs[1].question_id == "qb"
    assert restored_qs[1].category == "explanation_clarity"
