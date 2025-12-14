from pathlib import Path

import pytest

from csv2json.ingest import IngestOptions, detect_format, ingest_file


def test_detect_format() -> None:
    assert detect_format("a.csv") == "csv"
    assert detect_format("a.tsv") == "tsv"
    assert detect_format("a.xlsx") == "xlsx"
    assert detect_format("a.pdf") == "pdf"
    assert detect_format("a.unknown") == "csv"


def test_ingest_csv_via_file(tmp_path: Path) -> None:
    p = tmp_path / "in.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")

    data = ingest_file(p, filename="in.csv", options=IngestOptions(format="auto"))
    assert data == [{"a": "1", "b": "2"}]


def test_ingest_xlsx_optional(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    Workbook = openpyxl.Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "age"])
    ws.append(["Alice", 30])

    p = tmp_path / "in.xlsx"
    wb.save(p)

    data = ingest_file(p, filename="in.xlsx", options=IngestOptions(format="auto"))
    assert data == [{"name": "Alice", "age": 30}]
