"""Entry point for running the evaluator via ``python -m src``.

Loads the demo input file, evaluates all branches, and prints
formatted JSON reports to stdout.
"""

import json
import os
import sys

from src.simulation_evaluator_v2 import evaluate_all
from src.utils.serialization import report_to_dict


def main() -> None:
    """Load demo input, evaluate all branches, and print JSON results."""
    data_path = os.path.join("data", "evaluator_demo_input.json")

    with open(data_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    reports = evaluate_all(input_data)
    output = [report_to_dict(report) for report in reports]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
