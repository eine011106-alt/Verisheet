from __future__ import annotations

import io
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.differ import build_diff_summary
from src.llm_summary import create_llm_client_from_env, generate_change_summary
from src.loader import load_table, summarize_columns
from src.reporter import build_html_report, build_markdown_report
from src.utils import SUPPORTED_FILE_TYPES, format_file_size
from src.validator import validate_table


PAGE_TITLE = "Verisheet"
REPORT_TITLE = "通用表格智能校验与变更说明生成器"
BASE_DIR = Path(__file__).resolve().parent

SAMPLE_SCENARIOS = {
    "商品表": {
        "old_path": BASE_DIR / "samples" / "goods_old.csv",
        "new_path": BASE_DIR / "samples" / "goods_new.csv",
        "recommended_primary_key": "商品编号",
        "issues": [
            "缺失值：新表中“库存”存在空值",
            "数值异常：新表中“价格”包含明显异常值",
            "类型异常：新表中“库存”列混入非数字文本",
            "结构变化：包含新增行、删除行和修改行",
        ],
        "tips": "推荐先使用“商品编号”分析，再观察价格和库存相关问题。",
    },
    "人员名单": {
        "old_path": BASE_DIR / "samples" / "staff_old.csv",
        "new_path": BASE_DIR / "samples" / "staff_new.csv",
        "recommended_primary_key": "员工编号",
        "issues": [
            "缺失值：新表中“邮箱”存在空值",
            "类型异常：新表中“工龄”列混入文本值",
            "结构变化：包含新增人员、删除人员和字段修改",
            "重复主键演示：如将主键切换为“邮箱”，可体验重复主键问题",
        ],
        "tips": "推荐主键为“员工编号”；若想演示重复主键，可手动改选“邮箱”。",
    },
    "活动报名表": {
        "old_path": BASE_DIR / "samples" / "event_old.csv",
        "new_path": BASE_DIR / "samples" / "event_new.csv",
        "recommended_primary_key": "报名编号",
        "issues": [
            "缺失值：新表中“部门”存在空值",
            "数值异常：新表中“费用”包含高异常值",
            "结构变化：包含新增报名、删除报名和状态修改",
            "重复主键演示：如将主键切换为“联系方式”，可体验重复主键问题",
        ],
        "tips": "推荐主键为“报名编号”；若想观察重复主键告警，可手动改选“联系方式”。",
    },
}

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="📊",
    layout="wide",
)


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str) -> None:
        super().__init__(content)
        self.name = name


