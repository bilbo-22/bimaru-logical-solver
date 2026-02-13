"""Deduction rules for tiered solver."""
from dataclasses import dataclass
from typing import List, Callable, Dict, Tuple
from .board import PuzzleBoard, CellState

@dataclass
class Deduction:
    """A single cell deduction made by a rule."""
    row: int
    col: int
    value: CellState
    technique: str
    tier: int
    difficulty: int

# Type for rule functions
RuleFunc = Callable[[PuzzleBoard], List[Deduction]]

# Registry: tier -> list of (technique_id, difficulty, function)
RULES: Dict[int, List[Tuple[str, int, RuleFunc]]] = {
    1: [], 2: [], 3: [], 4: [], 5: []
}

def register(tier: int, technique_id: str, difficulty: int):
    """Decorator to register a rule function."""
    def decorator(func: RuleFunc) -> RuleFunc:
        RULES[tier].append((technique_id, difficulty, func))
        return func
    return decorator


def make_deduction(r: int, c: int, value: CellState,
                   technique: str, tier: int, difficulty: int) -> Deduction:
    """Helper to create a Deduction."""
    return Deduction(row=r, col=c, value=value,
                     technique=technique, tier=tier, difficulty=difficulty)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def count_in_line(board: PuzzleBoard, idx: int, is_row: bool) -> Tuple[int, int, int]:
    """Count ships, empties, and seas in a row or column.

    Returns: (ship_count, empty_count, sea_count)
    """
    ships = empties = seas = 0
    for i in range(board.dimension):
        r, c = (idx, i) if is_row else (i, idx)
        state = board.cells[r][c].state
        if state == CellState.SHIP:
            ships += 1
        elif state == CellState.EMPTY:
            empties += 1
        else:
            seas += 1
    return ships, empties, seas


def get_clue(board: PuzzleBoard, idx: int, is_row: bool) -> int:
    """Get the clue number for a row or column."""
    return board.row_counts[idx] if is_row else board.col_counts[idx]


# =============================================================================
# TIER 1 - BASIC (Difficulty 1-2)
# =============================================================================

@register(tier=1, technique_id="T1.1", difficulty=1)
def zero_clue(board: PuzzleBoard) -> List[Deduction]:
    """Row/col with clue=0 → all cells are water."""
    deductions = []
    for idx in range(board.dimension):
        # Check rows
        if board.row_counts[idx] == 0:
            for c in range(board.dimension):
                if board.cells[idx][c].state == CellState.EMPTY:
                    deductions.append(make_deduction(
                        idx, c, CellState.SEA, "T1.1", 1, 1))
        # Check columns
        if board.col_counts[idx] == 0:
            for r in range(board.dimension):
                if board.cells[r][idx].state == CellState.EMPTY:
                    deductions.append(make_deduction(
                        r, idx, CellState.SEA, "T1.1", 1, 1))
    return deductions


@register(tier=1, technique_id="T1.2", difficulty=1)
def satisfied_clue(board: PuzzleBoard) -> List[Deduction]:
    """Line with ship count = clue → fill rest with water."""
    deductions = []
    for idx in range(board.dimension):
        for is_row in [True, False]:
            ships, empties, _ = count_in_line(board, idx, is_row)
            clue = get_clue(board, idx, is_row)

            if ships == clue and empties > 0:
                for i in range(board.dimension):
                    r, c = (idx, i) if is_row else (i, idx)
                    if board.cells[r][c].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            r, c, CellState.SEA, "T1.2", 1, 1))
    return deductions


from .board import DIAGONAL, ORTHOGONAL

@register(tier=1, technique_id="T1.3", difficulty=1)
def diagonal_water(board: PuzzleBoard) -> List[Deduction]:
    """Ship diagonals must be water."""
    deductions = []
    for r in range(board.dimension):
        for c in range(board.dimension):
            if board.cells[r][c].state != CellState.SHIP:
                continue
            for dr, dc in DIAGONAL:
                nr, nc = r + dr, c + dc
                if board.within_bounds(nr, nc):
                    if board.cells[nr][nc].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            nr, nc, CellState.SEA, "T1.3", 1, 1))
    return deductions


@register(tier=1, technique_id="T1.4", difficulty=1)
def hint_shape_deduction(board: PuzzleBoard) -> List[Deduction]:
    """Deduce neighbors from hint cell shapes.

    Hints store their shape as metadata (hint_shape dict).
    The shape tells us which neighbors are ship vs water.
    """
    deductions = []

    for r in range(board.dimension):
        for c in range(board.dimension):
            cell = board.cells[r][c]
            if not cell.is_hint or cell.state != CellState.SHIP:
                continue
            if cell.hint_shape is None:
                continue

            # Use stored hint shape to make deductions
            for (dr, dc), expected in cell.hint_shape.items():
                nr, nc = r + dr, c + dc
                if not board.within_bounds(nr, nc):
                    continue
                if board.cells[nr][nc].state != CellState.EMPTY:
                    continue

                if expected == CellState.SHIP:
                    deductions.append(make_deduction(
                        nr, nc, CellState.SHIP, "T1.4", 1, 1))
                elif expected == CellState.SEA:
                    deductions.append(make_deduction(
                        nr, nc, CellState.SEA, "T1.4", 1, 1))

    return deductions


