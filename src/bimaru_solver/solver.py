"""Tiered logical solver."""
from dataclasses import dataclass
from typing import List, Set
from .board import PuzzleBoard, CellState, DIAGONAL
from .rules import RULES, Deduction

@dataclass
class SolveResult:
    """Result of a solve attempt."""
    solved: bool
    stuck: bool
    valid: bool
    techniques_used: List[Deduction]


class TieredSolver:
    """Solver that applies rules tier-by-tier."""

    def __init__(self, board: PuzzleBoard):
        self.board = board
        self.techniques_used: List[Deduction] = []
        self._applied_cells: Set[tuple] = set()

    def solve(self) -> SolveResult:
        """Solve using tiered rules, restarting from T1 after progress."""
        max_iterations = 1000
        iterations = 0
        inconsistent = False

        while not self.board.is_solved() and iterations < max_iterations:
            iterations += 1
            progress = False

            for tier in [1, 2, 3, 4, 5]:
                deductions = self._apply_tier(tier)

                if deductions:
                    self._apply_deductions(deductions)

                    if not self._is_consistent():
                        inconsistent = True
                        break

                    self.techniques_used.extend(deductions)

                    progress = True
                    break

            if inconsistent or not progress:
                break

        # Board is solved only if: no empty cells, not inconsistent, and clues satisfied
        no_empty = self.board.is_solved()
        clues_satisfied = self._clues_satisfied() if no_empty else False
        solved = no_empty and not inconsistent and clues_satisfied
        valid = solved and self.board.matches_solution()

        return SolveResult(
            solved=solved,
            stuck=not solved,
            valid=valid,
            techniques_used=self.techniques_used,
        )

    def _apply_tier(self, tier: int) -> List[Deduction]:
        """Run all rules for a tier, return first batch of new deductions."""
        for _, _, rule_func in RULES[tier]:
            deductions = rule_func(self.board)
            new_deductions = [
                d for d in deductions
                if (d.row, d.col, d.value) not in self._applied_cells
            ]
            new_deductions = self._filter_diagonal_conflicts(new_deductions)
            if new_deductions:
                return new_deductions
        return []

    def _filter_diagonal_conflicts(self, deductions: List[Deduction]) -> List[Deduction]:
        """Remove ship deductions that would create diagonal touching."""
        ship_deductions = [(d.row, d.col) for d in deductions if d.value == CellState.SHIP]
        if not ship_deductions:
            return deductions

        conflicts = set()
        for i, (r1, c1) in enumerate(ship_deductions):
            for r2, c2 in ship_deductions[i+1:]:
                if abs(r1 - r2) == 1 and abs(c1 - c2) == 1:
                    conflicts.add((r1, c1))
                    conflicts.add((r2, c2))

        for r, c in ship_deductions:
            for dr, dc in DIAGONAL:
                nr, nc = r + dr, c + dc
                if self.board.within_bounds(nr, nc):
                    if self.board.cells[nr][nc].state == CellState.SHIP:
                        conflicts.add((r, c))

        return [d for d in deductions
                if d.value != CellState.SHIP or (d.row, d.col) not in conflicts]

    def _apply_deductions(self, deductions: List[Deduction]) -> None:
        """Apply deductions to the board."""
        for d in deductions:
            self.board.cells[d.row][d.col].state = d.value
            self._applied_cells.add((d.row, d.col, d.value))

    def _is_consistent(self) -> bool:
        """Check if current board state is consistent (no violations)."""
        for idx in range(self.board.dimension):
            row_ships = sum(1 for c in range(self.board.dimension)
                          if self.board.cells[idx][c].state == CellState.SHIP)
            if row_ships > self.board.row_counts[idx]:
                return False

            col_ships = sum(1 for r in range(self.board.dimension)
                          if self.board.cells[r][idx].state == CellState.SHIP)
            if col_ships > self.board.col_counts[idx]:
                return False

        for r in range(self.board.dimension):
            for c in range(self.board.dimension):
                if self.board.cells[r][c].state == CellState.SHIP:
                    for dr, dc in DIAGONAL:
                        nr, nc = r + dr, c + dc
                        if self.board.within_bounds(nr, nc):
                            if self.board.cells[nr][nc].state == CellState.SHIP:
                                return False

        for r in range(self.board.dimension):
            for c in range(self.board.dimension):
                cell = self.board.cells[r][c]
                if not cell.is_hint or cell.state != CellState.SHIP:
                    continue
                if cell.hint_shape is None:
                    continue
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nr, nc = r + dr, c + dc
                    if not self.board.within_bounds(nr, nc):
                        continue
                    placed = self.board.cells[nr][nc].state
                    if placed == CellState.EMPTY:
                        continue
                    expected = cell.hint_shape.get((dr, dc))
                    if expected is None:
                        continue
                    if placed != expected:
                        return False

        return True

    def _clues_satisfied(self) -> bool:
        """Check if all row/col clues are exactly satisfied."""
        for idx in range(self.board.dimension):
            row_ships = sum(1 for c in range(self.board.dimension)
                          if self.board.cells[idx][c].state == CellState.SHIP)
            if row_ships != self.board.row_counts[idx]:
                return False

            col_ships = sum(1 for r in range(self.board.dimension)
                          if self.board.cells[r][idx].state == CellState.SHIP)
            if col_ships != self.board.col_counts[idx]:
                return False
        return True
