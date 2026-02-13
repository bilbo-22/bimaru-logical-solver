#!/usr/bin/env python3
"""Solve a Bimaru puzzle JSON file using the logical solver package."""

import argparse
import json
from pathlib import Path

from bimaru_solver import TieredSolver, build_board_from_puzzle


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve a Bimaru puzzle JSON file")
    parser.add_argument("path", type=Path, help="Path to puzzle JSON")
    args = parser.parse_args()

    puzzle = json.loads(args.path.read_text())
    board = build_board_from_puzzle(puzzle)
    result = TieredSolver(board).solve()

    print(f"Solved: {result.solved}")
    print(f"Valid: {result.valid}")
    print(f"Stuck: {result.stuck}")


if __name__ == "__main__":
    main()