# =============================================================================
# TIER 2 - INTERMEDIATE (Difficulty 3-4)
# =============================================================================

@register(tier=2, technique_id="T2.1", difficulty=3)
def exact_fit(board: PuzzleBoard) -> List[Deduction]:
    """Line where empties = ships needed → all empties are ships."""
    deductions = []
    for idx in range(board.dimension):
        for is_row in [True, False]:
            ships, empties, _ = count_in_line(board, idx, is_row)
            clue = get_clue(board, idx, is_row)
            needed = clue - ships

            if needed > 0 and empties == needed:
                for i in range(board.dimension):
                    r, c = (idx, i) if is_row else (i, idx)
                    if board.cells[r][c].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            r, c, CellState.SHIP, "T2.1", 2, 3))
    return deductions


@register(tier=2, technique_id="T2.4", difficulty=3)
def overflow_prevention(board: PuzzleBoard) -> List[Deduction]:
    """Cell where placing ship would exceed either row or column clue → water."""
    deductions = []
    for r in range(board.dimension):
        for c in range(board.dimension):
            if board.cells[r][c].state != CellState.EMPTY:
                continue

            ships_in_row, _, _ = count_in_line(board, r, True)
            ships_in_col, _, _ = count_in_line(board, c, False)

            row_full = ships_in_row >= board.row_counts[r]
            col_full = ships_in_col >= board.col_counts[c]

            if row_full or col_full:
                deductions.append(make_deduction(
                    r, c, CellState.SEA, "T2.4", 2, 3))
    return deductions


# =============================================================================
# TIER 3 - ADVANCED (Difficulty 5-6)
# =============================================================================

from .board import ORTHOGONAL

@register(tier=3, technique_id="T3.1", difficulty=5)
def forced_extension(board: PuzzleBoard) -> List[Deduction]:
    """Ship part that must extend (not a submarine) with only one open direction → extend there."""
    deductions = []

    for r in range(board.dimension):
        for c in range(board.dimension):
            if board.cells[r][c].state != CellState.SHIP:
                continue

            # Count neighbors by type
            ship_neighbors = []
            empty_neighbors = []
            blocked_count = 0

            for dr, dc in ORTHOGONAL:
                nr, nc = r + dr, c + dc
                if not board.within_bounds(nr, nc):
                    blocked_count += 1
                elif board.cells[nr][nc].state == CellState.SHIP:
                    ship_neighbors.append((nr, nc))
                elif board.cells[nr][nc].state == CellState.SEA:
                    blocked_count += 1
                else:
                    empty_neighbors.append((nr, nc))

            # If ship has exactly one ship neighbor (it's an end piece)
            # and exactly one empty neighbor, that empty must be water
            # (the ship extends from the ship neighbor side only)
            if len(ship_neighbors) == 1 and len(empty_neighbors) == 1:
                # Check if the empty is on the opposite side of the ship neighbor
                snr, snc = ship_neighbors[0]
                enr, enc = empty_neighbors[0]
                # If they're on opposite sides, the empty is water
                # If they're on the same axis (both horizontal or both vertical), empty is water
                ship_dir = (snr - r, snc - c)
                empty_dir = (enr - r, enc - c)
                # Opposite means same axis: both horizontal or both vertical
                same_axis = (ship_dir[0] == 0 and empty_dir[0] == 0) or \
                           (ship_dir[1] == 0 and empty_dir[1] == 0)
                if same_axis:
                    # Empty is on the extension side - it must be ship to continue
                    deductions.append(make_deduction(
                        enr, enc, CellState.SHIP, "T3.1", 3, 5))

            # If ship has no ship neighbors and only one empty neighbor
            # it must extend into that empty (can't be a submarine - would need 0 empties)
            if len(ship_neighbors) == 0 and len(empty_neighbors) == 1 and blocked_count == 3:
                enr, enc = empty_neighbors[0]
                deductions.append(make_deduction(
                    enr, enc, CellState.SHIP, "T3.1", 3, 5))

    return deductions


