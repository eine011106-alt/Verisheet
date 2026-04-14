from __future__ import annotations

from src.utils import normalize_records_for_display, normalize_value_for_display


def test_normalize_value_for_display_serializes_nested_dict_and_list() -> None:
    value = {
        "row_data": {"name": "alice", "amount": 10},
        "changes": [
            {"column_name": "amount", "old_value": 10, "new_value": 12},
        ],
    }

    normalized = normalize_value_for_display(value)

    assert isinstance(normalized, str)
    assert '"row_data"' in normalized
    assert '"changes"' in normalized
    assert '"column_name": "amount"' in normalized


def test_normalize_records_for_display_keeps_scalar_values_and_serializes_nested_values() -> None:
    records = [
        {
            "primary_key": "id",
            "primary_key_value": 1001,
            "changes": [
                {"column_name": "status", "old_value": "A", "new_value": "B"},
            ],
        }
    ]

    normalized = normalize_records_for_display(records)

    assert normalized == [
        {
            "primary_key": "id",
            "primary_key_value": 1001,
            "changes": '[{"column_name": "status", "old_value": "A", "new_value": "B"}]',
        }
    ]
