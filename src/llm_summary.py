from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

import streamlit as st


class LLMClient(Protocol):
    def generate_text(self, prompt: str) -> str: ...


@dataclass
class OpenAICompatibleLLMClient:
    api_key: str
    api_url: str
    model: str
    timeout_seconds: int = 30

    def generate_text(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个表格变更分析助手，请输出简洁、专业、适合业务协作的中文摘要。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,
        }

        req = request.Request(
            url=self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError("LLM 服务调用失败。") from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM 服务返回格式不符合预期。") from exc


def generate_change_summary(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any],
    llm_client: LLMClient | None = None,
) -> str:
    prompt = _build_prompt(old_validation, new_validation, diff_summary)
    client = llm_client or create_llm_client_from_env()

    if client is not None:
        try:
            return client.generate_text(prompt)
        except ValueError:
            pass

    return _build_local_template_summary(old_validation, new_validation, diff_summary)


def generate_change_report(diff_summary: dict[str, Any]) -> str:
    return generate_change_summary(
        old_validation=None,
        new_validation=None,
        diff_summary=diff_summary,
    )


def create_llm_client_from_env() -> LLMClient | None:
    api_key = _get_runtime_config("LLM_API_KEY", "OPENAI_API_KEY")
    api_url = _get_runtime_config("LLM_API_URL", "OPENAI_API_URL")
    model = _get_runtime_config("LLM_MODEL", "OPENAI_MODEL")

    if not api_key or not api_url or not model:
        return None

    timeout = int(_get_runtime_config("LLM_TIMEOUT_SECONDS", default="30"))
    return OpenAICompatibleLLMClient(
        api_key=api_key,
        api_url=api_url,
        model=model,
        timeout_seconds=timeout,
    )


def _get_runtime_config(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        env_value = os.getenv(key)
        if env_value:
            return env_value

    try:
        secrets = st.secrets
    except Exception:
        secrets = {}

    for key in keys:
        value = secrets.get(key)
        if value:
            return str(value)

    return default


def _build_prompt(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any],
) -> str:
    prompt_payload = {
        "old_validation": old_validation,
        "new_validation": new_validation,
        "diff_summary": diff_summary,
    }

    return "\n".join(
        [
            "请根据以下结构化结果生成中文自然语言摘要。",
            "输出必须包含以下四部分，并使用对应标题：",
            "1. 本次变更概览",
            "2. 主要风险提示",
            "3. 建议关注项",
            "4. 适合同事同步的更新说明",
            "语言要求：简洁、专业、适合业务协作，不要编造结构化结果中没有的信息。",
            json.dumps(prompt_payload, ensure_ascii=False, indent=2),
        ]
    )


def _build_local_template_summary(
    old_validation: dict[str, Any] | None,
    new_validation: dict[str, Any] | None,
    diff_summary: dict[str, Any],
) -> str:
    old_summary = (old_validation or {}).get("summary", {})
    new_summary = (new_validation or {}).get("summary", {})
    diff_metrics = diff_summary.get("summary", {})

    overview_lines = [
        f"本次共识别新增行 {diff_metrics.get('added_row_count', 0)} 条，删除行 {diff_metrics.get('removed_row_count', 0)} 条，变更行 {diff_metrics.get('changed_row_count', 0)} 条。",
        f"涉及字段变更 {diff_summary.get('changed_cell_count', 0)} 处，新增列 {len(diff_summary.get('added_columns', []))} 个，删除列 {len(diff_summary.get('removed_columns', []))} 个。",
    ]

    risk_lines = _build_risk_lines(old_summary, new_summary, diff_summary)
    suggestion_lines = _build_suggestion_lines(old_summary, new_summary, diff_summary)
    teammate_message = _build_teammate_message(diff_metrics, diff_summary, old_summary, new_summary)

    return "\n\n".join(
        [
            "本次变更概览\n" + "\n".join(f"- {line}" for line in overview_lines),
            "主要风险提示\n" + "\n".join(f"- {line}" for line in risk_lines),
            "建议关注项\n" + "\n".join(f"- {line}" for line in suggestion_lines),
            "适合同事同步的更新说明\n" + teammate_message,
        ]
    )