@register(tier=3, technique_id="T3.3", difficulty=6)
def overlap_analysis(board: PuzzleBoard) -> List[Deduction]:
    """In contiguous empty segment of L cells needing M ships, positions [L-M, M-1] are forced.

    Example: 5 cells need 4 ships → middle 3 are forced
    [ ? ? ? ? ? ] with 4 needed → [ ? S S S ? ]

    Note: v1 only handles single-segment case.
    """
    deductions = []

    for idx in range(board.dimension):
        for is_row in [True, False]:
            ships, empties, _ = count_in_line(board, idx, is_row)
            clue = get_clue(board, idx, is_row)
            needed = clue - ships

            if needed <= 0:
                continue

            # Find contiguous empty segments
            segments = []
            seg_start = None

            for i in range(board.dimension + 1):
                if i < board.dimension:
                    r, c = (idx, i) if is_row else (i, idx)
                    is_empty = board.cells[r][c].state == CellState.EMPTY
                else:
                    is_empty = False

                if is_empty:
                    if seg_start is None:
                        seg_start = i
                elif seg_start is not None:
                    segments.append((seg_start, i - 1))
                    seg_start = None

            # For single segment containing all empties, apply overlap
            if len(segments) == 1:
                start, end = segments[0]
                L = end - start + 1
                M = needed

                if M > 0 and L >= M and L > M:
                    # Forced positions: [L-M, M-1] in segment coordinates
                    forced_start = L - M
                    forced_end = M - 1

                    for seg_i in range(forced_start, forced_end + 1):
                        i = start + seg_i
                        r, c = (idx, i) if is_row else (i, idx)
                        if board.cells[r][c].state == CellState.EMPTY:
                            deductions.append(make_deduction(
                                r, c, CellState.SHIP, "T3.3", 3, 6))

    return deductions


@register(tier=3, technique_id="T3.4", difficulty=5)
def three_blocked_sides(board: PuzzleBoard) -> List[Deduction]:
    """Ship with 3 orthogonal neighbors blocked → must extend into 4th."""
    deductions = []

    for r in range(board.dimension):
        for c in range(board.dimension):
            if board.cells[r][c].state != CellState.SHIP:
                continue

            blocked = []
            open_neighbors = []

            for dr, dc in ORTHOGONAL:
                nr, nc = r + dr, c + dc
                if not board.within_bounds(nr, nc):
                    blocked.append((dr, dc))
                elif board.cells[nr][nc].state == CellState.SEA:
                    blocked.append((dr, dc))
                elif board.cells[nr][nc].state == CellState.EMPTY:
                    open_neighbors.append((nr, nc))
                # SHIP neighbors don't count as blocked or open

            # If exactly 3 blocked and 1 open, the open must be ship
            # But only if ship isn't already complete (has no ship neighbors)
            ship_neighbors = 0
            for dr, dc in ORTHOGONAL:
                nr, nc = r + dr, c + dc
                if board.within_bounds(nr, nc) and board.cells[nr][nc].state == CellState.SHIP:
                    ship_neighbors += 1

            if len(blocked) == 3 and len(open_neighbors) == 1 and ship_neighbors == 0:
                nr, nc = open_neighbors[0]
                deductions.append(make_deduction(
                    nr, nc, CellState.SHIP, "T3.4", 3, 5))

    return deductions


# =============================================================================
# SHIP TRACKING HELPERS
# =============================================================================

def find_ship_runs(board: PuzzleBoard) -> List[Tuple[int, List[Tuple[int, int]]]]:
    """Find all complete ship runs (bounded by sea/edge on both ends).

    Returns: list of (length, [(r,c), ...]) for each complete ship
    """
    found = []
    visited = set()

    # Horizontal runs
    for r in range(board.dimension):
        c = 0
        while c < board.dimension:
            if board.cells[r][c].state == CellState.SHIP and (r, c) not in visited:
                # Check if start is clean (sea or edge to the left)
                if c > 0 and board.cells[r][c-1].state != CellState.SEA:
                    c += 1
                    continue

                # Collect run
                run = []
                while c < board.dimension and board.cells[r][c].state == CellState.SHIP:
                    run.append((r, c))
                    visited.add((r, c))
                    c += 1

                # Check if end is clean (sea or edge to the right)
                if c < board.dimension and board.cells[r][c].state != CellState.SEA:
                    continue

                # For horizontal runs > 1, this is a complete ship
                if len(run) > 1:
                    found.append((len(run), run))
                elif len(run) == 1:
                    # Check if it's a submarine (vertical neighbors are sea)
                    rr, cc = run[0]
                    above = board.get_state_at(rr-1, cc)
                    below = board.get_state_at(rr+1, cc)
                    if above == CellState.SEA and below == CellState.SEA:
                        found.append((1, run))
            else:
                c += 1

    # Vertical runs (only count if > 1 to avoid double-counting submarines)
    for c in range(board.dimension):
        r = 0
        while r < board.dimension:
            if board.cells[r][c].state == CellState.SHIP and (r, c) not in visited:
                if r > 0 and board.cells[r-1][c].state != CellState.SEA:
                    r += 1
                    continue

                run = []
                while r < board.dimension and board.cells[r][c].state == CellState.SHIP:
                    run.append((r, c))
                    visited.add((r, c))
                    r += 1

                if r < board.dimension and board.cells[r][c].state != CellState.SEA:
                    continue

                if len(run) > 1:
                    found.append((len(run), run))
            else:
                r += 1

    return found


