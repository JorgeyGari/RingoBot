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
            # Whitelist of allowed puzzle functions
            puzzle_registry = {
                "hola": PuzzlesSolver.hola,
                # Add more puzzle functions here as needed
            }
            puzzle_func = puzzle_registry.get(puzzle_name)
            if not puzzle_name.replace("_", "").replace("-", "").isalnum():
                logger.warning(f"Invalid puzzle name format: '{puzzle_name}'")
                return "Nombre de puzzle inválido."

            if puzzle_func:
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
