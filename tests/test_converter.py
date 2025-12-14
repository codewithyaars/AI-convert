import io

import pytest

from csv2json.converter import convert_csv_text


def test_convert_csv_text_basic() -> None:
    csv_text = "name,age\nAlice,30\nBob,25\n"
    data = convert_csv_text(io.StringIO(csv_text))
    assert data == [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
    ]


def test_convert_csv_text_empty_raises() -> None:
    with pytest.raises(ValueError):
        convert_csv_text(io.StringIO(""))