def get_remaining_ships(board: PuzzleBoard) -> List[int]:
    """Get sizes of ships not yet fully placed."""
    placed = [length for length, _ in find_ship_runs(board)]
    remaining = board.fleet.copy()
    for size in placed:
        if size in remaining:
            remaining.remove(size)
    return remaining


def get_largest_remaining(board: PuzzleBoard) -> int:
    """Get the largest ship size still unplaced."""
    remaining = get_remaining_ships(board)
    return max(remaining) if remaining else 0


def is_fleet_consistent(board: PuzzleBoard) -> bool:
    """Check if placed ships are consistent with fleet composition.

    Returns False if:
    - A complete ship is larger than any ship in the fleet
    - More ships of a given size are placed than the fleet allows

    Only checks COMPLETE ships (bounded by sea/edge on both ends).
    Partial/incomplete ships are allowed during solving.
    """
    from collections import Counter

    runs = find_ship_runs(board)
    if not runs:
        return True  # No complete ships yet, consistent

    placed_sizes = [size for size, _ in runs]
    max_fleet_size = max(board.fleet)
    fleet_counts = Counter(board.fleet)
    placed_counts = Counter(placed_sizes)

    # Check for ships larger than any in fleet
    for size in placed_sizes:
        if size > max_fleet_size:
            return False

    # Check for too many ships of any size
    for size, count in placed_counts.items():
        if count > fleet_counts.get(size, 0):
            return False

    return True


# =============================================================================
# TIER 4 - EXPERT (Difficulty 7-8)
# =============================================================================

@register(tier=4, technique_id="T4.1", difficulty=7)
def gap_analysis(board: PuzzleBoard) -> List[Deduction]:
    """Gap smaller than smallest remaining ship → fill with water."""
    deductions = []
    remaining = get_remaining_ships(board)

    if not remaining:
        return deductions

    smallest = min(remaining)

    # Find gaps (contiguous empty cells bounded by sea/edge)
    # Horizontal gaps
    for r in range(board.dimension):
        gap_start = None
        for c in range(board.dimension + 1):
            if c < board.dimension:
                state = board.cells[r][c].state
            else:
                state = CellState.SEA  # Treat edge as sea

            if state == CellState.EMPTY:
                if gap_start is None:
                    gap_start = c
            else:
                if gap_start is not None:
                    gap_len = c - gap_start
                    # Check if bounded by sea/edge on both sides
                    left_blocked = gap_start == 0 or board.cells[r][gap_start-1].state == CellState.SEA
                    right_blocked = state == CellState.SEA

                    if left_blocked and right_blocked and gap_len < smallest:
                        for gc in range(gap_start, c):
                            deductions.append(make_deduction(
                                r, gc, CellState.SEA, "T4.1", 4, 7))
                    gap_start = None

    # Vertical gaps
    for c in range(board.dimension):
        gap_start = None
        for r in range(board.dimension + 1):
            if r < board.dimension:
                state = board.cells[r][c].state
            else:
                state = CellState.SEA

            if state == CellState.EMPTY:
                if gap_start is None:
                    gap_start = r
            else:
                if gap_start is not None:
                    gap_len = r - gap_start
                    top_blocked = gap_start == 0 or board.cells[gap_start-1][c].state == CellState.SEA
                    bottom_blocked = state == CellState.SEA

                    if top_blocked and bottom_blocked and gap_len < smallest:
                        for gr in range(gap_start, r):
                            deductions.append(make_deduction(
                                gr, c, CellState.SEA, "T4.1", 4, 7))
                    gap_start = None

    return deductions


