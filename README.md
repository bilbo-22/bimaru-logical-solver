# bimaru-logical-solver

A pure logic solver for Bimaru (Battleship Solitaire).

If you are learning puzzle-solving techniques, building puzzle tooling, or benchmarking logical deduction engines, this project is a friendly starting point.

## What This Repo Includes

- Board data structures (`PuzzleBoard`, `CellState`, `GridCell`)
- Deduction rules (`T1` to `T5` tiers)
- Tiered logical solver (`TieredSolver`) with solve metadata (`SolveResult`)

## What This Repo Does Not Include

- Puzzle generation / fleet deployment
- Hint optimization / uniqueness search
- DFS-based generation helpers
- Frontend or website code

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

# Optional: set solution to validate against an intended grid
# board.cells[r][c].solution = CellState(...)

solver = TieredSolver(board)
result = solver.solve()

print(result.solved, result.valid, result.max_tier_required, result.difficulty_score)
```

## Input Model

Solver inputs are provided through `PuzzleBoard`:

- `row_counts`: list of row ship totals
- `col_counts`: list of column ship totals
- `cells[r][c].state`: current cell state (`EMPTY`, `SEA`, `SHIP`)
- `cells[r][c].is_hint`: whether the cell is a fixed hint
- `cells[r][c].hint_shape`: optional hint-neighbor constraints

Optional validation field:

- `cells[r][c].solution`: expected final state; used by `result.valid`

## Example Script

Run:

```bash
python3 examples/solve_from_json.py tests/fixtures/puzzle_sample.json
```

The script reads a puzzle JSON with `clues`, `initial_hints`, and optional `solution`.

## Public API

- `CellState`, `GridCell`, `PuzzleBoard`
- `Deduction`
- `TieredSolver`, `SolveResult`, `T5Detail`

## Try Bimaru Online (Zolelot)

Want to play instead of code? Try my puzzle site: **https://zolelot.com**

`zolelot` is where I publish Bimaru/Battleship Solitaire puzzles for humans. This solver repo is focused on the logic engine behind that style of puzzle.
