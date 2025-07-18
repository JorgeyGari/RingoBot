"""
Puzzles utility for Discape module.
Contains puzzle solving functions.
"""

import logging

logger = logging.getLogger(__name__)


class PuzzlesSolver:
    """Handles puzzle solving functionality."""

    @staticmethod
    def solve_puzzle(puzzle_name: str) -> str:
        """
        Solve a puzzle by calling the appropriate function.

        Args:
            puzzle_name: Name of the puzzle to solve

        Returns:
            Result string from puzzle function
        """
        try:
            # Get the puzzle function by name
            puzzle_func = getattr(PuzzlesSolver, puzzle_name, None)
            if puzzle_func and callable(puzzle_func):
                return puzzle_func()
            else:
                logger.warning(f"Puzzle function '{puzzle_name}' not found")
                return f"Puzzle '{puzzle_name}' no encontrado."
        except Exception as e:
            logger.error(f"Error solving puzzle '{puzzle_name}': {e}")
            return "Error al resolver el puzzle."

    @staticmethod
    def hola() -> str:
        """Sample puzzle function."""
        return "¡Hola!"

    # Add more puzzle functions here as needed
    # Each function should return a string result