def _build_risk_lines(
    old_summary: dict[str, Any],
    new_summary: dict[str, Any],
    diff_summary: dict[str, Any],
) -> list[str]:
    risks: list[str] = []

    if old_summary.get("duplicate_key_row_count", 0) or new_summary.get("duplicate_key_row_count", 0):
        risks.append("存在重复主键行，后续比对、汇总或入库时可能出现覆盖或统计偏差。")

    if old_summary.get("missing_value_cell_count", 0) or new_summary.get("missing_value_cell_count", 0):
        risks.append("表中存在缺失值，关键字段可能影响业务判断或下游处理。")

    if old_summary.get("outlier_column_count", 0) or new_summary.get("outlier_column_count", 0):
        risks.append("检测到数值异常列，建议确认是否存在录入错误或异常业务波动。")

    if old_summary.get("suspected_type_issue_count", 0) or new_summary.get("suspected_type_issue_count", 0):
        risks.append("部分列存在疑似类型不一致，后续计算、排序或导出时可能出现格式问题。")

    if diff_summary.get("added_columns") or diff_summary.get("removed_columns"):
        risks.append("表结构发生变化，依赖固定列名的脚本、报表或接口需要同步检查。")

    if not risks:
        risks.append("当前未发现明显高风险项，但仍建议结合业务场景抽样复核关键记录。")

    return risks


def _build_suggestion_lines(
    old_summary: dict[str, Any],
    new_summary: dict[str, Any],
    diff_summary: dict[str, Any],
) -> list[str]:
    suggestions = [
        "优先核对变更行明细，确认是否为预期更新。",
    ]

    if diff_summary.get("changed_columns_summary"):
        top_column = diff_summary["changed_columns_summary"][0]["column_name"]
        suggestions.append(f"重点关注字段“{top_column}”的变化，它是本次变更中最先出现的重点字段之一。")

    if diff_summary.get("added_rows"):
        suggestions.append("建议抽查新增行的主键和关键业务字段，确认新增记录来源正确。")

    if diff_summary.get("removed_rows"):
        suggestions.append("建议确认删除行是否应当下线，避免误删历史有效数据。")

    if old_summary.get("missing_value_cell_count", 0) or new_summary.get("missing_value_cell_count", 0):
        suggestions.append("对缺失值较多的列补充校验规则，避免后续数据质量继续下降。")

    return suggestions


def _build_teammate_message(
    diff_metrics: dict[str, Any],
    diff_summary: dict[str, Any],
    old_summary: dict[str, Any],
    new_summary: dict[str, Any],
) -> str:
    structure_change = "有" if diff_summary.get("added_columns") or diff_summary.get("removed_columns") else "无"
    risk_count = sum(
        [
            1 if old_summary.get("duplicate_key_row_count", 0) or new_summary.get("duplicate_key_row_count", 0) else 0,
            1 if old_summary.get("missing_value_cell_count", 0) or new_summary.get("missing_value_cell_count", 0) else 0,
            1 if old_summary.get("outlier_column_count", 0) or new_summary.get("outlier_column_count", 0) else 0,
            1 if old_summary.get("suspected_type_issue_count", 0) or new_summary.get("suspected_type_issue_count", 0) else 0,
        ]
    )

    return (
        f"本次表格对比已完成：新增 {diff_metrics.get('added_row_count', 0)} 行，"
        f"删除 {diff_metrics.get('removed_row_count', 0)} 行，"
        f"变更 {diff_metrics.get('changed_row_count', 0)} 行，"
        f"字段变更共 {diff_summary.get('changed_cell_count', 0)} 处。"
        f"表结构变更：{structure_change}。"
        f"当前识别到 {risk_count} 类需要关注的数据质量风险，建议优先查看变更行和异常字段明细。"
    )
