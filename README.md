# bimaru-logical-solver

A pure logic solver for Bimaru (Battleship Solitaire).

I hope this project will help us build the best logical bimaru solver ever made.

## What This Repo Includes

- Board data structures (`PuzzleBoard`, `CellState`, `GridCell`)
- Deduction rules (`T1` to `T5` tiers)
- Tiered logical solver (`TieredSolver`) with solve metadata (`SolveResult`)

## Tier System:

The solver runs in escalating tiers. It always starts at `T1`, and when a deduction is applied it restarts from `T1` again. This keeps the solve path as "human-like" as possible: use the simplest valid rule first, then only escalate when needed.

### `T1` Basic (Difficulty 1-2)

Fast local constraints. These are the first-pass rules you would usually do by hand.

- `T1.1` Zero clue: if a row/column clue is `0`, all unknown cells in that line are sea.
- `T1.2` Satisfied clue: if a line already has its full ship count, remaining unknowns are sea.
- `T1.3` Diagonal water: ships cannot touch diagonally, so diagonal neighbors of ships become sea.
- `T1.4` Hint-shape deduction: ship hints with shape metadata force specific orthogonal neighbors to ship or sea.

### `T2` Intermediate (Difficulty 3-4)

Line-capacity logic. Still straightforward, but less local than `T1`.

- `T2.1` Exact fit: if ships needed equals empty cells in a line, all empties are ships.
- `T2.4` Overflow prevention: if a row/column is already at clue capacity, remaining unknowns in that line are sea.

### `T3` Advanced (Difficulty 5-6)

Structure-aware deductions on partial ship geometry and constrained segments.

- `T3.1` Forced extension: when a ship fragment can legally extend in only one direction, extend it.
- `T3.3` Overlap analysis: in a single contiguous empty segment, overlap of all legal placements produces forced ship cells.
- `T3.4` Three blocked sides: if a ship cell has three orthogonal sides blocked, the fourth open side must be ship.

### `T4` Expert (Difficulty 7-8)

Fleet-composition reasoning (remaining ship sizes) combined with spatial constraints.

- `T4.1` Gap analysis: a bounded empty gap shorter than the smallest remaining ship must be sea.
- `T4.2` Fleet exhaustion: if all ships of a length are already placed, block moves that would create another one.
- `T4.3` Cap ship: if a run already matches the largest remaining ship size, both ends are capped with sea.
- `T4.4` Prevent long join: if filling a cell would create a ship run longer than allowed, that cell is sea.

### `T5` Master (Difficulty 9-10)

Contradiction-based forcing without branching search. This is stronger than local heuristics but still rule-based.

- `T5.1` "Naked water" (like sudoku): if assuming a cell is ship leads to contradiction, the cell must be sea.
- `T5.2` "Naked ship": if assuming a cell is sea leads to contradiction, the cell must be ship.

`T5` internally uses propagation and consistency checks (clues, diagonal rule, hint-shape consistency, fleet consistency).

## Install

```bash
python3 -m pip install -e .
```

## Quick Start

```python
from bimaru_solver import PuzzleBoard, CellState, TieredSolver

board = PuzzleBoard()
board.row_counts = [0,2,4,1,4,2,0,1,5,1]
board.col_counts = [2,2,4,1,2,1,2,3,2,1]

solver = TieredSolver(board)
result = solver.solve()

print(result.solved, result.valid, result.stuck)
```

## Input Model

Solver inputs are provided through `PuzzleBoard`:

- `row_counts`: list of row ship totals
- `col_counts`: list of column ship totals
- `cells[r][c].state`: current cell state (`EMPTY`, `SEA`, `SHIP`)
- `cells[r][c].is_hint`: whether the cell is a fixed hint
- `cells[r][c].hint_shape`: optional hint-neighbor constraints

## Example Script

Run:

```bash
python3 examples/solve_from_json.py tests/fixtures/puzzle_sample.json
```

The script reads a puzzle JSON with `clues` and `initial_hints`.

## Public API

- `CellState`, `GridCell`, `PuzzleBoard`
- `Deduction`
- `TieredSolver`, `SolveResult`

## Try Bimaru Online (Zolelot)

Want to play instead of code? Try the original puzzle site: **https://zolelot.com**

`zolelot` is where I publish Bimaru/Battleship Solitaire puzzles daily for humans. This solver repo is focused on the logic engine behind that style of puzzle.

## Contributing

Pull requests are welcome.

If you have a bug fix, improvement, test idea, or docs update, feel free to open a PR.
