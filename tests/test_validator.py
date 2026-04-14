from __future__ import annotations

import pandas as pd
import pytest

from src.validator import validate_table


def test_validate_table_returns_structured_result() -> None:
    dataframe = pd.DataFrame(
        {
            "id": [1, 1, 2, 3, 4],
            "name": ["alice", None, "bob", "charlie", "david"],
            "amount": [10, 12, 11, 9, 1000],
            "mixed_text": ["100", "200", "bad", "300", "400"],
        }
    )

    result = validate_table(dataframe, primary_key_column="id")

    assert result["row_count"] == 5
    assert result["column_count"] == 4
    assert result["primary_key"] == "id"
    assert result["summary"]["duplicate_key_row_count"] == 2
    assert result["summary"]["columns_with_missing_values"] == 1
    assert result["summary"]["outlier_column_count"] == 1
    assert result["summary"]["suspected_type_issue_count"] == 1


def test_validate_table_reports_missing_values() -> None:
    dataframe = pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["alice", None],
        }
    )

    result = validate_table(dataframe, primary_key_column="id")

    assert result["missing_values"] == [
        {
            "column_name": "name",
            "missing_count": 1,
            "missing_ratio": 0.5,
        }
    ]


def test_validate_table_reports_duplicate_key_rows() -> None:
    dataframe = pd.DataFrame(
        {
            "id": ["A001", "A001", "A002"],
            "amount": [10, 20, 30],
        }
    )

    result = validate_table(dataframe, primary_key_column="id")

    assert result["duplicate_key_rows"] == [
        {
            "row_index": 0,
            "primary_key_column": "id",
            "primary_key_value": "A001",
        },
        {
            "row_index": 1,
            "primary_key_column": "id",
            "primary_key_value": "A001",
        },
    ]


def test_validate_table_reports_numeric_outlier_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "amount": [10, 11, 9, 12, 1000],
        }
    )

    result = validate_table(dataframe, primary_key_column="id")

    assert result["numeric_outlier_columns"] == [
        {
            "column_name": "amount",
            "rule": "IQR",
            "outlier_count": 1,
            "lower_bound": 7.0,
            "upper_bound": 15.0,
            "sample_values": [1000],
            "row_indices": [4],
        }
    ]


def test_validate_table_reports_suspected_type_issues() -> None:
    dataframe = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "value": ["10", "20", "bad", "30"],
        }
    )

    result = validate_table(dataframe, primary_key_column="id")

    assert result["suspected_type_issues"] == [
        {
            "column_name": "value",
            "issue_type": "mixed_numeric_and_text",
            "details": "该列包含可转为数字的文本，也包含非数字内容，疑似类型不一致。",
            "sample_values": ["bad"],
        }
    ]


def test_validate_table_raises_when_primary_key_is_missing() -> None:
    dataframe = pd.DataFrame({"name": ["alice", "bob"]})

    with pytest.raises(ValueError, match="主键列不存在"):
        validate_table(dataframe, primary_key_column="id")
