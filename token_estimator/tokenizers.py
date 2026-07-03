from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenCountResult:
    token_count: int
    method: str  # human-readable description shown to the user
    is_estimate: bool  # False only for an exact, provider-verified count


class TokenizerStrategy:
    """One token-counting method. Each model in the registry names one by key.

    To support a new provider with a real tokenizer/count endpoint, add a
    subclass here and register it in TOKENIZERS -- estimator.py and app.py
    need no changes.
    """

    def count(self, text: str, model_id: str) -> TokenCountResult:
        raise NotImplementedError


class HeuristicTokenizer(TokenizerStrategy):
    """Used for providers with no pre-execution tokenizer endpoint (e.g. Groq).

    Character-count based with a light content-type adjustment. Always
    labeled as an estimate -- never presented as exact. The real count is
    available after execution from the provider's own usage report.
    """

    def count(self, text: str, model_id: str) -> TokenCountResult:
        char_count = len(text)
        factor = _adjustment_factor(text)
        estimate = round((char_count / 4) * factor) if char_count else 0
        method = "Heuristic estimate (~4 chars/token, content-adjusted) -- this provider has no pre-execution tokenizer endpoint"
        return TokenCountResult(estimate, method, is_estimate=True)


def _adjustment_factor(text: str) -> float:
    """Cheap content-type sniff on a sample of the prompt, not the whole thing."""
    sample = text[:2000]
    if not sample:
        return 1.0
    structured_markers = sample.count("{") + sample.count("[") + sample.count('":')
    code_markers = sample.count("def ") + sample.count("function ") + sample.count("=>") + sample.count("    ")
    if structured_markers > 10:
        return 1.3  # JSON/structured data tokenizes denser than prose
    if code_markers > 10:
        return 1.2  # code
    return 1.0  # general prose


TOKENIZERS: dict[str, TokenizerStrategy] = {
    "heuristic": HeuristicTokenizer(),
}
