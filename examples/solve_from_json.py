#!/usr/bin/env python3
"""Solve a Bimaru puzzle JSON file using the logical solver package."""

import argparse
import json
from pathlib import Path

from bimaru_solver import CellState, PuzzleBoard, TieredSolver


def build_board(puzzle: dict) -> PuzzleBoard:
    board = PuzzleBoard()
    board.row_counts = puzzle["clues"]["rows"]
    board.col_counts = puzzle["clues"]["cols"]

    solution = puzzle.get("solution")
    if solution:
        for r in range(board.dimension):
            for c in range(board.dimension):
                board.cells[r][c].solution = CellState(solution[r][c])

    for hint in puzzle.get("initial_hints", []):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve a Bimaru puzzle JSON file")
    parser.add_argument("path", type=Path, help="Path to puzzle JSON")
    args = parser.parse_args()

    puzzle = json.loads(args.path.read_text())
    board = build_board(puzzle)
    result = TieredSolver(board).solve()

    print(f"Solved: {result.solved}")
    print(f"Valid: {result.valid}")
    print(f"Max tier: T{result.max_tier_required}")
    print(f"Difficulty score: {result.difficulty_score:.1f}")


if __name__ == "__main__":
    main()
