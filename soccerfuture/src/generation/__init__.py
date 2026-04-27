"""Branch generation package.

Re-exports the public API for convenient imports::

    from src.generation import generate_branches, GenerationResult
"""

from src.generation.branch_generator import GenerationResult, generate_branches

__all__ = ["generate_branches", "GenerationResult"]
