import pytest

from token_estimator.executors import ExecutionError, get_executor
from token_estimator.models import ModelConfig


def make_model(provider: str) -> ModelConfig:
    return ModelConfig(
        provider=provider,
        model_id="whatever-model",
        display_name="Whatever",
        input_price_per_million=1.0,
        output_price_per_million=1.0,
        tokenizer="heuristic",
    )


def test_execute_without_api_key_raises_clean_error(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    executor = get_executor("groq")
    with pytest.raises(ExecutionError, match="GROQ_API_KEY"):
        executor.execute("hello", make_model("groq"), 100)


def test_unknown_provider_raises_execution_error():
    with pytest.raises(ExecutionError):
        get_executor("not-a-real-provider")