@register(tier=4, technique_id="T4.2", difficulty=7)
def fleet_exhaustion(board: PuzzleBoard) -> List[Deduction]:
    """All ships of a given length placed → prevent new ships of that length."""
    deductions = []
    remaining = get_remaining_ships(board)

    # For each ship length that's fully placed (not in remaining)
    all_lengths = set(board.fleet)
    placed_lengths = all_lengths - set(remaining)

    for length in placed_lengths:
        # Find partial ships that could become this length and block them
        # A partial ship is a run of ships not yet bounded on both ends

        # Horizontal
        for r in range(board.dimension):
            run_start = None
            run_len = 0

            for c in range(board.dimension + 1):
                if c < board.dimension:
                    state = board.cells[r][c].state
                else:
                    state = CellState.SEA

                if state == CellState.SHIP:
                    if run_start is None:
                        run_start = c
                    run_len += 1
                else:
                    if run_start is not None and run_len > 0:
                        # Check if this run could grow to 'length'
                        left_open = run_start > 0 and board.cells[r][run_start-1].state == CellState.EMPTY
                        right_open = c < board.dimension and state == CellState.EMPTY

                        # If run_len < length and could grow to exactly length, block that growth
                        if run_len < length:
                            # Can grow left to make 'length'?
                            if left_open and run_len + 1 == length:
                                deductions.append(make_deduction(
                                    r, run_start-1, CellState.SEA, "T4.2", 4, 7))
                            # Can grow right to make 'length'?
                            if right_open and run_len + 1 == length:
                                deductions.append(make_deduction(
                                    r, c, CellState.SEA, "T4.2", 4, 7))

                    run_start = None
                    run_len = 0

        # Vertical
        for c in range(board.dimension):
            run_start = None
            run_len = 0

            for r in range(board.dimension + 1):
                if r < board.dimension:
                    state = board.cells[r][c].state
                else:
                    state = CellState.SEA

                if state == CellState.SHIP:
                    if run_start is None:
                        run_start = r
                    run_len += 1
                else:
                    if run_start is not None and run_len > 0:
                        top_open = run_start > 0 and board.cells[run_start-1][c].state == CellState.EMPTY
                        bottom_open = r < board.dimension and state == CellState.EMPTY

                        if run_len < length:
                            if top_open and run_len + 1 == length:
                                deductions.append(make_deduction(
                                    run_start-1, c, CellState.SEA, "T4.2", 4, 7))
                            if bottom_open and run_len + 1 == length:
                                deductions.append(make_deduction(
                                    r, c, CellState.SEA, "T4.2", 4, 7))

                    run_start = None
                    run_len = 0

    return deductions


@register(tier=4, technique_id="T4.3", difficulty=7)
def cap_ship(board: PuzzleBoard) -> List[Deduction]:
    """Ship run at max remaining length → cap both ends with water."""
    deductions = []
    max_size = get_largest_remaining(board)

    if max_size == 0:
        return deductions

    # Find runs at max_size
    for r in range(board.dimension):
        run_start = -1
        run_len = 0

        for c in range(board.dimension + 1):
            state = CellState.SEA if c == board.dimension else board.cells[r][c].state

            if state == CellState.SHIP:
                if run_start < 0:
                    run_start = c
                run_len += 1
            else:
                if run_len == max_size:
                    # Cap before
                    if run_start > 0 and board.cells[r][run_start-1].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            r, run_start-1, CellState.SEA, "T4.3", 4, 7))
                    # Cap after
                    end_c = run_start + run_len
                    if end_c < board.dimension and board.cells[r][end_c].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            r, end_c, CellState.SEA, "T4.3", 4, 7))
                run_start = -1
                run_len = 0

    # Vertical
    for c in range(board.dimension):
        run_start = -1
        run_len = 0

        for r in range(board.dimension + 1):
            state = CellState.SEA if r == board.dimension else board.cells[r][c].state

            if state == CellState.SHIP:
                if run_start < 0:
                    run_start = r
                run_len += 1
            else:
                if run_len == max_size:
                    if run_start > 0 and board.cells[run_start-1][c].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            run_start-1, c, CellState.SEA, "T4.3", 4, 7))
                    end_r = run_start + run_len
                    if end_r < board.dimension and board.cells[end_r][c].state == CellState.EMPTY:
                        deductions.append(make_deduction(
                            end_r, c, CellState.SEA, "T4.3", 4, 7))
                run_start = -1
                run_len = 0

    return deductions


@register(tier=4, technique_id="T4.4", difficulty=8)
def prevent_long_join(board: PuzzleBoard) -> List[Deduction]:
    """Empty cell that would join ships into too-long run → water."""
    deductions = []
    max_size = get_largest_remaining(board)

    if max_size == 0:
        return deductions

    for r in range(board.dimension):
        for c in range(board.dimension):
            if board.cells[r][c].state != CellState.EMPTY:
                continue

            # Check horizontal join
            before = 0
            for i in range(c - 1, -1, -1):
                if board.cells[r][i].state == CellState.SHIP:
                    before += 1
                else:
                    break

            after = 0
            for i in range(c + 1, board.dimension):
                if board.cells[r][i].state == CellState.SHIP:
                    after += 1
                else:
                    break

            if before + after + 1 > max_size:
                deductions.append(make_deduction(
                    r, c, CellState.SEA, "T4.4", 4, 8))
                continue

            # Check vertical join
            before = 0
            for i in range(r - 1, -1, -1):
                if board.cells[i][c].state == CellState.SHIP:
                    before += 1
                else:
                    break

            after = 0
            for i in range(r + 1, board.dimension):
                if board.cells[i][c].state == CellState.SHIP:
                    after += 1
                else:
                    break

            if before + after + 1 > max_size:
                deductions.append(make_deduction(
                    r, c, CellState.SEA, "T4.4", 4, 8))

    return deductions


# =============================================================================
# TIER 5 - MASTER (Difficulty 9-10)
# =============================================================================

