from __future__ import annotations

import os

import pytest

from src.llm_summary import (
    OpenAICompatibleLLMClient,
    create_llm_client_from_env,
    generate_change_summary,
)


class FakeLLMClient:
    def __init__(self, response: str, should_fail: bool = False) -> None:
        self.response = response
        self.should_fail = should_fail

    def generate_text(self, prompt: str) -> str:
        if self.should_fail:
            raise ValueError("failed")
        assert "diff_summary" in prompt
        return self.response


def build_validation_result() -> dict:
    return {
        "summary": {
            "missing_value_cell_count": 2,
            "duplicate_key_row_count": 1,
            "outlier_column_count": 1,
            "suspected_type_issue_count": 1,
        }
    }


def build_diff_result() -> dict:
    return {
        "added_columns": ["remark"],
        "removed_columns": [],
        "changed_cell_count": 3,
        "summary": {
            "added_row_count": 1,
            "removed_row_count": 0,
            "changed_row_count": 2,
        },
        "changed_columns_summary": [
            {
                "column_name": "amount",
                "change_count": 2,
                "sample_primary_keys": [1001, 1002],
            }
        ],
        "added_rows": [{"primary_key_value": 1003, "row_data": {"amount": 50}}],
        "removed_rows": [],
    }


def test_generate_change_summary_returns_local_template_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    summary = generate_change_summary(
        old_validation=build_validation_result(),
        new_validation=build_validation_result(),
        diff_summary=build_diff_result(),
    )

    assert "本次变更概览" in summary
    assert "主要风险提示" in summary
    assert "建议关注项" in summary
    assert "适合同事同步的更新说明" in summary


def test_generate_change_summary_uses_injected_client_when_available() -> None:
    summary = generate_change_summary(
        old_validation=build_validation_result(),
        new_validation=build_validation_result(),
        diff_summary=build_diff_result(),
        llm_client=FakeLLMClient("这是模型生成的摘要。"),
    )

    assert summary == "这是模型生成的摘要。"


def test_generate_change_summary_falls_back_when_client_fails() -> None:
    summary = generate_change_summary(
        old_validation=build_validation_result(),
        new_validation=build_validation_result(),
        diff_summary=build_diff_result(),
        llm_client=FakeLLMClient("unused", should_fail=True),
    )

    assert "本次变更概览" in summary
    assert "新增 1 行" in summary


def test_create_llm_client_from_env_returns_client_when_env_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_URL", "https://example.com/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "demo-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = create_llm_client_from_env()

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client.api_key == "test-key"
    assert client.api_url == "https://example.com/v1/chat/completions"
    assert client.model == "demo-model"


def test_create_llm_client_from_env_returns_none_when_env_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    client = create_llm_client_from_env()

    assert client is None
