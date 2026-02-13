"""Integration tests for solver behavior on puzzle-like JSON input."""

import json
from pathlib import Path

from bimaru_solver import CellState, PuzzleBoard, TieredSolver

FIXTURE = Path(__file__).parent / "fixtures" / "puzzle_sample.json"


def build_board_from_puzzle(puzzle: dict) -> PuzzleBoard:
    board = PuzzleBoard()
    board.row_counts = puzzle["clues"]["rows"]
    board.col_counts = puzzle["clues"]["cols"]

    solution = puzzle.get("solution")
    if solution:
        for r in range(board.dimension):
            for c in range(board.dimension):
                board.cells[r][c].solution = CellState(solution[r][c])

    for hint in puzzle["initial_hints"]:
        r, c, val = hint["r"], hint["c"], hint["val"]
        cell = board.cells[r][c]
        cell.is_hint = True
        cell.state = CellState(val)

        if val == CellState.SHIP and solution:
            cell.hint_shape = {
                (-1, 0): board.get_solution_at(r - 1, c),
                (1, 0): board.get_solution_at(r + 1, c),
                (0, -1): board.get_solution_at(r, c - 1),
                (0, 1): board.get_solution_at(r, c + 1),
            }

    return board


def test_solver_solves_known_puzzle() -> None:
    puzzle = json.loads(FIXTURE.read_text())
    board = build_board_from_puzzle(puzzle)

    result = TieredSolver(board).solve()

    assert result.solved is True
    assert result.valid is True
    assert result.max_tier_required >= 1


def test_solver_reports_inconsistent_setup() -> None:
    puzzle = json.loads(FIXTURE.read_text())
    board = build_board_from_puzzle(puzzle)

    # Force contradiction by changing one clue to impossible.
    board.row_counts[0] = 10

    result = TieredSolver(board).solve()

    assert (result.solved and result.valid) is False