def _propagate_basic(board: PuzzleBoard, max_iterations: int = 50) -> bool:
    """Apply tiers 1-4 until no progress. Returns True if consistent."""
    from .board import DIAGONAL

    for _ in range(max_iterations):
        progress = False

        # T1.2 Satisfied clue
        for idx in range(board.dimension):
            for is_row in [True, False]:
                ships, empties, _ = count_in_line(board, idx, is_row)
                clue = get_clue(board, idx, is_row)
                if ships == clue:
                    for i in range(board.dimension):
                        r, c = (idx, i) if is_row else (i, idx)
                        if board.cells[r][c].state == CellState.EMPTY:
                            board.cells[r][c].state = CellState.SEA
                            progress = True

        # T1.3 Diagonal water
        for r in range(board.dimension):
            for c in range(board.dimension):
                if board.cells[r][c].state == CellState.SHIP:
                    for dr, dc in DIAGONAL:
                        nr, nc = r + dr, c + dc
                        if board.within_bounds(nr, nc):
                            if board.cells[nr][nc].state == CellState.EMPTY:
                                board.cells[nr][nc].state = CellState.SEA
                                progress = True

        # T1.4 Hint shape deduction
        for r in range(board.dimension):
            for c in range(board.dimension):
                cell = board.cells[r][c]
                if not cell.is_hint or cell.state != CellState.SHIP:
                    continue
                if cell.hint_shape is None:
                    continue
                for (dr, dc), expected in cell.hint_shape.items():
                    nr, nc = r + dr, c + dc
                    if not board.within_bounds(nr, nc):
                        continue
                    if board.cells[nr][nc].state != CellState.EMPTY:
                        continue
                    if expected == CellState.SHIP:
                        board.cells[nr][nc].state = CellState.SHIP
                        progress = True
                    elif expected == CellState.SEA:
                        board.cells[nr][nc].state = CellState.SEA
                        progress = True

        # T2.1 Exact fit
        for idx in range(board.dimension):
            for is_row in [True, False]:
                ships, empties, _ = count_in_line(board, idx, is_row)
                clue = get_clue(board, idx, is_row)
                needed = clue - ships
                if needed > 0 and empties == needed:
                    for i in range(board.dimension):
                        r, c = (idx, i) if is_row else (i, idx)
                        if board.cells[r][c].state == CellState.EMPTY:
                            board.cells[r][c].state = CellState.SHIP
                            progress = True

        # Check consistency
        for idx in range(board.dimension):
            for is_row in [True, False]:
                ships, empties, _ = count_in_line(board, idx, is_row)
                clue = get_clue(board, idx, is_row)
                if ships > clue or ships + empties < clue:
                    return False

        # Check diagonal touching
        for r in range(board.dimension):
            for c in range(board.dimension):
                if board.cells[r][c].state == CellState.SHIP:
                    for dr, dc in DIAGONAL:
                        nr, nc = r + dr, c + dc
                        if board.within_bounds(nr, nc):
                            if board.cells[nr][nc].state == CellState.SHIP:
                                return False

        # Check hint shape consistency
        for r in range(board.dimension):
            for c in range(board.dimension):
                cell = board.cells[r][c]
                if not cell.is_hint or cell.state != CellState.SHIP:
                    continue
                if cell.hint_shape is None:
                    continue
                for (dr, dc), expected in cell.hint_shape.items():
                    nr, nc = r + dr, c + dc
                    if not board.within_bounds(nr, nc):
                        continue
                    placed = board.cells[nr][nc].state
                    if placed == CellState.EMPTY:
                        continue
                    # If placed value contradicts hint metadata, inconsistent.
                    if placed != expected:
                        return False

        # Check fleet consistency - reject invalid fleet compositions
        if not is_fleet_consistent(board):
            return False

        if not progress:
            break

    return True


