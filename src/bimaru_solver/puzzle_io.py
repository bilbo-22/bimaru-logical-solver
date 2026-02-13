"""Puzzle JSON parsing helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .board import CellState, PuzzleBoard

ORTHOGONAL_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _parse_cell_state(raw: Any) -> CellState:
    if isinstance(raw, CellState):
        return raw
    if isinstance(raw, int):
        return CellState(raw)
    if isinstance(raw, str):
        token = raw.strip().lower()
        mapping = {
            "empty": CellState.EMPTY,
            "unknown": CellState.EMPTY,
            "sea": CellState.SEA,
            "water": CellState.SEA,
            "ship": CellState.SHIP,
        }
        if token in mapping:
            return mapping[token]
        return CellState(int(raw))
    raise ValueError(f"Unsupported cell state value: {raw!r}")


def _shape_to_hint_map(shape: Optional[str]) -> Optional[Dict[Tuple[int, int], CellState]]:
    if not shape:
        return None

    token = shape.strip().lower()
    if token in {"sub", "single"}:
        return {d: CellState.SEA for d in ORTHOGONAL_DIRS}
    if token in {"top", "bow", "up"}:
        return {
            (-1, 0): CellState.SEA,
            (1, 0): CellState.SHIP,
            (0, -1): CellState.SEA,
            (0, 1): CellState.SEA,
        }
    if token in {"bot", "bottom", "down"}:
        return {
            (-1, 0): CellState.SHIP,
            (1, 0): CellState.SEA,
            (0, -1): CellState.SEA,
            (0, 1): CellState.SEA,
        }
    if token in {"left"}:
        return {
            (-1, 0): CellState.SEA,
            (1, 0): CellState.SEA,
            (0, -1): CellState.SEA,
            (0, 1): CellState.SHIP,
        }
    if token in {"right"}:
        return {
            (-1, 0): CellState.SEA,
            (1, 0): CellState.SEA,
            (0, -1): CellState.SHIP,
            (0, 1): CellState.SEA,
        }
    if token in {"mid_h", "middle_h", "horizontal_mid"}:
        return {
            (-1, 0): CellState.SEA,
            (1, 0): CellState.SEA,
            (0, -1): CellState.SHIP,
            (0, 1): CellState.SHIP,
        }
    if token in {"mid_v", "middle_v", "vertical_mid"}:
        return {
            (-1, 0): CellState.SHIP,
            (1, 0): CellState.SHIP,
            (0, -1): CellState.SEA,
            (0, 1): CellState.SEA,
        }
    # Ambiguous middle hints (orientation unknown) are intentionally ignored.
    return None


def build_board_from_puzzle(puzzle: dict[str, Any]) -> PuzzleBoard:
    """Build a board from puzzle JSON."""
    board = PuzzleBoard()

    board.row_counts = puzzle["clues"]["rows"]
    board.col_counts = puzzle["clues"]["cols"]

    solution = puzzle.get("solution")
    if solution:
        for r in range(board.dimension):
            for c in range(board.dimension):
                board.cells[r][c].solution = _parse_cell_state(solution[r][c])

    for hint in puzzle["initial_hints"]:
        r, c, val = hint["r"], hint["c"], hint["val"]

        cell = board.cells[r][c]
        cell.is_hint = True
        cell.state = _parse_cell_state(val)

        if cell.state != CellState.SHIP:
            continue

        if solution:
            cell.hint_shape = {
                (-1, 0): board.get_solution_at(r - 1, c),
                (1, 0): board.get_solution_at(r + 1, c),
                (0, -1): board.get_solution_at(r, c - 1),
                (0, 1): board.get_solution_at(r, c + 1),
            }
            continue

        cell.hint_shape = _shape_to_hint_map(hint.get("shape"))

    return board
