import io
import json
from pathlib import Path

from csv2json.cli import main


def test_cli_stdin_to_stdout_pretty() -> None:
    stdin = io.StringIO("a,b\n1,2\n")
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = main(["--pretty"], stdin=stdin, stdout=stdout, stderr=stderr)
    assert code == 0
    assert stderr.getvalue() == ""

    out = stdout.getvalue()
    parsed = json.loads(out)
    assert parsed == [{"a": "1", "b": "2"}]


def test_cli_file_to_file(tmp_path: Path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"

    input_path.write_text("x\ny\n", encoding="utf-8")

    stdout = io.StringIO()
    stderr = io.StringIO()

    code = main(
        [str(input_path), "--output", str(output_path)],
        stdout=stdout,
        stderr=stderr,
    )
    assert code == 0
    assert stderr.getvalue() == ""

    parsed = json.loads(output_path.read_text(encoding="utf-8"))
    assert parsed == [{"x": "y"}]
