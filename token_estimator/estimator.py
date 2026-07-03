from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import ModelConfig
from .tokenizers import TOKENIZERS


class GuardrailError(Exception):
    """Raised for invalid input, an unsupported model, or anything else that
    should stop the flow with a clean message instead of a stack trace."""


@dataclass
class EstimationResult:
    model: ModelConfig
    input_tokens: int
    input_token_method: str
    input_is_estimate: bool
    expected_output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    context_window: Optional[int]
    context_window_pct: Optional[float]
    exceeds_context: bool
    warnings: list[str]


def validate_inputs(prompt: str, model: Optional[ModelConfig], expected_output_tokens: int) -> None:
    if model is None:
        raise GuardrailError("Selected model is not in the configured registry. Choose a supported model.")
    if prompt is None or not prompt.strip():
        raise GuardrailError("Prompt is empty. Enter a prompt before estimating.")
    if expected_output_tokens < 0:
        raise GuardrailError("Expected output tokens cannot be negative.")


def estimate(prompt: str, model: Optional[ModelConfig], expected_output_tokens: int) -> EstimationResult:
    """Compute token usage and cost for a prompt against one model.

    Never executes anything -- pure estimation. Raises GuardrailError for
    invalid input; returns a result with `.warnings` (and possibly
    `.exceeds_context`) for problems that should be shown but not block the
    estimate itself.
    """
    validate_inputs(prompt, model, expected_output_tokens)
    assert model is not None  # narrowed by validate_inputs

    tokenizer = TOKENIZERS[model.tokenizer]
    count_result = tokenizer.count(prompt, model.model_id)

    input_tokens = count_result.token_count
    total_tokens = input_tokens + expected_output_tokens

    input_cost = (input_tokens / 1_000_000) * model.input_price_per_million
    output_cost = (expected_output_tokens / 1_000_000) * model.output_price_per_million

    warnings: list[str] = []
    exceeds_context = False
    context_window_pct: Optional[float] = None

    if model.context_window:
        context_window_pct = round(100 * total_tokens / model.context_window, 1)
        if total_tokens > model.context_window:
            exceeds_context = True
            warnings.append(
                f"Estimated total tokens ({total_tokens:,}) exceed {model.display_name}'s "
                f"context window ({model.context_window:,}). Reduce the prompt or expected "
                "output before running."
            )
    else:
        warnings.append(
            f"{model.display_name}'s context window is not verified in this registry -- "
            "context-limit checking is disabled for this model."
        )

    if count_result.is_estimate:
        warnings.append(f"Input token count is an estimate, not an exact count: {count_result.method}")

    return EstimationResult(
        model=model,
        input_tokens=input_tokens,
        input_token_method=count_result.method,
        input_is_estimate=count_result.is_estimate,
        expected_output_tokens=expected_output_tokens,
        total_tokens=total_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        context_window=model.context_window,
        context_window_pct=context_window_pct,
        exceeds_context=exceeds_context,
        warnings=warnings,
    )
