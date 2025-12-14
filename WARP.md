# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project overview
`csv2json-cli` is a small Python (>=3.10) CLI that converts CSV input into a JSON array of objects (CSV header row becomes object keys).

Entry points:
- Console script: `csv2json` (configured in `pyproject.toml` as `csv2json = "csv2json.cli:main"`).
- Module entry: `python -m csv2json` (via `src/csv2json/__main__.py`).

## Repo structure (big picture)
- `src/csv2json/cli.py`: CLI layer.
  - `build_parser()` defines the argparse interface.
  - `main(argv=None, *, stdin, stdout, stderr) -> int` is the core entrypoint; it accepts injected IO streams for testability.
  - Handles opening/closing files based on args and delegates conversion + JSON writing.
- `src/csv2json/converter.py`: conversion primitives.
  - `convert_csv_text(fp, delimiter=",") -> list[dict[str, str]]`: uses `csv.DictReader`; raises if no header row.
  - `write_json(data, fp, pretty=False)`: `json.dump(...)` and always appends a trailing newline.
- `tests/`: pytest tests.
  - `tests/test_converter.py` covers conversion behavior.
  - `tests/test_cli.py` exercises `cli.main(...)` using in-memory streams and temp paths.

## Common commands
All commands below assume you run them from the repo root.

### Setup (editable install)
```powershell path=null start=null
python -m pip install -e ".[dev]"
```
Notes:
- The `dev` extra installs `pytest` and `ruff` (see `pyproject.toml`).

### Run the CLI
After editable install:
```powershell path=null start=null
csv2json input.csv --pretty > output.json
```
Without installing (module entrypoint):
```powershell path=null start=null
python -m csv2json input.csv --pretty
```
Read from stdin (PowerShell):
```powershell path=null start=null
Get-Content -Raw input.csv | csv2json --pretty
```

### Run the Web UI
Supported inputs: `.csv`, `.tsv`, `.xlsx` (first sheet), `.pdf` (tables and/or text).

Install web dependencies:
```powershell path=null start=null
python -m pip install -e ".[web]"
```
Run the dev server:
```powershell path=null start=null
python -m uvicorn csv2json.web:app --reload --port 8000
```
Then open `http://127.0.0.1:8000/`.

### Web limits (large files)
- Max upload size defaults to 50MB.
- Override via environment variable:
```powershell path=null start=null
$env:CSV2JSON_MAX_UPLOAD_BYTES = 104857600  # 100MB
python -m uvicorn csv2json.web:app --reload --port 8000
```
- Large conversions run as background jobs; the UI polls `/api/jobs/{job_id}` so requests don’t hang.
- Jobs enforce a timeout (default 120s) via `CSV2JSON_JOB_TIMEOUT_SECONDS`.

### Tests
Run all tests:
```powershell path=null start=null
pytest
```
Run a single test file:
```powershell path=null start=null
pytest tests/test_cli.py
```
Run a single test:
```powershell path=null start=null
pytest tests/test_cli.py::test_cli_stdin_to_stdout_pretty
```

### Linting (ruff)
Run lint:
```powershell path=null start=null
ruff check .
```
Auto-fix what can be fixed safely:
```powershell path=null start=null
ruff check . --fix
```
If you use ruff formatting in your workflow:
```powershell path=null start=null
ruff format .
```

### Build a wheel/sdist
This project uses Hatchling as the build backend.
```powershell path=null start=null
python -m pip install build
python -m build
```
