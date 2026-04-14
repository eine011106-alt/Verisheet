from __future__ import annotations

import re
from typing import Any

import pandas as pd

NUMERIC_TEXT_PATTERN = re.compile(r"^[+-]?(\d+(\.\d+)?|\.\d+)$")


def validate_table(
    dataframe: pd.DataFrame,
    primary_key_column: str | None = None,
) -> dict[str, Any]:
    if primary_key_column and primary_key_column not in dataframe.columns:
        raise ValueError(f"主键列不存在：{primary_key_column}")

    missing_values = _build_missing_values(dataframe)
    duplicate_key_rows = _build_duplicate_key_rows(dataframe, primary_key_column)
    numeric_outlier_columns = _build_numeric_outlier_columns(dataframe)
    suspected_type_issues = _build_suspected_type_issues(dataframe)

    return {
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "primary_key": primary_key_column,
        "missing_values": missing_values,
        "duplicate_key_rows": duplicate_key_rows,
        "numeric_outlier_columns": numeric_outlier_columns,
        "suspected_type_issues": suspected_type_issues,
        "summary": {
            "missing_value_cell_count": int(dataframe.isna().sum().sum()),
            "columns_with_missing_values": len(missing_values),
            "duplicate_key_row_count": len(duplicate_key_rows),
            "outlier_column_count": len(numeric_outlier_columns),
            "suspected_type_issue_count": len(suspected_type_issues),
        },
    }


def _build_missing_values(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for column_name in dataframe.columns:
        missing_count = int(dataframe[column_name].isna().sum())
        if missing_count == 0:
            continue

        result.append(
            {
                "column_name": str(column_name),
                "missing_count": missing_count,
                "missing_ratio": round(missing_count / max(len(dataframe), 1), 4),
            }
        )

    return result


def _build_duplicate_key_rows(
    dataframe: pd.DataFrame,
    primary_key_column: str | None,
) -> list[dict[str, Any]]:
    if not primary_key_column:
        return []

    duplicate_mask = dataframe[primary_key_column].duplicated(keep=False)
    if not duplicate_mask.any():
        return []

    duplicate_rows = dataframe.loc[duplicate_mask, [primary_key_column]]
    result: list[dict[str, Any]] = []

    for row_index, row in duplicate_rows.iterrows():
        result.append(
            {
                "row_index": int(row_index),
                "primary_key_column": primary_key_column,
                "primary_key_value": _to_json_value(row[primary_key_column]),
            }
        )

    return result


def _build_numeric_outlier_columns(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    numeric_columns = dataframe.select_dtypes(include="number").columns
    for column_name in numeric_columns:
        series = dataframe[column_name].dropna()
        if len(series) < 4:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        if iqr > 0:
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            rule = "IQR"
        else:
            std = float(series.std())
            if std == 0:
                continue
            mean = float(series.mean())
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std
            rule = "3-sigma"

        outlier_mask = (dataframe[column_name] < lower_bound) | (dataframe[column_name] > upper_bound)
        outlier_rows = dataframe.loc[outlier_mask, column_name]
        if outlier_rows.empty:
            continue

        results.append(
            {
                "column_name": str(column_name),
                "rule": rule,
                "outlier_count": int(len(outlier_rows)),
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "sample_values": [_to_json_value(value) for value in outlier_rows.head(5).tolist()],
                "row_indices": [int(index) for index in outlier_rows.index[:5].tolist()],
            }
        )

    return results


def _build_suspected_type_issues(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for column_name in dataframe.columns:
        series = dataframe[column_name].dropna()
        if series.empty:
            continue

        python_types = {type(value).__name__ for value in series.tolist()}
        if len(python_types) > 1:
            results.append(
                {
                    "column_name": str(column_name),
                    "issue_type": "mixed_python_types",
                    "details": f"同一列中检测到多种 Python 类型：{', '.join(sorted(python_types))}",
                    "sample_values": [_to_json_value(value) for value in series.head(5).tolist()],
                }
            )
            continue

        if pd.api.types.is_object_dtype(dataframe[column_name]) or pd.api.types.is_string_dtype(dataframe[column_name]):
            string_values = series.astype(str).str.strip()
            numeric_mask = string_values.str.match(NUMERIC_TEXT_PATTERN)

            if numeric_mask.any() and (~numeric_mask).any():
                invalid_samples = string_values[~numeric_mask].head(5).tolist()
                results.append(
                    {
                        "column_name": str(column_name),
                        "issue_type": "mixed_numeric_and_text",
                        "details": "该列包含可转为数字的文本，也包含非数字内容，疑似类型不一致。",
                        "sample_values": [_to_json_value(value) for value in invalid_samples],
                    }
                )

    return results


def _to_json_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # pragma: no cover - defensive branch
            return str(value)

    return value
