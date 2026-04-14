from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_TITLE = "通用表格智能校验与变更说明生成器"


def build_markdown_report(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any] | None,
    ai_summary: str,
    *,
    project_title: str = DEFAULT_PROJECT_TITLE,
    analysis_time: datetime | None = None,
    old_file_info: dict[str, Any] | None = None,
    new_file_info: dict[str, Any] | None = None,
    detail_limit: int = 5,
) -> str:
    analysis_time = analysis_time or datetime.now()
    lines = [
        f"# {project_title}",
        "",
        f"- 分析时间：{analysis_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 文件信息",
    ]

    lines.extend(_build_file_info_lines("旧表", old_file_info))
    lines.extend(_build_file_info_lines("新表", new_file_info))

    lines.extend(["", "## 校验结果摘要"])
    lines.extend(_build_validation_lines("旧表", old_validation))
    lines.extend(_build_validation_lines("新表", new_validation))

    lines.extend(["", "## Diff 摘要"])
    lines.extend(_build_diff_lines(diff_summary))

    lines.extend(["", "## 明细节选"])
    lines.extend(_build_detail_excerpt_lines(old_validation, new_validation, diff_summary, detail_limit))

    lines.extend(["", "## AI 变更说明", ai_summary.strip() or "未生成 AI 摘要。"])
    return "\n".join(lines).strip() + "\n"


