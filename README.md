# csv-to-json-cli
A small command-line tool that converts CSV input into JSON.

## Requirements
- Python 3.10+

## Install (editable, local)
```bash
python -m pip install -e .
```

## Usage
Convert a file:
```bash
csv2json input.csv --pretty > output.json
```

Read from stdin:
```bash
type input.csv | csv2json --pretty
```

Write to a file:
```bash
csv2json input.csv --output output.json
```

## Web UI (upload file → JSON)
Supported inputs:
- `.csv`, `.tsv`
- `.xlsx` (first worksheet)
- `.pdf` (tables and/or text; extracted per page)

For PDFs, the UI supports `pdf_mode`:
- `auto` (try tables; if none, fall back to text)
- `tables` (tables only)
- `text` (text only)
- `both` (returns both)

Install web dependencies:
```bash
python -m pip install -e ".[web]"
```
Run the server (dev reload):
```bash
python -m uvicorn csv2json.web:app --reload --port 8000
```
Then open http://127.0.0.1:8000 in your browser.

### Upload size limit
The web server enforces a max upload size (default **50MB**). Override with:
- `CSV2JSON_MAX_UPLOAD_BYTES` (bytes)

### Job timeout
Each conversion job has a timeout (default **120s**) to avoid getting stuck.
Override with:
- `CSV2JSON_JOB_TIMEOUT_SECONDS`

Options:
- `--delimiter` (default `,`)
- `--encoding` (default `utf-8`) for reading the input file
- `--pretty` to pretty-print JSON

## Output format
The output is a JSON array of objects, using the CSV header row as keys.