class _IncrementalPropagator:
    """Fast propagation by tracking dirty lines."""

    def __init__(self, board: PuzzleBoard):
        self.board = board
        self.dim = board.dimension

        # Precompute line counts
        self.row_ships = [0] * self.dim
        self.row_empties = [0] * self.dim
        self.col_ships = [0] * self.dim
        self.col_empties = [0] * self.dim

        for r in range(self.dim):
            for c in range(self.dim):
                state = board.cells[r][c].state
                if state == CellState.SHIP:
                    self.row_ships[r] += 1
                    self.col_ships[c] += 1
                elif state == CellState.EMPTY:
                    self.row_empties[r] += 1
                    self.col_empties[c] += 1

        # Precompute hint constraints from hint_shape metadata.
        self.hint_constraints = {}
        for r in range(self.dim):
            for c in range(self.dim):
                cell = board.cells[r][c]
                if cell.is_hint and cell.state == CellState.SHIP:
                    if cell.hint_shape is None:
                        continue
                    for (dr, dc), expected in cell.hint_shape.items():
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.dim and 0 <= nc < self.dim:
                            self.hint_constraints[(nr, nc)] = expected

    def test_ship(self, r: int, c: int) -> bool:
        """Test if placing ship at (r,c) causes contradiction. Returns True if contradiction."""
        from collections import deque

        # Check hint constraint
        if (r, c) in self.hint_constraints:
            if self.hint_constraints[(r, c)] != CellState.SHIP:
                return True

        # Temporarily place ship
        self.board.cells[r][c].state = CellState.SHIP
        self.row_empties[r] -= 1
        self.col_empties[c] -= 1
        self.row_ships[r] += 1
        self.col_ships[c] += 1

        dirty = deque([('row', r), ('col', c)])
        contradiction = False

        # Add diagonal water
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.dim and 0 <= nc < self.dim:
                if self.board.cells[nr][nc].state == CellState.EMPTY:
                    if (nr, nc) in self.hint_constraints:
                        if self.hint_constraints[(nr, nc)] != CellState.SEA:
                            contradiction = True
                            break
                    self.board.cells[nr][nc].state = CellState.SEA
                    self.row_empties[nr] -= 1
                    self.col_empties[nc] -= 1
                    dirty.append(('row', nr))
                    dirty.append(('col', nc))

        # Propagate
        steps = 0
        while dirty and not contradiction and steps < 200:
            steps += 1
            line_type, idx = dirty.popleft()
            is_row = (line_type == 'row')

            ships = self.row_ships[idx] if is_row else self.col_ships[idx]
            empties = self.row_empties[idx] if is_row else self.col_empties[idx]
            clue = self.board.row_counts[idx] if is_row else self.board.col_counts[idx]
            needed = clue - ships

            if ships > clue or ships + empties < clue:
                contradiction = True
                break

            if ships == clue and empties > 0:
                for i in range(self.dim):
                    rr, cc = (idx, i) if is_row else (i, idx)
                    if self.board.cells[rr][cc].state == CellState.EMPTY:
                        if (rr, cc) in self.hint_constraints:
                            if self.hint_constraints[(rr, cc)] != CellState.SEA:
                                contradiction = True
                                break
                        self.board.cells[rr][cc].state = CellState.SEA
                        self.row_empties[rr] -= 1
                        self.col_empties[cc] -= 1
                        dirty.append(('row', rr))
                        dirty.append(('col', cc))

            elif needed > 0 and empties == needed:
                for i in range(self.dim):
                    rr, cc = (idx, i) if is_row else (i, idx)
                    if self.board.cells[rr][cc].state == CellState.EMPTY:
                        # Check diagonal conflict
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            nr, nc = rr + dr, cc + dc
                            if 0 <= nr < self.dim and 0 <= nc < self.dim:
                                if self.board.cells[nr][nc].state == CellState.SHIP:
                                    contradiction = True
                                    break
                        if contradiction:
                            break
                        if (rr, cc) in self.hint_constraints:
                            if self.hint_constraints[(rr, cc)] != CellState.SHIP:
                                contradiction = True
                                break
                        self.board.cells[rr][cc].state = CellState.SHIP
                        self.row_empties[rr] -= 1
                        self.col_empties[cc] -= 1
                        self.row_ships[rr] += 1
                        self.col_ships[cc] += 1
                        dirty.append(('row', rr))
                        dirty.append(('col', cc))
                        # Diagonal water for new ship
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            nr, nc = rr + dr, cc + dc
                            if 0 <= nr < self.dim and 0 <= nc < self.dim:
                                if self.board.cells[nr][nc].state == CellState.EMPTY:
                                    if (nr, nc) in self.hint_constraints:
                                        if self.hint_constraints[(nr, nc)] != CellState.SEA:
                                            contradiction = True
                                            break
                                    self.board.cells[nr][nc].state = CellState.SEA
                                    self.row_empties[nr] -= 1
                                    self.col_empties[nc] -= 1
                                    dirty.append(('row', nr))
                                    dirty.append(('col', nc))

        # Check fleet consistency
        if not contradiction and not is_fleet_consistent(self.board):
            contradiction = True

        return contradiction

    def test_water(self, r: int, c: int) -> bool:
        """Test if placing water at (r,c) causes contradiction. Returns True if contradiction."""
        from collections import deque

        # Check hint constraint
        if (r, c) in self.hint_constraints:
            if self.hint_constraints[(r, c)] != CellState.SEA:
                return True

        # Temporarily place water
        self.board.cells[r][c].state = CellState.SEA
        self.row_empties[r] -= 1
        self.col_empties[c] -= 1

        dirty = deque([('row', r), ('col', c)])
        contradiction = False

        # Propagate (same logic as test_ship but simpler - no diagonal water needed)
        steps = 0
        while dirty and not contradiction and steps < 200:
            steps += 1
            line_type, idx = dirty.popleft()
            is_row = (line_type == 'row')

            ships = self.row_ships[idx] if is_row else self.col_ships[idx]
            empties = self.row_empties[idx] if is_row else self.col_empties[idx]
            clue = self.board.row_counts[idx] if is_row else self.board.col_counts[idx]
            needed = clue - ships

            if ships > clue or ships + empties < clue:
                contradiction = True
                break

            if ships == clue and empties > 0:
                for i in range(self.dim):
                    rr, cc = (idx, i) if is_row else (i, idx)
                    if self.board.cells[rr][cc].state == CellState.EMPTY:
                        if (rr, cc) in self.hint_constraints:
                            if self.hint_constraints[(rr, cc)] != CellState.SEA:
                                contradiction = True
                                break
                        self.board.cells[rr][cc].state = CellState.SEA
                        self.row_empties[rr] -= 1
                        self.col_empties[cc] -= 1
                        dirty.append(('row', rr))
                        dirty.append(('col', cc))

            elif needed > 0 and empties == needed:
                for i in range(self.dim):
                    rr, cc = (idx, i) if is_row else (i, idx)
                    if self.board.cells[rr][cc].state == CellState.EMPTY:
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            nr, nc = rr + dr, cc + dc
                            if 0 <= nr < self.dim and 0 <= nc < self.dim:
                                if self.board.cells[nr][nc].state == CellState.SHIP:
                                    contradiction = True
                                    break
                        if contradiction:
                            break
                        if (rr, cc) in self.hint_constraints:
                            if self.hint_constraints[(rr, cc)] != CellState.SHIP:
                                contradiction = True
                                break
                        self.board.cells[rr][cc].state = CellState.SHIP
                        self.row_empties[rr] -= 1
                        self.col_empties[cc] -= 1
                        self.row_ships[rr] += 1
                        self.col_ships[cc] += 1
                        dirty.append(('row', rr))
                        dirty.append(('col', cc))
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            nr, nc = rr + dr, cc + dc
                            if 0 <= nr < self.dim and 0 <= nc < self.dim:
                                if self.board.cells[nr][nc].state == CellState.EMPTY:
                                    if (nr, nc) in self.hint_constraints:
                                        if self.hint_constraints[(nr, nc)] != CellState.SEA:
                                            contradiction = True
                                            break
                                    self.board.cells[nr][nc].state = CellState.SEA
                                    self.row_empties[nr] -= 1
                                    self.col_empties[nc] -= 1
                                    dirty.append(('row', nr))
                                    dirty.append(('col', nc))

        # Check fleet consistency
        if not contradiction and not is_fleet_consistent(self.board):
            contradiction = True

        return contradiction


