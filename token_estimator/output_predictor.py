from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TOKENS = 200  # conservative fallback when there's no prompt yet

_TOKEN_LIMIT_RE = re.compile(r"\b(\d{1,6})\s*tokens?\b", re.IGNORECASE)
_WORD_LIMIT_RE = re.compile(r"\b(\d{1,5})\s*words?\b", re.IGNORECASE)
_PARAGRAPH_LIMIT_RE = re.compile(r"\b(\d{1,3})\s*paragraphs?\b", re.IGNORECASE)
_SENTENCE_LIMIT_RE = re.compile(r"\b(\d{1,3})\s*sentences?\b", re.IGNORECASE)

_SHORT_MARKERS = (
    "one word",
    "single word",
    "yes or no",
    "briefly",
    "one sentence",
    "in short",
    "tl;dr",
    "just the answer",
    "a single number",
)
_CODE_MARKERS = ("write a function", "write code", "implement", "```", "def ", "class ", "script", "regex")
_LONG_MARKERS = (
    "essay",
    "report",
    "in detail",
    "comprehensive",
    "step by step",
    "step-by-step",
    "story",
    "article",
    "blog post",
    "documentation",
    "detailed explanation",
    "thorough",
)


@dataclass
class OutputPrediction:
    tokens: int
    reason: str


def predict_output_tokens(prompt: str) -> OutputPrediction:
    """Predict a reasonable expected-output-token count from the prompt itself.

    Always a heuristic default for the cost estimate -- never used to block
    or alter execution, and the caller is free to override the number.
    Priority: explicit length instructions in the prompt > task-type
    keyword signals > scaling with prompt length.
    """
    text = prompt.strip()
    if not text:
        return OutputPrediction(DEFAULT_TOKENS, "No prompt yet -- conservative default")

    if match := _TOKEN_LIMIT_RE.search(text):
        n = int(match.group(1))
        return OutputPrediction(n, f'Prompt explicitly asks for ~{n} tokens')

    if match := _WORD_LIMIT_RE.search(text):
        n = int(match.group(1))
        tokens = max(1, round(n * 1.3))
        return OutputPrediction(tokens, f"Prompt asks for ~{n} words (~1.3 tokens/word)")

    if match := _PARAGRAPH_LIMIT_RE.search(text):
        n = int(match.group(1))
        tokens = max(1, round(n * 75))
        return OutputPrediction(tokens, f"Prompt asks for {n} paragraph(s) (~75 tokens/paragraph)")

    if match := _SENTENCE_LIMIT_RE.search(text):
        n = int(match.group(1))
        tokens = max(1, round(n * 20))
        return OutputPrediction(tokens, f"Prompt asks for {n} sentence(s) (~20 tokens/sentence)")

    lowered = text.lower()
    if any(marker in lowered for marker in _SHORT_MARKERS):
        return OutputPrediction(40, "Prompt signals a short, direct answer")
    if any(marker in lowered for marker in _CODE_MARKERS):
        return OutputPrediction(700, "Prompt appears to request code")
    if any(marker in lowered for marker in _LONG_MARKERS):
        return OutputPrediction(900, "Prompt signals a long-form response")

    word_count = len(text.split())
    scaled = max(150, min(600, round(word_count * 0.8)))
    return OutputPrediction(scaled, "No explicit length cue -- scaled from prompt length")
