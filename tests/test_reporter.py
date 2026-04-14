from __future__ import annotations

from datetime import datetime

from src.reporter import build_html_report, build_markdown_report, save_html_report, save_markdown_report


def build_validation_result() -> dict:
    return {
        "summary": {
            "missing_value_cell_count": 2,
            "columns_with_missing_values": 1,
            "duplicate_key_row_count": 1,
            "outlier_column_count": 1,
            "suspected_type_issue_count": 1,
        },
        "missing_values": [{"column_name": "name", "missing_count": 2, "missing_ratio": 0.2}],
        "duplicate_key_rows": [{"row_index": 1, "primary_key_value": "A001"}],
    }


def build_diff_summary() -> dict:
    return {
        "row_delta": 1,
        "changed_cell_count": 3,
        "added_columns": ["remark"],
        "removed_columns": [],
        "added_rows": [{"primary_key_value": "A003", "row_data": {"name": "carol"}}],
        "removed_rows": [],
        "changed_rows": [
            {
                "primary_key": "id",
                "primary_key_value": "A002",
                "changes": [{"column_name": "amount", "old_value": 100, "new_value": 120}],
            }
        ],
        "changed_columns_summary": [
            {"column_name": "amount", "change_count": 1, "sample_primary_keys": ["A002"]}
        ],
        "summary": {
            "added_row_count": 1,
            "removed_row_count": 0,
            "changed_row_count": 1,
            "changed_column_count": 1,
        },
    }


def test_build_markdown_report_contains_required_sections() -> None:
    report = build_markdown_report(
        old_validation=build_validation_result(),
        new_validation=build_validation_result(),
        diff_summary=build_diff_summary(),
        ai_summary="这是 AI 变更说明。",
        analysis_time=datetime(2026, 4, 13, 12, 0, 0),
        old_file_info={"name": "old.xlsx", "size": "10 KB", "row_count": 10, "column_count": 3},
        new_file_info={"name": "new.xlsx", "size": "12 KB", "row_count": 11, "column_count": 4},
    )

    assert "# 通用表格智能校验与变更说明生成器" in report
    assert "## 文件信息" in report
    assert "## 校验结果摘要" in report
    assert "## Diff 摘要" in report
    assert "## 明细节选" in report
    assert "## AI 变更说明" in report
    assert "分析时间：2026-04-13 12:00:00" in report
    assert "旧表文件名：old.xlsx" in report
    assert "这是 AI 变更说明。" in report


def test_save_markdown_report_writes_file_with_timestamp(tmp_path) -> None:
    report_path = save_markdown_report(
        "# demo\n",
        output_dir=tmp_path,
        file_prefix="demo_report",
        timestamp=datetime(2026, 4, 13, 12, 30, 45),
    )

    assert report_path.name == "demo_report_20260413_123045.md"
    assert report_path.read_text(encoding="utf-8") == "# demo\n"


def test_build_html_report_contains_required_sections() -> None:
    report = build_html_report(
        old_validation=build_validation_result(),
        new_validation=build_validation_result(),
        diff_summary=build_diff_summary(),
        ai_summary="这是 AI 变更说明。",
        analysis_time=datetime(2026, 4, 13, 12, 0, 0),
        old_file_info={"name": "old.xlsx", "size": "10 KB", "row_count": 10, "column_count": 3},
        new_file_info={"name": "new.xlsx", "size": "12 KB", "row_count": 11, "column_count": 4},
    )

    assert "<!DOCTYPE html>" in report
    assert "通用表格智能校验与变更说明生成器" in report
    assert "分析时间：2026-04-13 12:00:00" in report
    assert "关键指标" in report
    assert "校验结果摘要" in report
    assert "Diff 摘要" in report
    assert "问题明细节选" in report
    assert "AI 摘要" in report
    assert "这是 AI 变更说明。" in report


def test_save_html_report_writes_file_with_timestamp(tmp_path) -> None:
    report_path = save_html_report(
        "<html></html>",
        output_dir=tmp_path,
        file_prefix="demo_report",
        timestamp=datetime(2026, 4, 13, 12, 30, 45),
    )

    assert report_path.name == "demo_report_20260413_123045.html"
    assert report_path.read_text(encoding="utf-8") == "<html></html>"
