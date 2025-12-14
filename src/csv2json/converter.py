from __future__ import annotations

import csv
import json
from typing import IO, Any


def convert_csv_text(fp: IO[str], *, delimiter: str = ",") -> list[dict[str, str]]:
    """Convert a CSV text stream into a list of dict rows.

    Expects a header row; keys come from the header.
    """

    reader = csv.DictReader(fp, delimiter=delimiter)

    # If the CSV is empty, DictReader.fieldnames will be None.
    if reader.fieldnames is None:
        raise ValueError("CSV input has no header row (empty input?)")

    return [dict(row) for row in reader]


def write_json(data: Any, fp: IO[str], *, pretty: bool = False) -> None:
    """Write JSON to a text stream, always ending with a trailing newline."""

    if pretty:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    else:
        json.dump(data, fp, ensure_ascii=False)

    fp.write("\n")