# Toggle for fast vs accurate T5
USE_INCREMENTAL_T5 = True


@register(tier=5, technique_id="T5.1", difficulty=9)
def naked_water(board: PuzzleBoard) -> List[Deduction]:
    """If placing ship in cell → contradiction, cell must be water."""
    deductions = []

    if USE_INCREMENTAL_T5:
        prop = _IncrementalPropagator(board)
        empties = [(r, c) for r in range(board.dimension)
                   for c in range(board.dimension)
                   if board.cells[r][c].state == CellState.EMPTY]

        for r, c in empties:
            snapshot = board.get_snapshot()
            if prop.test_ship(r, c):
                deductions.append(make_deduction(r, c, CellState.SEA, "T5.1", 5, 9))
            board.restore_snapshot(snapshot)
            # Re-init propagator after restore
            prop = _IncrementalPropagator(board)
    else:
        for r in range(board.dimension):
            for c in range(board.dimension):
                if board.cells[r][c].state != CellState.EMPTY:
                    continue
                snapshot = board.get_snapshot()
                board.cells[r][c].state = CellState.SHIP
                is_consistent = _propagate_basic(board)
                board.restore_snapshot(snapshot)
                if not is_consistent:
                    deductions.append(make_deduction(r, c, CellState.SEA, "T5.1", 5, 9))

    return deductions


@register(tier=5, technique_id="T5.2", difficulty=9)
def naked_ship(board: PuzzleBoard) -> List[Deduction]:
    """If placing water in cell → contradiction, cell must be ship."""
    deductions = []

    if USE_INCREMENTAL_T5:
        prop = _IncrementalPropagator(board)
        empties = [(r, c) for r in range(board.dimension)
                   for c in range(board.dimension)
                   if board.cells[r][c].state == CellState.EMPTY]

        for r, c in empties:
            snapshot = board.get_snapshot()
            if prop.test_water(r, c):
                deductions.append(make_deduction(r, c, CellState.SHIP, "T5.2", 5, 9))
            board.restore_snapshot(snapshot)
            prop = _IncrementalPropagator(board)
    else:
        for r in range(board.dimension):
            for c in range(board.dimension):
                if board.cells[r][c].state != CellState.EMPTY:
                    continue
                snapshot = board.get_snapshot()
                board.cells[r][c].state = CellState.SEA
                is_consistent = _propagate_basic(board)
                board.restore_snapshot(snapshot)
                if not is_consistent:
                    deductions.append(make_deduction(r, c, CellState.SHIP, "T5.2", 5, 9))

    return deductions
