import pytest

from token_estimator.estimator import GuardrailError, estimate
from token_estimator.models import ModelConfig


def make_model(**overrides):
    base = dict(
        provider="groq",
        model_id="llama-3.1-8b-instant",
        display_name="Test Model",
        input_price_per_million=1.0,
        output_price_per_million=2.0,
        tokenizer="heuristic",
        context_window=1000,
    )
    base.update(overrides)
    return ModelConfig(**base)


def test_empty_prompt_raises_guardrail():
    with pytest.raises(GuardrailError):
        estimate("   ", make_model(), 100)


def test_unsupported_model_raises_guardrail():
    with pytest.raises(GuardrailError):
        estimate("hello", None, 100)


def test_negative_output_tokens_raises_guardrail():
    with pytest.raises(GuardrailError):
        estimate("hello", make_model(), -1)


def test_estimate_computes_cost():
    model = make_model(input_price_per_million=1_000_000, output_price_per_million=2_000_000)
    result = estimate("a" * 400, model, 10)  # heuristic: ~100 input tokens
    assert result.input_tokens > 0
    assert result.total_tokens == result.input_tokens + 10
    assert result.total_cost == pytest.approx(result.input_cost + result.output_cost)


def test_context_window_exceeded_flagged_not_raised():
    model = make_model(context_window=50)
    result = estimate("word " * 500, model, 0)  # far more than 50 tokens
    assert result.exceeds_context is True
    assert any("exceed" in w for w in result.warnings)


def test_unknown_context_window_warns_but_does_not_block():
    model = make_model(context_window=None)
    result = estimate("hello world", model, 0)
    assert result.exceeds_context is False
    assert result.context_window_pct is None
    assert any("not verified" in w for w in result.warnings)


def test_heuristic_result_is_flagged_as_estimate():
    model = make_model(tokenizer="heuristic")
    result = estimate("hello world", model, 0)
    assert result.input_is_estimate is True