def build_html_report(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any] | None,
    ai_summary: str,
    *,
    project_title: str = DEFAULT_PROJECT_TITLE,
    analysis_time: datetime | None = None,
    old_file_info: dict[str, Any] | None = None,
    new_file_info: dict[str, Any] | None = None,
    detail_limit: int = 5,
) -> str:
    analysis_time = analysis_time or datetime.now()
    old_summary = (old_validation or {}).get("summary", {})
    new_summary = (new_validation or {}).get("summary", {})
    diff_metrics = (diff_summary or {}).get("summary", {})

    metric_cards = [
        ("旧表空值单元格", old_summary.get("missing_value_cell_count", 0)),
        ("新表空值单元格", new_summary.get("missing_value_cell_count", 0)),
        ("重复主键行", old_summary.get("duplicate_key_row_count", 0) + new_summary.get("duplicate_key_row_count", 0)),
        ("新增行数", diff_metrics.get("added_row_count", 0)),
        ("删除行数", diff_metrics.get("removed_row_count", 0)),
        ("修改行数", diff_metrics.get("changed_row_count", 0)),
    ]

    detail_sections = [
        ("旧表缺失值节选", (old_validation or {}).get("missing_values", [])),
        ("新表缺失值节选", (new_validation or {}).get("missing_values", [])),
        ("旧表重复主键节选", (old_validation or {}).get("duplicate_key_rows", [])),
        ("新表重复主键节选", (new_validation or {}).get("duplicate_key_rows", [])),
        ("新增行节选", (diff_summary or {}).get("added_rows", [])),
        ("删除行节选", (diff_summary or {}).get("removed_rows", [])),
        ("变更行节选", (diff_summary or {}).get("changed_rows", [])),
    ]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(project_title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f5f7fa;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.6;
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    .header {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      padding: 24px 28px;
      margin-bottom: 20px;
    }}
    .header h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .muted {{
      color: #6b7280;
      font-size: 14px;
    }}
    .section {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      padding: 20px 24px;
      margin-bottom: 18px;
    }}
    .section h2 {{
      margin: 0 0 16px;
      font-size: 20px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .metric-card {{
      border: 1px solid #dbe2ea;
      border-radius: 12px;
      padding: 14px 16px;
      background: #f8fafc;
    }}
    .metric-card .label {{
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 6px;
    }}
    .metric-card .value {{
      font-size: 24px;
      font-weight: 700;
      color: #111827;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f8fafc;
      color: #374151;
      font-weight: 600;
    }}
    .empty {{
      padding: 12px 14px;
      border: 1px dashed #d1d5db;
      border-radius: 10px;
      background: #fafafa;
      color: #6b7280;
    }}
    .detail-block {{
      margin-bottom: 16px;
    }}
    .detail-block h3 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .ai-box {{
      white-space: pre-wrap;
      background: #f8fafc;
      border: 1px solid #dbe2ea;
      border-radius: 12px;
      padding: 16px;
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>{escape(project_title)}</h1>
      <div class="muted">分析时间：{escape(analysis_time.strftime("%Y-%m-%d %H:%M:%S"))}</div>
    </div>

    <div class="section">
      <h2>文件信息</h2>
      <div class="grid">
        {_build_file_info_html("旧表", old_file_info)}
        {_build_file_info_html("新表", new_file_info)}
      </div>
    </div>

    <div class="section">
      <h2>关键指标</h2>
      <div class="metrics">
        {''.join(_build_metric_card_html(label, value) for label, value in metric_cards)}
      </div>
    </div>

    <div class="section">
      <h2>校验结果摘要</h2>
      <div class="grid">
        {_build_key_value_table_html("旧表校验摘要", _build_validation_pairs("旧表", old_validation))}
        {_build_key_value_table_html("新表校验摘要", _build_validation_pairs("新表", new_validation))}
      </div>
    </div>

    <div class="section">
      <h2>Diff 摘要</h2>
      {_build_key_value_table_html("差异概览", _build_diff_pairs(diff_summary))}
    </div>

    <div class="section">
      <h2>问题明细节选</h2>
      {''.join(_build_detail_block_html(title, records, detail_limit) for title, records in detail_sections)}
    </div>

    <div class="section">
      <h2>AI 摘要</h2>
      <div class="ai-box">{escape(ai_summary.strip() or "未生成 AI 摘要。")}</div>
    </div>
  </div>
</body>
</html>
"""
    return html


def save_markdown_report(
    markdown_content: str,
    *,
    output_dir: str | Path = "outputs",
    file_prefix: str = "table_checker_report",
    timestamp: datetime | None = None,
) -> Path:
    timestamp = timestamp or datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{file_prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(markdown_content, encoding="utf-8")
    return report_path


def save_html_report(
    html_content: str,
    *,
    output_dir: str | Path = "outputs",
    file_prefix: str = "table_checker_report",
    timestamp: datetime | None = None,
) -> Path:
    timestamp = timestamp or datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{file_prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.html"
    report_path.write_text(html_content, encoding="utf-8")
    return report_path


def _build_file_info_lines(label: str, file_info: dict[str, Any] | None) -> list[str]:
    normalized = _normalize_file_info(file_info)
    if not normalized:
        return [f"- {label}：未提供文件信息"]
    return [
        f"- {label}文件名：{normalized['name']}",
        f"- {label}文件大小：{normalized['size']}",
        f"- {label}行数：{normalized['row_count']}",
        f"- {label}列数：{normalized['column_count']}",
    ]


def _build_validation_lines(label: str, validation_result: dict[str, Any] | None) -> list[str]:
    return [f"- {item[0]}：{item[1]}" for item in _build_validation_pairs(label, validation_result)]


def _build_diff_lines(diff_summary: dict[str, Any] | None) -> list[str]:
    return [f"- {item[0]}：{item[1]}" for item in _build_diff_pairs(diff_summary)]


def _build_validation_pairs(label: str, validation_result: dict[str, Any] | None) -> list[tuple[str, Any]]:
    if not validation_result:
        return [(label, "未执行校验")]

    summary = validation_result.get("summary", {})
    return [
        (f"{label}缺失值单元格", summary.get("missing_value_cell_count", 0)),
        (f"{label}存在缺失值的列数", summary.get("columns_with_missing_values", 0)),
        (f"{label}重复主键行数", summary.get("duplicate_key_row_count", 0)),
        (f"{label}异常数值列数", summary.get("outlier_column_count", 0)),
        (f"{label}疑似类型问题数", summary.get("suspected_type_issue_count", 0)),
    ]


def _build_diff_pairs(diff_summary: dict[str, Any] | None) -> list[tuple[str, Any]]:
    if not diff_summary:
        return [("差异分析", "未执行")]

    summary = diff_summary.get("summary", {})
    return [
        ("行数变化", diff_summary.get("row_delta", 0)),
        ("新增行数", summary.get("added_row_count", 0)),
        ("删除行数", summary.get("removed_row_count", 0)),
        ("变更行数", summary.get("changed_row_count", 0)),
        ("字段变更次数", diff_summary.get("changed_cell_count", 0)),
        ("新增列", ", ".join(diff_summary.get("added_columns", [])) or "无"),
        ("删除列", ", ".join(diff_summary.get("removed_columns", [])) or "无"),
    ]


def _build_detail_excerpt_lines(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any] | None,
    detail_limit: int,
) -> list[str]:
    lines: list[str] = []
    lines.extend(_format_record_excerpt("旧表缺失值节选", (old_validation or {}).get("missing_values", []), detail_limit))
    lines.extend(_format_record_excerpt("新表缺失值节选", (new_validation or {}).get("missing_values", []), detail_limit))
    lines.extend(_format_record_excerpt("旧表重复主键节选", (old_validation or {}).get("duplicate_key_rows", []), detail_limit))
    lines.extend(_format_record_excerpt("新表重复主键节选", (new_validation or {}).get("duplicate_key_rows", []), detail_limit))
    lines.extend(_format_record_excerpt("新增行节选", (diff_summary or {}).get("added_rows", []), detail_limit))
    lines.extend(_format_record_excerpt("删除行节选", (diff_summary or {}).get("removed_rows", []), detail_limit))
    lines.extend(_format_record_excerpt("变更行节选", (diff_summary or {}).get("changed_rows", []), detail_limit))
    lines.extend(_format_record_excerpt("变更列汇总节选", (diff_summary or {}).get("changed_columns_summary", []), detail_limit))
    return lines or ["- 无可展示的明细节选"]


def _format_record_excerpt(title: str, records: list[dict[str, Any]], detail_limit: int) -> list[str]:
    if not records:
        return [f"- {title}：无"]

    lines = [f"- {title}："]
    for record in records[:detail_limit]:
        lines.append(f"  - {record}")
    return lines


def _normalize_file_info(file_info: dict[str, Any] | None) -> dict[str, Any] | None:
    if not file_info:
        return None

    return {
        "name": file_info.get("name", file_info.get("文件名", "未知")),
        "size": file_info.get("size", file_info.get("文件大小", "未知")),
        "row_count": file_info.get("row_count", file_info.get("行数", "未知")),
        "column_count": file_info.get("column_count", file_info.get("列数", "未知")),
    }


def _build_file_info_html(title: str, file_info: dict[str, Any] | None) -> str:
    normalized = _normalize_file_info(file_info)
    if not normalized:
        return f'<div class="empty">{escape(title)}：未提供文件信息</div>'

    rows = [
        ("文件名", normalized["name"]),
        ("文件大小", normalized["size"]),
        ("行数", normalized["row_count"]),
        ("列数", normalized["column_count"]),
    ]
    return _build_key_value_table_html(title, rows)


def _build_metric_card_html(label: str, value: Any) -> str:
    return (
        '<div class="metric-card">'
        f'<div class="label">{escape(str(label))}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


def _build_key_value_table_html(title: str, rows: list[tuple[str, Any]]) -> str:
    if not rows:
        return f'<div class="empty">{escape(title)}：无数据</div>'

    table_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in rows
    )
    return (
        f"<div><div class=\"muted\" style=\"margin-bottom:8px;\">{escape(title)}</div>"
        f"<table>{table_rows}</table></div>"
    )


def _build_detail_block_html(title: str, records: list[dict[str, Any]], detail_limit: int) -> str:
    if not records:
        return f'<div class="detail-block"><h3>{escape(title)}</h3><div class="empty">无数据</div></div>'

    rows = records[:detail_limit]
    columns = sorted({key for row in rows for key in row.keys()})
    head = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_format_cell_html(row.get(column))}</td>" for column in columns)
        + "</tr>"
        for row in rows
    )
    return f'<div class="detail-block"><h3>{escape(title)}</h3><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _format_cell_html(value: Any) -> str:
    if isinstance(value, dict):
        return escape(", ".join(f"{k}: {v}" for k, v in value.items()) or "无")
    if isinstance(value, list):
        return escape(", ".join(str(item) for item in value) or "无")
    if value in (None, "", []):
        return "无"
    return escape(str(value))
