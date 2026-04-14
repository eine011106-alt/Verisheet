from __future__ import annotations

from pathlib import Path

SUPPORTED_FILE_TYPES = ["xlsx", "xls", "csv"]


def get_file_extension(file_name: str) -> str:
    return Path(file_name).suffix.lower().lstrip(".")


def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    return f"{size_in_bytes / (1024 * 1024):.1f} MB"