def apply_custom_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }
        h1 {
            font-size: 1.9rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.25rem !important;
        }
        h2 {
            font-size: 1.2rem !important;
            font-weight: 650 !important;
            margin-top: 0.5rem !important;
        }
        h3 {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
        }
        p, li, label, .stMarkdown, .stCaption {
            font-size: 0.95rem !important;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 12px;
            padding: 0.75rem 0.9rem;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
        }
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            width: auto !important;
            min-width: 7rem;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        div[data-testid="stForm"] {
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 12px;
            padding: 0.75rem 0.85rem 0.5rem 0.85rem;
            background: rgba(248, 250, 252, 0.6);
        }
        .summary-panel {
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            background: #ffffff;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    st.session_state.setdefault("loaded_data", None)
    st.session_state.setdefault("analysis_result", None)
    st.session_state.setdefault("ai_summary", None)
    st.session_state.setdefault("selected_primary_key", "")
    st.session_state.setdefault("timings", {})
    st.session_state.setdefault("sample_choice", list(SAMPLE_SCENARIOS.keys())[0])


@st.cache_data(show_spinner=False)
def cached_load_table(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    return load_table(NamedBytesIO(file_bytes, file_name))


@st.cache_resource
def cached_llm_client():
    return create_llm_client_from_env()


@st.cache_data(show_spinner=False)
def cached_generate_change_summary(
    old_validation: dict[str, Any],
    new_validation: dict[str, Any],
    diff_summary: dict[str, Any],
) -> str:
    return generate_change_summary(
        old_validation=old_validation,
        new_validation=new_validation,
        diff_summary=diff_summary,
        llm_client=cached_llm_client(),
    )


def dataframe_from_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame([{"提示": "无数据"}])
    return pd.DataFrame(records)


def build_file_info(file_name: str, file_size: int, dataframe: pd.DataFrame) -> dict[str, Any]:
    return {
        "文件名": file_name,
        "文件大小": format_file_size(file_size),
        "行数": int(len(dataframe)),
        "列数": int(len(dataframe.columns)),
    }


def render_file_info_card(title: str, file_info: dict[str, Any]) -> None:
    st.markdown(f"### {title}")
    st.dataframe(pd.DataFrame([file_info]), use_container_width=True, hide_index=True)


def render_timings() -> None:
    timings = st.session_state.get("timings", {})
    if not timings:
        return

    rows = [{"阶段": key, "耗时（秒）": round(value, 4)} for key, value in timings.items()]
    with st.expander("性能统计", expanded=False):
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def clear_analysis_state() -> None:
    st.session_state["analysis_result"] = None
    st.session_state["ai_summary"] = None
    st.session_state["selected_primary_key"] = ""


def recommend_primary_key(
    common_columns: list[str],
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    preferred: str | None = None,
) -> str:
    if preferred and preferred in common_columns:
        return preferred

    for column in common_columns:
        if old_df[column].is_unique and new_df[column].is_unique:
            return str(column)

    return common_columns[0] if common_columns else ""


def load_uploaded_files(old_file, new_file) -> None:
    if old_file is None or new_file is None:
        st.sidebar.error("请同时上传旧表和新表。")
        return

    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    with st.status("正在读取文件...", expanded=True) as status:
        try:
            old_bytes = old_file.getvalue()
            new_bytes = new_file.getvalue()

            step_start = time.perf_counter()
            old_df = cached_load_table(old_bytes, old_file.name)
            timings["加载旧表"] = time.perf_counter() - step_start
            status.write(f"旧表加载完成：{old_file.name}")

            step_start = time.perf_counter()
            new_df = cached_load_table(new_bytes, new_file.name)
            timings["加载新表"] = time.perf_counter() - step_start
            status.write(f"新表加载完成：{new_file.name}")
        except ValueError as exc:
            status.update(label="文件读取失败", state="error")
            st.sidebar.error(f"文件加载失败：{exc}")
            return

        status.update(label="文件读取完成", state="complete")

    common_columns = [str(column) for column in old_df.columns if column in new_df.columns]
    recommended_primary_key = recommend_primary_key(common_columns, old_df, new_df)
    timings["文件加载总耗时"] = time.perf_counter() - total_start

    st.session_state["loaded_data"] = {
        "source_type": "upload",
        "old_name": old_file.name,
        "new_name": new_file.name,
        "old_size": old_file.size,
        "new_size": new_file.size,
        "old_df": old_df,
        "new_df": new_df,
        "common_columns": common_columns,
        "recommended_primary_key": recommended_primary_key,
        "sample_issues": [],
        "sample_tips": "",
        "sample_title": "",
    }
    st.session_state["timings"] = timings
    clear_analysis_state()
    st.session_state["selected_primary_key"] = recommended_primary_key
    st.sidebar.success("文件已加载，可以选择主键并开始分析。")


def load_builtin_sample(sample_name: str) -> None:
    scenario = SAMPLE_SCENARIOS[sample_name]
    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    with st.status("正在加载内置示例...", expanded=True) as status:
        old_bytes = scenario["old_path"].read_bytes()
        new_bytes = scenario["new_path"].read_bytes()

        step_start = time.perf_counter()
        old_df = cached_load_table(old_bytes, scenario["old_path"].name)
        timings["加载示例旧表"] = time.perf_counter() - step_start
        status.write(f"已加载示例旧表：{scenario['old_path'].name}")

        step_start = time.perf_counter()
        new_df = cached_load_table(new_bytes, scenario["new_path"].name)
        timings["加载示例新表"] = time.perf_counter() - step_start
        status.write(f"已加载示例新表：{scenario['new_path'].name}")
        status.update(label="内置示例加载完成", state="complete")

    common_columns = [str(column) for column in old_df.columns if column in new_df.columns]
    recommended_primary_key = recommend_primary_key(
        common_columns,
        old_df,
        new_df,
        preferred=scenario["recommended_primary_key"],
    )
    timings["示例加载总耗时"] = time.perf_counter() - total_start

    st.session_state["loaded_data"] = {
        "source_type": "sample",
        "sample_name": sample_name,
        "sample_title": sample_name,
        "sample_issues": scenario["issues"],
        "sample_tips": scenario["tips"],
        "old_name": scenario["old_path"].name,
        "new_name": scenario["new_path"].name,
        "old_size": len(old_bytes),
        "new_size": len(new_bytes),
        "old_df": old_df,
        "new_df": new_df,
        "common_columns": common_columns,
        "recommended_primary_key": recommended_primary_key,
    }
    st.session_state["timings"] = timings
    clear_analysis_state()
    st.session_state["selected_primary_key"] = recommended_primary_key


def run_analysis(primary_key: str) -> None:
    loaded_data = st.session_state.get("loaded_data")
    if not loaded_data:
        st.error("请先加载旧表和新表。")
        return

    if not primary_key:
        st.error("请选择主键列后再开始分析。")
        return

    timings = dict(st.session_state.get("timings", {}))
    total_start = time.perf_counter()

    old_df = loaded_data["old_df"]
    new_df = loaded_data["new_df"]

    with st.status("正在执行分析...", expanded=True) as status:
        try:
            step_start = time.perf_counter()
            old_validation = validate_table(old_df, primary_key_column=primary_key)
            timings["校验旧表"] = time.perf_counter() - step_start
            status.write("旧表校验完成")

            step_start = time.perf_counter()
            new_validation = validate_table(new_df, primary_key_column=primary_key)
            timings["校验新表"] = time.perf_counter() - step_start
            status.write("新表校验完成")

            step_start = time.perf_counter()
            diff_summary = build_diff_summary(old_df, new_df, primary_key=primary_key)
            timings["执行 Diff"] = time.perf_counter() - step_start
            status.write("差异分析完成")
        except ValueError as exc:
            status.update(label="分析失败", state="error")
            st.error(f"分析失败：{exc}")
            return

        status.update(label="分析完成", state="complete")

    timings["分析总耗时"] = time.perf_counter() - total_start

    old_file_info = build_file_info(loaded_data["old_name"], loaded_data["old_size"], old_df)
    new_file_info = build_file_info(loaded_data["new_name"], loaded_data["new_size"], new_df)

    st.session_state["selected_primary_key"] = primary_key
    st.session_state["analysis_result"] = {
        "old_validation": old_validation,
        "new_validation": new_validation,
        "diff_summary": diff_summary,
        "old_file_info": old_file_info,
        "new_file_info": new_file_info,
    }
    st.session_state["ai_summary"] = None
    st.session_state["timings"] = timings


def generate_ai_summary() -> None:
    analysis_result = st.session_state.get("analysis_result")
    if not analysis_result:
        st.error("请先完成分析，再生成 AI 摘要。")
        return

    step_start = time.perf_counter()
    with st.status("正在生成摘要...", expanded=True) as status:
        status.write("正在准备结构化结果")
        ai_summary = cached_generate_change_summary(
            analysis_result["old_validation"],
            analysis_result["new_validation"],
            analysis_result["diff_summary"],
        )
        status.write("摘要生成完成")
        status.update(label="AI 摘要已生成", state="complete")

    timings = dict(st.session_state.get("timings", {}))
    timings["生成 AI 摘要"] = time.perf_counter() - step_start
    st.session_state["timings"] = timings
    st.session_state["ai_summary"] = ai_summary


def build_current_markdown_report() -> str | None:
    analysis_result = st.session_state.get("analysis_result")
    if not analysis_result:
        return None

    ai_summary = st.session_state.get("ai_summary") or "尚未生成 AI 变更说明，可在页面中点击“生成 AI 摘要”。"
    return build_markdown_report(
        old_validation=analysis_result["old_validation"],
        new_validation=analysis_result["new_validation"],
        diff_summary=analysis_result["diff_summary"],
        ai_summary=ai_summary,
        project_title=REPORT_TITLE,
        analysis_time=datetime.now(),
        old_file_info=analysis_result["old_file_info"],
        new_file_info=analysis_result["new_file_info"],
    )


def build_current_html_report() -> str | None:
    analysis_result = st.session_state.get("analysis_result")
    if not analysis_result:
        return None

    ai_summary = st.session_state.get("ai_summary") or "尚未生成 AI 变更说明，可在页面中点击“生成 AI 摘要”。"
    return build_html_report(
        old_validation=analysis_result["old_validation"],
        new_validation=analysis_result["new_validation"],
        diff_summary=analysis_result["diff_summary"],
        ai_summary=ai_summary,
        project_title=REPORT_TITLE,
        analysis_time=datetime.now(),
        old_file_info=analysis_result["old_file_info"],
        new_file_info=analysis_result["new_file_info"],
    )


def render_summary_metrics(analysis_result: dict[str, Any]) -> None:
    old_summary = analysis_result["old_validation"]["summary"]
    new_summary = analysis_result["new_validation"]["summary"]
    diff_summary = analysis_result["diff_summary"]
    diff_metrics = diff_summary["summary"]

    empty_issue_count = old_summary["columns_with_missing_values"] + new_summary["columns_with_missing_values"]
    duplicate_key_count = old_summary["duplicate_key_row_count"] + new_summary["duplicate_key_row_count"]

    metric_col_1, metric_col_2, metric_col_3, metric_col_4, metric_col_5 = st.columns(5)
    metric_col_1.metric("空值问题数", empty_issue_count)
    metric_col_2.metric("重复主键数", duplicate_key_count)
    metric_col_3.metric("新增行数", diff_metrics["added_row_count"])
    metric_col_4.metric("删除行数", diff_metrics["removed_row_count"])
    metric_col_5.metric("修改行数", diff_metrics["changed_row_count"])


def render_sample_description(loaded_data: dict[str, Any]) -> None:
    if loaded_data.get("source_type") != "sample":
        return

    st.markdown("## 示例说明")
    st.info(f"当前示例：{loaded_data.get('sample_title', '')}")
    issue_rows = [{"典型问题": item} for item in loaded_data.get("sample_issues", [])]
    st.dataframe(pd.DataFrame(issue_rows), use_container_width=True, hide_index=True)
    if loaded_data.get("sample_tips"):
        st.caption(loaded_data["sample_tips"])


def render_validation_tab(analysis_result: dict[str, Any]) -> None:
    col_1, col_2 = st.columns(2)
    with col_1:
        st.markdown("### 旧表基础信息")
        render_file_info_card("旧表文件", analysis_result["old_file_info"])
        st.markdown("### 旧表校验概览")
        st.json(analysis_result["old_validation"]["summary"])
    with col_2:
        st.markdown("### 新表基础信息")
        render_file_info_card("新表文件", analysis_result["new_file_info"])
        st.markdown("### 新表校验概览")
        st.json(analysis_result["new_validation"]["summary"])


def render_diff_overview(diff_summary: dict[str, Any]) -> None:
    summary = diff_summary["summary"]
    col_1, col_2, col_3, col_4 = st.columns(4)
    col_1.metric("新增行", summary["added_row_count"])
    col_2.metric("删除行", summary["removed_row_count"])
    col_3.metric("修改行", summary["changed_row_count"])
    col_4.metric("字段变更次数", diff_summary["changed_cell_count"])


def render_diff_tab(analysis_result: dict[str, Any]) -> None:
    diff_summary = analysis_result["diff_summary"]
    render_diff_overview(diff_summary)

    st.markdown("### 结构变化")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "新增列": ", ".join(diff_summary["added_columns"]) or "无",
                    "删除列": ", ".join(diff_summary["removed_columns"]) or "无",
                    "字段变更次数": diff_summary["changed_cell_count"],
                }
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 变更列汇总")
    st.dataframe(
        dataframe_from_records(diff_summary["changed_columns_summary"]),
        use_container_width=True,
        hide_index=True,
    )


def render_ai_tab() -> None:
    ai_summary = st.session_state.get("ai_summary")
    if ai_summary is None:
        st.info("AI 摘要默认按需生成，避免阻塞主分析流程。")
        if st.button("生成 AI 摘要"):
            generate_ai_summary()
            st.markdown(st.session_state["ai_summary"])
        return

    st.markdown(ai_summary)
    if st.button("重新生成 AI 摘要"):
        generate_ai_summary()
        st.markdown(st.session_state["ai_summary"])


def render_detail_tab(analysis_result: dict[str, Any]) -> None:
    st.caption("详细数据默认折叠，避免首屏直接渲染大表格。")

    with st.expander("查看缺失值明细", expanded=False):
        col_1, col_2 = st.columns(2)
        with col_1:
            st.markdown("#### 旧表缺失值")
            st.dataframe(
                dataframe_from_records(analysis_result["old_validation"]["missing_values"]),
                use_container_width=True,
                hide_index=True,
            )
        with col_2:
            st.markdown("#### 新表缺失值")
            st.dataframe(
                dataframe_from_records(analysis_result["new_validation"]["missing_values"]),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("查看重复主键明细", expanded=False):
        col_1, col_2 = st.columns(2)
        with col_1:
            st.markdown("#### 旧表重复主键")
            st.dataframe(
                dataframe_from_records(analysis_result["old_validation"]["duplicate_key_rows"]),
                use_container_width=True,
                hide_index=True,
            )
        with col_2:
            st.markdown("#### 新表重复主键")
            st.dataframe(
                dataframe_from_records(analysis_result["new_validation"]["duplicate_key_rows"]),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("查看新增与删除行", expanded=False):
        col_1, col_2 = st.columns(2)
        with col_1:
            st.markdown("#### 新增行")
            st.dataframe(
                dataframe_from_records(analysis_result["diff_summary"]["added_rows"]),
                use_container_width=True,
                hide_index=True,
            )
        with col_2:
            st.markdown("#### 删除行")
            st.dataframe(
                dataframe_from_records(analysis_result["diff_summary"]["removed_rows"]),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("查看字段变更明细", expanded=False):
        st.dataframe(
            dataframe_from_records(analysis_result["diff_summary"]["changed_rows"]),
            use_container_width=True,
            hide_index=True,
        )


init_session_state()
apply_custom_style()

st.title(PAGE_TITLE)
st.caption("标准化表格校验与差异分析工具。先完成文件加载与分析，再查看摘要、明细与导出结果。")

with st.sidebar:
    st.header("输入与配置")
    st.caption("请先上传两份表格，再选择主键列并执行分析。")
    use_builtin_sample = st.toggle("使用内置示例", value=False)

    if use_builtin_sample:
        sample_choice = st.selectbox(
            "示例场景",
            options=list(SAMPLE_SCENARIOS.keys()),
            key="sample_choice",
        )
        current_loaded = st.session_state.get("loaded_data")
        if (
            current_loaded is None
            or current_loaded.get("source_type") != "sample"
            or current_loaded.get("sample_name") != sample_choice
        ):
            load_builtin_sample(sample_choice)
        st.caption(f"推荐主键：{SAMPLE_SCENARIOS[sample_choice]['recommended_primary_key']}")
        st.caption("选择场景后已自动加载示例数据，无需上传文件。")
    else:
        with st.form("upload_form", clear_on_submit=False):
            old_file = st.file_uploader("旧版本文件", type=SUPPORTED_FILE_TYPES, accept_multiple_files=False)
            new_file = st.file_uploader("新版本文件", type=SUPPORTED_FILE_TYPES, accept_multiple_files=False)
            load_clicked = st.form_submit_button("加载文件")

        if load_clicked:
            load_uploaded_files(old_file, new_file)

    loaded_data = st.session_state.get("loaded_data")
    if loaded_data:
        st.markdown("### 当前文件")
        st.caption(f"旧表：{loaded_data['old_name']}")
        st.caption(f"新表：{loaded_data['new_name']}")

        with st.form("analysis_form", clear_on_submit=False):
            selected_primary_key = st.selectbox(
                "主键列",
                options=[""] + loaded_data["common_columns"],
                index=([""] + loaded_data["common_columns"]).index(st.session_state.get("selected_primary_key", ""))
                if st.session_state.get("selected_primary_key", "") in loaded_data["common_columns"]
                else 0,
                format_func=lambda value: "请选择" if value == "" else value,
            )
            analyze_clicked = st.form_submit_button("开始分析")

        if analyze_clicked:
            run_analysis(selected_primary_key)
    else:
        st.info("上传并加载文件后，这里会出现主键配置区。")

render_timings()

analysis_result = st.session_state.get("analysis_result")
loaded_data = st.session_state.get("loaded_data")

if loaded_data is None:
    st.info("请先在左侧上传旧表和新表。完成“加载文件”后，主区域将展示摘要与分析结果。")
    st.stop()

render_sample_description(loaded_data)

if analysis_result is None:
    top_col_1, top_col_2 = st.columns([1.2, 1])
    with top_col_1:
        st.markdown("## 当前数据准备情况")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "旧表文件": loaded_data["old_name"],
                        "新表文件": loaded_data["new_name"],
                        "共同列数": len(loaded_data["common_columns"]),
                    }
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("### 列信息预览")
        preview_col_1, preview_col_2 = st.columns(2)
        with preview_col_1:
            st.dataframe(
                dataframe_from_records(summarize_columns(loaded_data["old_df"])),
                use_container_width=True,
                hide_index=True,
            )
        with preview_col_2:
            st.dataframe(
                dataframe_from_records(summarize_columns(loaded_data["new_df"])),
                use_container_width=True,
                hide_index=True,
            )
    with top_col_2:
        st.markdown("## 使用引导")
        st.markdown(
            """
            1. 在左侧确认文件已加载完成  
            2. 选择主键列  
            3. 点击“开始分析”  
            4. 在主区域查看摘要结果与详细信息  
            """
        )
        if not loaded_data["common_columns"]:
            st.error("两份表格没有共同列，当前无法继续分析。")
        else:
            st.success("文件已准备完成，可以开始分析。")
    st.stop()

st.markdown("## 分析摘要")
render_summary_metrics(analysis_result)

tab_1, tab_2, tab_3, tab_4 = st.tabs(["校验概览", "差异分析", "AI 摘要", "明细数据"])

with tab_1:
    render_validation_tab(analysis_result)

with tab_2:
    render_diff_tab(analysis_result)

with tab_3:
    render_ai_tab()

with tab_4:
    render_detail_tab(analysis_result)

st.markdown("## 报告导出")
html_report = build_current_html_report()
st.download_button(
    label="下载 HTML 报告",
    data=html_report or "",
    file_name=f"table_checker_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
    mime="text/html",
)
