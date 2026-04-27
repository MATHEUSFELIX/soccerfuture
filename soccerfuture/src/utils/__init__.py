"""Shared utilities for the simulation evaluator.

Re-exports serialization helpers and constants for convenient imports::

    from src.utils import report_to_dict, dict_to_report
"""

from src.utils.serialization import dict_to_report, report_to_dict

__all__ = [
    "dict_to_report",
    "report_to_dict",
]
