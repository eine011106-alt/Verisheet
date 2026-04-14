from __future__ import annotations

import pandas as pd
import pytest

from src.differ import build_diff_summary


def test_build_diff_summary_reports_added_removed_and_changed_rows() -> None:
    old_df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["alice", "bob", "carol"],
            "amount": [100, 200, 300],
            "status": ["A", "A", "B"],
        }
    )
    new_df = pd.DataFrame(
        {
            "id": [1, 2, 4],
            "name": ["alice", "bob", "david"],
            "amount": [100, 250, 80],
            "status": ["A", "B", "A"],
        }
    )

    summary = build_diff_summary(old_df, new_df, primary_key="id")

    assert summary["added_rows"] == [
        {
            "primary_key_value": 4,
            "row_data": {"name": "david", "amount": 80, "status": "A"},
        }
    ]
    assert summary["removed_rows"] == [
        {
            "primary_key_value": 3,
            "row_data": {"name": "carol", "amount": 300, "status": "B"},
        }
    ]
    assert summary["changed_rows"] == [
        {
            "primary_key": "id",
            "primary_key_value": 2,
            "changes": [
                {"column_name": "amount", "old_value": 200, "new_value": 250},
                {"column_name": "status", "old_value": "A", "new_value": "B"},
            ],
        }
    ]


def test_build_diff_summary_reports_changed_columns_summary() -> None:
    old_df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["alice", "bob", "carol"],
            "amount": [100, 200, 300],
        }
    )
    new_df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["alice", "tom", "carol"],
            "amount": [110, 200, 330],
        }
    )

    summary = build_diff_summary(old_df, new_df, primary_key="id")

    assert summary["changed_columns_summary"] == [
        {
            "column_name": "name",
            "change_count": 1,
            "sample_primary_keys": [2],
        },
        {
            "column_name": "amount",
            "change_count": 2,
            "sample_primary_keys": [1, 3],
        },
    ]
    assert summary["changed_cell_count"] == 3
    assert summary["summary"]["changed_row_count"] == 3


def test_build_diff_summary_reports_added_and_removed_columns() -> None:
    old_df = pd.DataFrame({"id": [1], "name": ["alice"], "old_flag": ["Y"]})
    new_df = pd.DataFrame({"id": [1], "name": ["alice"], "new_flag": ["N"]})

    summary = build_diff_summary(old_df, new_df, primary_key="id")

    assert summary["added_columns"] == ["new_flag"]
    assert summary["removed_columns"] == ["old_flag"]


def test_build_diff_summary_serializes_missing_values_as_none() -> None:
    old_df = pd.DataFrame({"id": [1], "name": [None], "amount": [10]})
    new_df = pd.DataFrame({"id": [1], "name": ["alice"], "amount": [10]})

    summary = build_diff_summary(old_df, new_df, primary_key="id")

    assert summary["changed_rows"] == [
        {
            "primary_key": "id",
            "primary_key_value": 1,
            "changes": [
                {"column_name": "name", "old_value": None, "new_value": "alice"},
            ],
        }
    ]


def test_build_diff_summary_raises_when_primary_key_is_missing() -> None:
    old_df = pd.DataFrame({"id": [1], "name": ["alice"]})
    new_df = pd.DataFrame({"code": [1], "name": ["alice"]})

    with pytest.raises(ValueError, match="主键列"):
        build_diff_summary(old_df, new_df, primary_key="id")


def test_build_diff_summary_raises_when_primary_key_has_duplicates() -> None:
    old_df = pd.DataFrame({"id": [1, 1], "name": ["alice", "bob"]})
    new_df = pd.DataFrame({"id": [1, 2], "name": ["alice", "tom"]})

    with pytest.raises(ValueError, match="重复值"):
        build_diff_summary(old_df, new_df, primary_key="id")
