# ruff: noqa: E501

from __future__ import annotations

import asyncio
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from csv2json.ingest import IngestOptions, ingest_file

app = FastAPI(title="csv2json")

# Upload/job settings (override via environment variables)
MAX_UPLOAD_BYTES = int(os.getenv("CSV2JSON_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50MB
JOB_RESULT_TTL_SECONDS = int(os.getenv("CSV2JSON_JOB_TTL_SECONDS", str(10 * 60)))  # 10 minutes
JOB_TIMEOUT_SECONDS = int(os.getenv("CSV2JSON_JOB_TIMEOUT_SECONDS", str(120)))  # per job


@dataclass
class Job:
    status: str  # queued|running|done|error
    created_at: float
    filename: str
    result: Any | None = None
    error: str | None = None


JOBS: dict[str, Job] = {}


def _cleanup_jobs() -> None:
    now = time.time()
    expired = [
        job_id
        for job_id, job in JOBS.items()
        if now - job.created_at > JOB_RESULT_TTL_SECONDS
    ]
    for job_id in expired:
        JOBS.pop(job_id, None)


async def _save_upload_to_temp(upload: UploadFile) -> tuple[str, str]:
    """Save UploadFile to disk without loading the whole file into memory."""

    suffix = Path(upload.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        size = 0
        while True:
            chunk = await upload.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                tmp_path = tmp.name
                tmp.close()
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                raise ValueError(
                    f"File too large. Max upload is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
                )
            tmp.write(chunk)

        return tmp.name, upload.filename or "upload"


def _run_ingest(tmp_path: str, filename: str, options: IngestOptions) -> Any:
    return ingest_file(tmp_path, filename=filename, options=options)


async def _process_job(job_id: str, tmp_path: str, filename: str, options: IngestOptions) -> None:
    try:
        job = JOBS[job_id]
        job.status = "running"
        # Ingest is CPU-bound / blocking; run in a thread to keep the server responsive.
        # We also enforce a timeout so large/slow files fail with a clear error instead of
        # keeping the job "running" forever.
        data = await asyncio.wait_for(
            asyncio.to_thread(_run_ingest, tmp_path, filename, options),
            timeout=JOB_TIMEOUT_SECONDS,
        )
        job.result = data
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        JOBS[job_id].status = "error"
        JOBS[job_id].error = str(exc)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        _cleanup_jobs()


INDEX_HTML = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>File → JSON</title>
    <link
      rel=\"stylesheet\"
      href=\"https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css\"
    />
    <style>
      :root { --pico-font-size: 100%; }
      .container { max-width: 1100px; }
      pre { max-height: 60vh; overflow: auto; }
      .grid-2 { display: grid; gap: 1rem; grid-template-columns: 1fr; }
      @media (min-width: 900px) { .grid-2 { grid-template-columns: 1fr 1fr; } }
      .muted { opacity: 0.7; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
  </head>
  <body>
    <main class=\"container\">
      <h1>File → JSON</h1>
      <p class=\"muted\">Convert CSV/TSV/XLSX/PDF into JSON. PDFs can be extracted as tables, text, or both.</p>

      <article>
        <form id=\"convertForm\">
          <div class=\"grid\">
            <label>
              File
              <input type=\"file\" id=\"inFile\" name=\"file\" accept=\".csv,.tsv,.xlsx,.pdf,text/csv\" required />
            </label>

            <label>
              Format
              <select id=\"format\" name=\"format\">
                <option value=\"auto\" selected>auto (by file extension)</option>
                <option value=\"csv\">csv</option>
                <option value=\"tsv\">tsv</option>
                <option value=\"xlsx\">xlsx</option>
                <option value=\"pdf\">pdf</option>
              </select>
            </label>

            <label>
              Delimiter (CSV only)
              <input type=\"text\" id=\"delimiter\" name=\"delimiter\" value=\",\" maxlength=\"5\" />
              <small class=\"muted\">Examples: <code>,</code> <code>;</code> <code>\\t</code></small>
            </label>

            <label>
              Encoding (CSV only)
              <select id=\"encoding\" name=\"encoding\">
                <option value=\"utf-8\" selected>utf-8</option>
                <option value=\"utf-8-sig\">utf-8-sig</option>
                <option value=\"cp1252\">cp1252</option>
                <option value=\"latin-1\">latin-1</option>
              </select>
            </label>

            <label>
              PDF mode
              <select id=\"pdfMode\" name=\"pdfMode\">
                <option value=\"auto\" selected>auto (tables then text)</option>
                <option value=\"tables\">tables only</option>
                <option value=\"text\">text only</option>
                <option value=\"both\">both</option>
              </select>
            </label>

            <label>
              Max PDF pages
              <input type=\"number\" id=\"maxPdfPages\" name=\"maxPdfPages\" value=\"25\" min=\"1\" max=\"500\" />
            </label>

            <label>
              Max PDF text chars
              <input type=\"number\" id=\"maxPdfChars\" name=\"maxPdfChars\" value=\"2000000\" min=\"1000\" max=\"50000000\" />
              <small class=\"muted\">Prevents huge responses for large PDFs.</small>
            </label>

            <label>
              Pretty-print
              <input type=\"checkbox\" id=\"pretty\" checked />
            </label>
          </div>

          <div class=\"grid\">
            <button type=\"submit\" id=\"convertBtn\">Convert</button>
            <button type=\"button\" id=\"copyBtn\" disabled>Copy JSON</button>
            <button type=\"button\" id=\"downloadBtn\" disabled>Download JSON</button>
          </div>
        </form>
      </article>

      <div class=\"grid-2\">
        <article>
          <header><strong>Status</strong></header>
          <div id=\"status\" class=\"muted\">Choose a file and click Convert.</div>
          <div class=\"muted\">Jobs auto-expire after ~10 minutes. Large PDFs may take time; the UI will keep polling.</div>
        </article>

        <article>
          <header><strong>Output</strong></header>
          <pre><code id=\"output\" class=\"mono\"></code></pre>
        </article>
      </div>
    </main>

    <script>
      const form = document.getElementById('convertForm');
      const statusEl = document.getElementById('status');
      const outputEl = document.getElementById('output');
      const copyBtn = document.getElementById('copyBtn');
      const downloadBtn = document.getElementById('downloadBtn');

      let lastJsonText = '';

      function setStatus(text, isError=false) {
        statusEl.textContent = text;
        statusEl.style.color = isError ? 'var(--pico-del-color)' : '';
      }

      function normalizeDelimiter(s) {
        if (s === '\\t') return '\t';
        return s;
      }

      async function pollJob(jobId, pretty, filename) {
        const start = Date.now();
        while (true) {
          const resp = await fetch(`/api/jobs/${jobId}`);
          const payload = await resp.json();

          if (!resp.ok) {
            setStatus(payload?.error ? `Error: ${payload.error}` : `Error: HTTP ${resp.status}`, true);
            return;
          }

          if (payload.status === 'done') {
            lastJsonText = pretty ? JSON.stringify(payload.result, null, 2) : JSON.stringify(payload.result);
            outputEl.textContent = lastJsonText;
            setStatus(`Converted ${filename}`);
            copyBtn.disabled = false;
            downloadBtn.disabled = false;
            return;
          }

          if (payload.status === 'error') {
            setStatus(`Error: ${payload.error || 'Unknown error'}`, true);
            return;
          }

          const elapsed = Math.floor((Date.now() - start) / 1000);
          setStatus(`Processing… (${elapsed}s)`);
          await new Promise(r => setTimeout(r, 800));
        }
      }

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        outputEl.textContent = '';
        lastJsonText = '';
        copyBtn.disabled = true;
        downloadBtn.disabled = true;

        const fileInput = document.getElementById('inFile');
        const format = document.getElementById('format').value;
        const delimiterInput = document.getElementById('delimiter');
        const encodingInput = document.getElementById('encoding');
        const pdfMode = document.getElementById('pdfMode').value;
        const maxPdfPages = document.getElementById('maxPdfPages').value;
        const maxPdfChars = document.getElementById('maxPdfChars').value;
        const pretty = document.getElementById('pretty').checked;

        if (!fileInput.files || fileInput.files.length === 0) {
          setStatus('No file selected.', true);
          return;
        }

        const file = fileInput.files[0];

        const fd = new FormData();
        fd.append('file', file);
        fd.append('format', format);
        fd.append('delimiter', normalizeDelimiter(delimiterInput.value || ','));
        fd.append('encoding', encodingInput.value || 'utf-8');
        fd.append('pdf_mode', pdfMode || 'auto');
        fd.append('max_pdf_pages', maxPdfPages || '25');
        fd.append('max_pdf_chars', maxPdfChars || '2000000');

        setStatus('Uploading…');

        try {
          const resp = await fetch('/api/jobs', { method: 'POST', body: fd });
          const payload = await resp.json();

          if (!resp.ok) {
            setStatus(payload?.error ? `Error: ${payload.error}` : `Error: HTTP ${resp.status}`, true);
            return;
          }

          setStatus('Queued…');
          await pollJob(payload.job_id, pretty, file.name);
        } catch (err) {
          setStatus(`Error: ${err}`, true);
        }
      });

      copyBtn.addEventListener('click', async () => {
        if (!lastJsonText) return;
        await navigator.clipboard.writeText(lastJsonText);
        setStatus('Copied JSON to clipboard.');
      });

      downloadBtn.addEventListener('click', () => {
        if (!lastJsonText) return;
        const blob = new Blob([lastJsonText + "\\n"], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'output.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setStatus('Downloaded output.json');
      });
    </script>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),  # noqa: B008
    format: str = Form("auto"),  # noqa: A002
    delimiter: str = Form(","),
    encoding: str = Form("utf-8"),
    pdf_mode: str = Form("auto"),
    max_pdf_pages: int = Form(25),
    max_pdf_chars: int = Form(2_000_000),
) -> Any:
    try:
        tmp_path, filename = await _save_upload_to_temp(file)
        job_id = uuid.uuid4().hex
        JOBS[job_id] = Job(status="queued", created_at=time.time(), filename=filename)

        options = IngestOptions(
            format=format,
            delimiter=delimiter,
            encoding=encoding,
            pdf_mode=pdf_mode,
            max_pdf_pages=max_pdf_pages,
            max_pdf_chars=max_pdf_chars,
        )

        asyncio.create_task(_process_job(job_id, tmp_path, filename, options))
        _cleanup_jobs()
        return JSONResponse(content={"job_id": job_id})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> Any:
    _cleanup_jobs()
    job = JOBS.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found (expired?)"})

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": job.status,
            "filename": job.filename,
            "result": job.result if job.status == "done" else None,
            "error": job.error if job.status == "error" else None,
        }
    )


# Backwards-compatible endpoint for small CSVs (kept for API users).
@app.post("/api/convert")
async def api_convert(
    file: UploadFile = File(...),  # noqa: B008
    delimiter: str = Form(","),
    encoding: str = Form("utf-8"),
) -> Any:
    try:
        tmp_path, filename = await _save_upload_to_temp(file)
        try:
            data = await asyncio.to_thread(
                _run_ingest,
                tmp_path,
                filename,
                IngestOptions(format="csv", delimiter=delimiter, encoding=encoding),
            )
            return JSONResponse(content=data)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"error": str(exc)})


def main() -> None:
    import uvicorn

    uvicorn.run(
        "csv2json.web:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
