"""Tests for fleet composition validation during solving."""

from collections import Counter

from bimaru_solver.board import CellState, PuzzleBoard
from bimaru_solver.rules import find_ship_runs, is_fleet_consistent, _propagate_basic


def test_find_ship_runs_counts_complete_ships() -> None:
    """find_ship_runs should identify complete ships bounded by sea/edge."""
    board = PuzzleBoard()
    for c in range(3):
        board.cells[0][c].state = CellState.SHIP
    board.cells[0][3].state = CellState.SEA

    for r in range(2):
        board.cells[r][5].state = CellState.SHIP
    board.cells[2][5].state = CellState.SEA

    runs = find_ship_runs(board)
    sizes = sorted([size for size, _ in runs], reverse=True)
    assert sizes == [3, 2]


def test_too_many_ships_of_same_size_detected() -> None:
    """Detect when more complete ships of a size exist than fleet allows."""
    board = PuzzleBoard()
    for c in range(4):
        board.cells[0][c].state = CellState.SHIP
    board.cells[0][4].state = CellState.SEA

    for c in range(4):
        board.cells[2][c].state = CellState.SHIP
    board.cells[2][4].state = CellState.SEA

    runs = find_ship_runs(board)
    placed_sizes = [size for size, _ in runs]
    fleet_counts = Counter(board.fleet)
    placed_counts = Counter(placed_sizes)

    assert placed_counts[4] == 2
    assert fleet_counts[4] == 1
    assert any(placed_counts[size] > fleet_counts[size] for size in placed_counts)


def test_is_fleet_consistent_helper() -> None:
    """Test fleet consistency helper on valid and invalid states."""
    board = PuzzleBoard()
    assert is_fleet_consistent(board)

    for c in range(3):
        board.cells[0][c].state = CellState.SHIP
    board.cells[0][3].state = CellState.SEA
    assert is_fleet_consistent(board)

    for c in range(3):
        board.cells[2][c].state = CellState.SHIP
    board.cells[2][3].state = CellState.SEA
    assert is_fleet_consistent(board)

    for c in range(3):
        board.cells[4][c].state = CellState.SHIP
    board.cells[4][3].state = CellState.SEA
    assert not is_fleet_consistent(board)


def test_is_fleet_consistent_rejects_oversized_ships() -> None:
    """is_fleet_consistent should reject ships larger than any in fleet."""
    board = PuzzleBoard()
    for c in range(5):
        board.cells[0][c].state = CellState.SHIP
    board.cells[0][5].state = CellState.SEA
    assert not is_fleet_consistent(board)


def test_propagate_basic_rejects_too_many_battleships() -> None:
    """_propagate_basic should fail for impossible fleet composition."""
    board = PuzzleBoard()
    board.row_counts = [4, 0, 4, 0, 0, 0, 0, 0, 0, 0]
    board.col_counts = [2, 2, 2, 2, 0, 0, 0, 0, 0, 0]

    for c in range(4):
        board.cells[0][c].state = CellState.SHIP
        board.cells[2][c].state = CellState.SHIP

    assert not _propagate_basic(board)
