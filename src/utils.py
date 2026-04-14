from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_FILE_TYPES = ["xlsx", "xls", "csv"]


def get_file_extension(file_name: str) -> str:
    return Path(file_name).suffix.lower().lstrip(".")


def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    return f"{size_in_bytes / (1024 * 1024):.1f} MB"


def normalize_value_for_display(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {str(key): normalize_value_for_display(item) for key, item in value.items()}
        return json.dumps(normalized, ensure_ascii=False)

    if isinstance(value, (list, tuple, set)):
        normalized = [normalize_value_for_display(item) for item in value]
        return json.dumps(normalized, ensure_ascii=False)

    return value


def normalize_records_for_display(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            str(key): normalize_value_for_display(value)
            for key, value in record.items()
        }
        for record in records
    ]
