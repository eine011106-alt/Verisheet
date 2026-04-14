from __future__ import annotations

import io

import pandas as pd
import pytest

from src.loader import load_table, summarize_columns
from src.utils import get_file_extension


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str) -> None:
        super().__init__(content)
        self.name = name


def build_excel_file() -> NamedBytesIO:
    buffer = io.BytesIO()
    dataframe = pd.DataFrame({"name": ["alice", "bob"], "score": [90, 88]})
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return NamedBytesIO(buffer.getvalue(), "demo.xlsx")


def test_get_file_extension_returns_lowercase_suffix() -> None:
    assert get_file_extension("demo.CSV") == "csv"


def test_load_table_reads_csv_file() -> None:
    file_obj = NamedBytesIO("name,age\nalice,18\nbob,20\n".encode("utf-8"), "demo.csv")

    dataframe = load_table(file_obj)

    assert list(dataframe.columns) == ["name", "age"]
    assert len(dataframe) == 2


def test_load_table_reads_excel_file() -> None:
    dataframe = load_table(build_excel_file())

    assert list(dataframe.columns) == ["name", "score"]
    assert dataframe.iloc[1]["name"] == "bob"


def test_load_table_raises_friendly_error_for_empty_file() -> None:
    file_obj = NamedBytesIO(b"", "empty.csv")

    with pytest.raises(ValueError, match="文件为空"):
        load_table(file_obj)


def test_load_table_raises_friendly_error_for_invalid_excel_file() -> None:
    file_obj = NamedBytesIO(b"not-an-excel-file", "broken.xlsx")

    with pytest.raises(ValueError, match="Excel 文件"):
        load_table(file_obj)


def test_load_table_raises_friendly_error_for_encoding_error(monkeypatch: pytest.MonkeyPatch) -> None:
    file_obj = NamedBytesIO("name\nalice\n".encode("utf-8"), "demo.csv")

    def fake_read_csv(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)

    with pytest.raises(ValueError, match="编码无法识别"):
        load_table(file_obj)


def test_summarize_columns_returns_basic_column_stats() -> None:
    dataframe = pd.DataFrame(
        {
            "name": ["alice", None],
            "score": [95, 88],
        }
    )

    summary = summarize_columns(dataframe)

    assert summary == [
        {"column_name": "name", "dtype": "object", "missing_count": 1},
        {"column_name": "score", "dtype": "int64", "missing_count": 0},
    ]
