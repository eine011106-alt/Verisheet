from __future__ import annotations

from typing import Any

import pandas as pd


def build_diff_summary(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    primary_key: str | None = None,
) -> dict[str, Any]:
    key_column = primary_key or "__row_index__"
    old_prepared = _prepare_dataframe(old_df, primary_key)
    new_prepared = _prepare_dataframe(new_df, primary_key)

    _ensure_key_column_exists(old_prepared, key_column, "旧版本")
    _ensure_key_column_exists(new_prepared, key_column, "新版本")
    _ensure_key_is_unique(old_prepared, key_column, "旧版本")
    _ensure_key_is_unique(new_prepared, key_column, "新版本")

    old_keys = set(old_prepared[key_column].tolist())
    new_keys = set(new_prepared[key_column].tolist())
    common_keys = old_keys & new_keys

    added_key_list = [key for key in new_prepared[key_column].tolist() if key not in old_keys]
    removed_key_list = [key for key in old_prepared[key_column].tolist() if key not in new_keys]

    old_columns = [str(column) for column in old_prepared.columns if column != key_column]
    new_columns = [str(column) for column in new_prepared.columns if column != key_column]
    added_columns = [column for column in new_columns if column not in old_columns]
    removed_columns = [column for column in old_columns if column not in new_columns]
    common_columns = [column for column in old_columns if column in new_columns]

    old_indexed = old_prepared.set_index(key_column, drop=False)
    new_indexed = new_prepared.set_index(key_column, drop=False)

    changed_rows: list[dict[str, Any]] = []
    changed_column_counter: dict[str, int] = {}
    changed_column_keys: dict[str, list[Any]] = {}

    for key in _preserve_key_order(old_prepared[key_column].tolist(), common_keys):
        old_row = old_indexed.loc[key]
        new_row = new_indexed.loc[key]
        row_changes = _build_row_changes(old_row, new_row, common_columns)

        if not row_changes:
            continue

        changed_rows.append(
            {
                "primary_key": primary_key,
                "primary_key_value": _to_json_value(key),
                "changes": row_changes,
            }
        )

        for change in row_changes:
            column_name = change["column_name"]
            changed_column_counter[column_name] = changed_column_counter.get(column_name, 0) + 1
            changed_column_keys.setdefault(column_name, []).append(_to_json_value(key))

    changed_columns_summary = [
        {
            "column_name": column_name,
            "change_count": changed_column_counter[column_name],
            "sample_primary_keys": changed_column_keys[column_name][:5],
        }
        for column_name in common_columns
        if column_name in changed_column_counter
    ]

    changed_cell_count = sum(item["change_count"] for item in changed_columns_summary)
    added_rows = _build_row_records(new_indexed, added_key_list, key_column)
    removed_rows = _build_row_records(old_indexed, removed_key_list, key_column)

    return {
        "primary_key": primary_key,
        "old_row_count": int(len(old_df)),
        "new_row_count": int(len(new_df)),
        "row_delta": int(len(new_df) - len(old_df)),
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "added_rows": added_rows,
        "removed_rows": removed_rows,
        "changed_rows": changed_rows,
        "changed_columns_summary": changed_columns_summary,
        "changed_cell_count": int(changed_cell_count),
        "is_row_comparable": True,
        "summary": {
            "added_row_count": len(added_rows),
            "removed_row_count": len(removed_rows),
            "changed_row_count": len(changed_rows),
            "changed_column_count": len(changed_columns_summary),
        },
    }


def _prepare_dataframe(dataframe: pd.DataFrame, primary_key: str | None) -> pd.DataFrame:
    if primary_key:
        return dataframe.copy()

    prepared = dataframe.reset_index(drop=True).copy()
    prepared.insert(0, "__row_index__", prepared.index.astype(int))
    return prepared


def _ensure_key_column_exists(dataframe: pd.DataFrame, key_column: str, label: str) -> None:
    if key_column not in dataframe.columns:
        raise ValueError(f"{label}中不存在主键列：{key_column}")


def _ensure_key_is_unique(dataframe: pd.DataFrame, key_column: str, label: str) -> None:
    duplicate_mask = dataframe[key_column].duplicated(keep=False)
    if not duplicate_mask.any():
        return

    duplicated_values = dataframe.loc[duplicate_mask, key_column].head(5).tolist()
    raise ValueError(
        f"{label}中的主键列存在重复值，无法进行稳定对比：{', '.join(str(value) for value in duplicated_values)}"
    )


def _build_row_changes(
    old_row: pd.Series,
    new_row: pd.Series,
    comparable_columns: list[str],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for column_name in comparable_columns:
        old_value = old_row[column_name]
        new_value = new_row[column_name]
        if _values_equal(old_value, new_value):
            continue

        changes.append(
            {
                "column_name": column_name,
                "old_value": _to_json_value(old_value),
                "new_value": _to_json_value(new_value),
            }
        )

    return changes


def _build_row_records(
    dataframe: pd.DataFrame,
    key_list: list[Any],
    key_column: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for key in key_list:
        row = dataframe.loc[key]
        records.append(
            {
                "primary_key_value": _to_json_value(key),
                "row_data": {
                    str(column_name): _to_json_value(value)
                    for column_name, value in row.items()
                    if column_name != key_column
                },
            }
        )

    return records


def _preserve_key_order(keys_in_old_order: list[Any], common_keys: set[Any]) -> list[Any]:
    return [key for key in keys_in_old_order if key in common_keys]


def _values_equal(old_value: Any, new_value: Any) -> bool:
    if pd.isna(old_value) and pd.isna(new_value):
        return True
    return bool(old_value == new_value)


def _to_json_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # pragma: no cover - defensive branch
            return str(value)

    return value
