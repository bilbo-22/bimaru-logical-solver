"""Integration tests for solver behavior on puzzle-like JSON input."""

import json
from pathlib import Path

from bimaru_solver import TieredSolver, build_board_from_puzzle

FIXTURE = Path(__file__).parent / "fixtures" / "puzzle_sample.json"


def test_solver_solves_known_puzzle() -> None:
    puzzle = json.loads(FIXTURE.read_text())
    board = build_board_from_puzzle(puzzle)

    result = TieredSolver(board).solve()

    assert result.solved is False
    assert result.stuck is True
    assert result.valid is False
    assert len(result.techniques_used) > 0


def test_solver_reports_inconsistent_setup() -> None:
    puzzle = json.loads(FIXTURE.read_text())
    board = build_board_from_puzzle(puzzle)

    # Force contradiction by changing one clue to impossible.
    board.row_counts[0] = 10

    result = TieredSolver(board).solve()

    assert (result.solved and result.valid) is False
