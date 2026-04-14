from __future__ import annotations

import io
from typing import Any, BinaryIO
from zipfile import BadZipFile

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from src.utils import SUPPORTED_FILE_TYPES, get_file_extension

CSV_EXTENSIONS = {"csv"}
EXCEL_EXTENSIONS = {"xlsx", "xls"}
XLSX_SIGNATURE = b"PK\x03\x04"
XLS_SIGNATURE = b"\xD0\xCF\x11\xE0"
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")


def load_table(file: BinaryIO) -> pd.DataFrame:
    file_name = getattr(file, "name", "")
    raw_bytes = _read_file_bytes(file)

    if not raw_bytes.strip():
        raise ValueError("文件为空，请上传包含表头和数据的 CSV 或 Excel 文件。")

    file_type = _detect_file_type(file_name, raw_bytes)

    if file_type == "csv":
        dataframe = _load_csv_from_bytes(raw_bytes)
    else:
        dataframe = _load_excel_from_bytes(raw_bytes, file_name)

    if len(dataframe.columns) == 0:
        raise ValueError("文件中未识别到有效列，请检查表头是否完整。")

    _reset_file_pointer(file)
    return dataframe


def summarize_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "column_name": str(column_name),
            "dtype": str(df[column_name].dtype),
            "missing_count": int(df[column_name].isna().sum()),
        }
        for column_name in df.columns
    ]


def _read_file_bytes(file: BinaryIO) -> bytes:
    try:
        _reset_file_pointer(file)
        content = file.read()
    except Exception as exc:  # pragma: no cover - defensive branch
        raise ValueError("文件读取失败，请重新上传后再试。") from exc

    if isinstance(content, str):
        content = content.encode("utf-8")

    if not isinstance(content, bytes):
        raise ValueError("无法读取上传文件内容，请确认文件格式正确。")

    return content


def _detect_file_type(file_name: str, raw_bytes: bytes) -> str:
    extension = get_file_extension(file_name)

    if extension in CSV_EXTENSIONS:
        return "csv"
    if extension in EXCEL_EXTENSIONS:
        return "excel"
    if extension and extension not in SUPPORTED_FILE_TYPES:
        raise ValueError(f"暂不支持的文件类型：{extension}")

    if raw_bytes.startswith(XLSX_SIGNATURE) or raw_bytes.startswith(XLS_SIGNATURE):
        return "excel"
    if b"\x00" in raw_bytes[:1024]:
        raise ValueError("文件内容不是可识别的 CSV 或 Excel 格式，请检查上传文件。")

    return "csv"


def _load_csv_from_bytes(raw_bytes: bytes) -> pd.DataFrame:
    last_unicode_error: UnicodeError | None = None

    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_unicode_error = exc
        except EmptyDataError as exc:
            raise ValueError("CSV 文件为空，请检查文件是否包含表头和数据。") from exc
        except ParserError as exc:
            raise ValueError("CSV 文件格式不正确，请检查分隔符、引号或内容是否损坏。") from exc

    if last_unicode_error is not None:
        raise ValueError("CSV 文件编码无法识别，请尝试转为 UTF-8 编码后再上传。") from last_unicode_error

    raise ValueError("CSV 文件读取失败，请检查文件内容是否完整。")


def _load_excel_from_bytes(raw_bytes: bytes, file_name: str) -> pd.DataFrame:
    extension = get_file_extension(file_name)
    engine: str | None = None

    if extension == "xlsx" or (not extension and raw_bytes.startswith(XLSX_SIGNATURE)):
        engine = "openpyxl"
    elif extension == "xls" or (not extension and raw_bytes.startswith(XLS_SIGNATURE)):
        engine = "xlrd"

    try:
        return pd.read_excel(io.BytesIO(raw_bytes), engine=engine)
    except ValueError as exc:
        raise ValueError("Excel 文件格式无法识别，请确认上传的是有效的 xls 或 xlsx 文件。") from exc
    except BadZipFile as exc:
        raise ValueError("Excel 文件已损坏或内容不完整，请检查文件后重新上传。") from exc
    except Exception as exc:
        raise ValueError("Excel 文件读取失败，请确认文件内容有效且未损坏。") from exc


def _reset_file_pointer(file: BinaryIO) -> None:
    if hasattr(file, "seek"):
        file.seek(0)
