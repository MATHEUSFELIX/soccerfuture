"""Human evaluation pack generator.

Produces reproducible evaluation packs from pipeline runs. Each pack
contains scenarios with pipeline reports and standard evaluation
questions, ready for human reviewers.
"""

from __future__ import annotations

import datetime
import json

from src.domain.match_context import MatchContext
from src.evaluation.human_eval_protocol import (
    STANDARD_QUESTIONS,
    HumanEvalProtocol,
    HumanEvalQuestion,
    HumanEvalScenario,
    protocol_to_dict,
)
from src.models.play_state import PlayState
from src.pipeline import PipelineConfig, run_pipeline


DEFAULT_EVALUATOR_INSTRUCTIONS: str = (
    "Human Evaluation Instructions\n"
    "=============================\n"
    "\n"
    "For each scenario, review the pipeline output and answer every\n"
    "question on a 1-5 scale:\n"
    "\n"
    "  1 = Strongly disagree\n"
    "  2 = Disagree\n"
    "  3 = Neutral\n"
    "  4 = Agree\n"
    "  5 = Strongly agree\n"
    "\n"
    "Focus on the top-ranked branches when forming your assessment.\n"
    "Consider whether the rankings, explanations, and physical\n"
    "plausibility are reasonable for the given play state.\n"
    "\n"
    "If you have specific concerns or observations, note them in\n"
    "the free-text notes field for that scenario.\n"
)


def generate_eval_pack(
    scenarios: list[dict],
    config: PipelineConfig | None = None,
    match_context: MatchContext | None = None,
    protocol_id: str = "default",
    questions: list[HumanEvalQuestion] | None = None,
) -> HumanEvalProtocol:
    """Generate a human evaluation pack from scenario definitions.

    For each scenario, runs the pipeline and assembles a
    HumanEvalScenario with the report and evaluation questions.

    Each scenario dict must contain:
        - ``scenario_id``: Unique identifier for the scenario.
        - ``play_state_file``: Path or identifier for the play state source.
        - ``play_state``: A PlayState instance to run through the pipeline.

    Args:
        scenarios: List of scenario dicts with play state data.
        config: Optional pipeline configuration overrides.
        match_context: Optional match context for context-aware runs.
        protocol_id: Identifier for the generated protocol.
        questions: Custom evaluation questions. Defaults to
            STANDARD_QUESTIONS if not provided.

    Returns:
        A HumanEvalProtocol ready for human evaluation.
    """
    eval_questions = questions if questions is not None else list(STANDARD_QUESTIONS)
    eval_scenarios: list[HumanEvalScenario] = []

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        play_state_file = scenario.get("play_state_file", "")
        play_state: PlayState = scenario["play_state"]

        report = run_pipeline(
            play_state, config=config, match_context=match_context
        )
        report_dict = report.to_dict()

        eval_scenario = HumanEvalScenario(
            scenario_id=scenario_id,
            play_state_file=play_state_file,
            pipeline_report=report_dict,
            questions=eval_questions,
            metadata=scenario.get("metadata", {}),
        )
        eval_scenarios.append(eval_scenario)

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return HumanEvalProtocol(
        protocol_id=protocol_id,
        scenarios=eval_scenarios,
        evaluator_instructions=DEFAULT_EVALUATOR_INSTRUCTIONS,
        created_at=created_at,
    )


def save_eval_pack(protocol: HumanEvalProtocol, output_path: str) -> None:
    """Save a human evaluation protocol to a JSON file.

    Args:
        protocol: The protocol to save.
        output_path: File path to write the JSON output.
    """
    data = protocol_to_dict(protocol)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_eval_pack(path: str) -> dict:
    """Load a previously saved evaluation pack JSON file.

    Args:
        path: File path to the JSON file.

    Returns:
        The parsed dict containing the protocol data.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
