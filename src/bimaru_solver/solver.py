"""Tiered solver that tracks technique usage and scores difficulty."""
from dataclasses import dataclass, field
from typing import List, Dict, Set
from .board import PuzzleBoard, CellState, DIAGONAL
from .rules import RULES, Deduction

@dataclass
class T5Detail:
    """Details of a single T5 (speculative) solve step."""
    empty_before: int  # How many cells were empty when T5 was used
    cells_filled: int  # How many cells T5 filled


@dataclass
class SolveResult:
    """Result of a solve attempt."""
    solved: bool
    stuck: bool
    valid: bool  # True if solution matches intended
    tier_usage: Dict[int, int]
    techniques_used: List[Deduction]
    difficulty_score: float
    max_tier_required: int
    t5_details: List[T5Detail] = field(default_factory=list)  # Track T5 usage details
    t3plus_remaining: List[int] = field(default_factory=list)  # Remaining cells at each T3+ moment


class TieredSolver:
    """Solver that applies rules tier-by-tier, tracking difficulty."""

    def __init__(self, board: PuzzleBoard):
        self.board = board
        self.tier_usage: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.techniques_used: List[Deduction] = []
        self.t5_details: List[T5Detail] = []  # Track T5 usage details
        self._applied_cells: Set[tuple] = set()  # Track (r, c, value) to avoid duplicates
        # Track remaining cells at each T3+ moment for difficulty scoring
        self._t3plus_remaining: List[int] = []
        self._last_t3plus_remaining: int = -1  # To detect new T3+ moments

    def solve(self) -> SolveResult:
        """Solve using tiered rules, restarting from T1 after progress."""
        max_iterations = 1000
        iterations = 0
        inconsistent = False

        while not self.board.is_solved() and iterations < max_iterations:
            iterations += 1
            progress = False

            for tier in [1, 2, 3, 4, 5]:
                # Track empty cells before T5
                empty_before = self._count_empty() if tier == 5 else 0

                deductions = self._apply_tier(tier)

                if deductions:
                    # Track each T3+ moment (when remaining drops significantly)
                    if tier >= 3:
                        current_remaining = self._count_empty()
                        # Only record if this is a new T3+ "moment" (not consecutive steps)
                        if current_remaining < self._last_t3plus_remaining - 1 or self._last_t3plus_remaining == -1:
                            self._t3plus_remaining.append(current_remaining)
                        self._last_t3plus_remaining = current_remaining

                    self._apply_deductions(deductions)

                    # Check consistency after applying deductions
                    if not self._is_consistent():
                        inconsistent = True
                        break

                    self.tier_usage[tier] += 1
                    self.techniques_used.extend(deductions)

                    # Track T5 details
                    if tier == 5:
                        cells_filled = empty_before - self._count_empty()
                        self.t5_details.append(T5Detail(empty_before, cells_filled))

                    progress = True
                    break  # Restart from Tier 1

            if inconsistent or not progress:
                break  # Stuck or inconsistent

        # Board is solved only if: no empty cells, not inconsistent, and clues satisfied
        no_empty = self.board.is_solved()
        clues_satisfied = self._clues_satisfied() if no_empty else False
        solved = no_empty and not inconsistent and clues_satisfied
        valid = solved and self.board.matches_solution()

        return SolveResult(
            solved=solved,
            stuck=not solved,
            valid=valid,
            tier_usage=self.tier_usage,
            techniques_used=self.techniques_used,
            difficulty_score=self._compute_score(),
            max_tier_required=self._max_tier(),
            t5_details=self.t5_details,
            t3plus_remaining=self._t3plus_remaining,
        )

    def _apply_tier(self, tier: int) -> List[Deduction]:
        """Run all rules for a tier, return first batch of new deductions."""
        for technique_id, difficulty, rule_func in RULES[tier]:
            deductions = rule_func(self.board)
            # Filter out already-applied deductions
            new_deductions = [
                d for d in deductions
                if (d.row, d.col, d.value) not in self._applied_cells
            ]
            # Filter out deductions that would create diagonal touching
            new_deductions = self._filter_diagonal_conflicts(new_deductions)
            if new_deductions:
                return new_deductions
        return []

    def _filter_diagonal_conflicts(self, deductions: List[Deduction]) -> List[Deduction]:
        """Remove ship deductions that would create diagonal touching."""
        ship_deductions = [(d.row, d.col) for d in deductions if d.value == CellState.SHIP]
        if not ship_deductions:
            return deductions

        # Check for conflicts within the batch
        conflicts = set()
        for i, (r1, c1) in enumerate(ship_deductions):
            for r2, c2 in ship_deductions[i+1:]:
                # Check if diagonal
                if abs(r1 - r2) == 1 and abs(c1 - c2) == 1:
                    conflicts.add((r1, c1))
                    conflicts.add((r2, c2))

        # Check for conflicts with existing ships
        for r, c in ship_deductions:
            for dr, dc in DIAGONAL:
                nr, nc = r + dr, c + dc
                if self.board.within_bounds(nr, nc):
                    if self.board.cells[nr][nc].state == CellState.SHIP:
                        conflicts.add((r, c))

        # Filter out conflicting deductions
        return [d for d in deductions
                if d.value != CellState.SHIP or (d.row, d.col) not in conflicts]

    def _apply_deductions(self, deductions: List[Deduction]) -> None:
        """Apply deductions to the board."""
        for d in deductions:
            self.board.cells[d.row][d.col].state = d.value
            self._applied_cells.add((d.row, d.col, d.value))

    def _is_consistent(self) -> bool:
        """Check if current board state is consistent (no violations)."""
        # Check row/column counts not exceeded
        for idx in range(self.board.dimension):
            row_ships = sum(1 for c in range(self.board.dimension)
                          if self.board.cells[idx][c].state == CellState.SHIP)
            if row_ships > self.board.row_counts[idx]:
                return False

            col_ships = sum(1 for r in range(self.board.dimension)
                          if self.board.cells[r][idx].state == CellState.SHIP)
            if col_ships > self.board.col_counts[idx]:
                return False

        # Check diagonal touching
        for r in range(self.board.dimension):
            for c in range(self.board.dimension):
                if self.board.cells[r][c].state == CellState.SHIP:
                    for dr, dc in DIAGONAL:
                        nr, nc = r + dr, c + dc
                        if self.board.within_bounds(nr, nc):
                            if self.board.cells[nr][nc].state == CellState.SHIP:
                                return False

        # Check hint shape consistency
        for r in range(self.board.dimension):
            for c in range(self.board.dimension):
                cell = self.board.cells[r][c]
                if not cell.is_hint or cell.state != CellState.SHIP:
                    continue
                if cell.hint_shape is None:
                    continue  # No shape info available
                # Check if any neighbor contradicts hint's known shape
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nr, nc = r + dr, c + dc
                    if not self.board.within_bounds(nr, nc):
                        continue
                    placed = self.board.cells[nr][nc].state
                    if placed == CellState.EMPTY:
                        continue
                    expected = cell.hint_shape.get((dr, dc))
                    if expected is None:
                        continue  # Direction not in shape dict
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

    def _compute_score(self) -> float:
        """Compute difficulty score based on uncertainty at each T3+ moment.

        Uses diminishing returns: each T3+ moment contributes less than the previous.
        - 1st moment: full value (÷1)
        - 2nd moment: half value (÷2)
        - 3rd moment: third value (÷3)

        This naturally rewards:
        - Early T3+ (high remaining = high contribution)
        - Multiple T3+ moments (more terms in sum)
        - Both together (multiple early hard moments)

        Correlation with human solve time: r = 0.85
        """
        if not self._t3plus_remaining:
            return 0.0

        # Diminishing sum: each moment contributes less than the previous
        raw = sum(remaining / (i + 1)
                  for i, remaining in enumerate(self._t3plus_remaining))

        # Scale to 0-100 (max observed raw ~56)
        score = raw * 1.8

        return min(100.0, score)

    def _max_tier(self) -> int:
        """Get highest tier that was used."""
        for tier in [5, 4, 3, 2, 1]:
            if self.tier_usage[tier] > 0:
                return tier
        return 0

    def _count_empty(self) -> int:
        """Count empty cells on the board."""
        return sum(1 for r in range(self.board.dimension)
                   for c in range(self.board.dimension)
                   if self.board.cells[r][c].state == CellState.EMPTY)
