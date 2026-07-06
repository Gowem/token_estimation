from __future__ import annotations

import os
from dataclasses import dataclass

from .models import ModelConfig


class ExecutionError(Exception):
    """Raised when a prompt can't be executed -- missing key, missing SDK, or
    an API failure. Always caught and shown as a clean message, never a
    raw traceback."""


@dataclass
class ExecutionResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    reported_model: str


class Executor:
    """Runs a confirmed prompt against one provider.

    To support a new provider, add a subclass here and register it in
    EXECUTORS -- estimator.py and app.py need no changes.
    """

    def execute(self, prompt: str, model: ModelConfig, max_output_tokens: int) -> ExecutionResult:
        raise NotImplementedError


class GroqExecutor(Executor):
    def execute(self, prompt: str, model: ModelConfig, max_output_tokens: int) -> ExecutionResult:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ExecutionError("GROQ_API_KEY is not set. Add it to your environment before running Groq models.")
        try:
            from groq import Groq
        except ImportError as exc:
            raise ExecutionError("The 'groq' package is not installed. Run: pip install groq") from exc

        client = Groq(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model=model.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=None,  # Do not truncate execution based on cost-estimation settings
            )
        except Exception as exc:
            raise ExecutionError(f"Groq API request failed: {exc}") from exc

        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        return ExecutionResult(
            text=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            reported_model=response.model,
        )


EXECUTORS: dict[str, Executor] = {
    "groq": GroqExecutor(),
    "gpt": GroqExecutor(),
    "meta": GroqExecutor(),
}


def get_executor(provider: str) -> Executor:
    executor = EXECUTORS.get(provider)
    if executor is None:
        raise ExecutionError(f"No executor configured for provider '{provider}'.")
    return executor
