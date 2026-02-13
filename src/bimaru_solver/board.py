"""Board data structures and state management."""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

class CellState(IntEnum):
    """Cell state values matching puzzle JSON format."""
    EMPTY = 0
    SEA = 1
    SHIP = 2

@dataclass
class GridCell:
    """Single cell in the puzzle grid."""
    row: int
    col: int
    state: CellState = CellState.EMPTY
    solution: CellState = CellState.EMPTY
    is_hint: bool = False
    # For hints: maps direction (dr, dc) -> expected neighbor state
    hint_shape: Optional[Dict[Tuple[int, int], CellState]] = None

@dataclass
class PuzzleBoard:
    """10x10 puzzle board with fleet and clues."""
    dimension: int = 10
    cells: List[List[GridCell]] = field(default_factory=list)
    row_counts: List[int] = field(default_factory=list)
    col_counts: List[int] = field(default_factory=list)
    fleet: List[int] = field(default_factory=lambda: [4, 3, 3, 2, 2, 2, 1, 1, 1, 1])

    def __post_init__(self):
        if not self.cells:
            self.cells = [
                [GridCell(r, c) for c in range(self.dimension)]
                for r in range(self.dimension)
            ]

    def reset_grid(self) -> None:
        """Clear all cells to empty."""
        for r in range(self.dimension):
            for c in range(self.dimension):
                self.cells[r][c].state = CellState.EMPTY
                self.cells[r][c].solution = CellState.EMPTY
                self.cells[r][c].is_hint = False
                self.cells[r][c].hint_shape = None

    def within_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.dimension and 0 <= c < self.dimension

    def get_state_at(self, r: int, c: int) -> CellState:
        if self.within_bounds(r, c):
            return self.cells[r][c].state
        return CellState.SEA

    def get_solution_at(self, r: int, c: int) -> CellState:
        if self.within_bounds(r, c):
            return self.cells[r][c].solution
        return CellState.SEA

    def get_shape_name(self, r: int, c: int) -> str:
        """Determine ship shape from solution neighbors."""
        n = self.get_solution_at(r - 1, c) == CellState.SHIP
        s = self.get_solution_at(r + 1, c) == CellState.SHIP
        w = self.get_solution_at(r, c - 1) == CellState.SHIP
        e = self.get_solution_at(r, c + 1) == CellState.SHIP

        if (n and s) or (w and e): return "mid"
        if s: return "top"
        if n: return "bot"
        if e: return "left"
        if w: return "right"
        return "sub"

    def compute_clue_numbers(self) -> None:
        """Calculate row/column ship counts from solution."""
        self.row_counts = [
            sum(1 for c in range(self.dimension)
                if self.cells[r][c].solution == CellState.SHIP)
            for r in range(self.dimension)
        ]
        self.col_counts = [
            sum(1 for r in range(self.dimension)
                if self.cells[r][c].solution == CellState.SHIP)
            for c in range(self.dimension)
        ]

    def get_snapshot(self) -> str:
        """Capture board state as string for save/restore."""
        chars = []
        for r in range(self.dimension):
            for c in range(self.dimension):
                cell = self.cells[r][c]
                if cell.is_hint:
                    char = 'H' if cell.state == CellState.SHIP else 'h'
                elif cell.state == CellState.EMPTY:
                    char = ' '
                elif cell.state == CellState.SHIP:
                    char = 'S'
                else:
                    char = '~'
                chars.append(char)
        return ''.join(chars)

    def restore_snapshot(self, snapshot: str) -> None:
        """Restore board state from snapshot string."""
        for idx, ch in enumerate(snapshot):
            r, c = divmod(idx, self.dimension)
            cell = self.cells[r][c]
            if ch == 'H':
                cell.is_hint = True
                cell.state = CellState.SHIP
            elif ch == 'h':
                cell.is_hint = True
                cell.state = CellState.SEA
            elif ch == 'S':
                cell.is_hint = False
                cell.state = CellState.SHIP
            elif ch == '~':
                cell.is_hint = False
                cell.state = CellState.SEA
            else:
                cell.is_hint = False
                cell.state = CellState.EMPTY

    def clear_to_hints_only(self) -> None:
        """Reset all non-hint cells to empty, hints to their solution."""
        for r in range(self.dimension):
            for c in range(self.dimension):
                cell = self.cells[r][c]
                if cell.is_hint:
                    cell.state = cell.solution
                else:
                    cell.state = CellState.EMPTY

    def count_empty(self) -> int:
        """Count cells still empty."""
        return sum(
            1 for r in range(self.dimension)
            for c in range(self.dimension)
            if self.cells[r][c].state == CellState.EMPTY
        )

    def is_solved(self) -> bool:
        """Check if no empty cells remain."""
        return self.count_empty() == 0

    def matches_solution(self) -> bool:
        """Check if current state matches intended solution."""
        for r in range(self.dimension):
            for c in range(self.dimension):
                if self.cells[r][c].state != self.cells[r][c].solution:
                    return False
        return True


# Direction constants
ORTHOGONAL = [(-1, 0), (0, -1), (1, 0), (0, 1)]
DIAGONAL = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
ALL_NEIGHBORS = ORTHOGONAL + DIAGONAL
