from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TOKENS = 200  # conservative fallback when there's no prompt yet

_TOKEN_LIMIT_RE = re.compile(r"\b(\d{1,6})[^\S\r\n]*tokens?\b", re.IGNORECASE)
_WORD_LIMIT_RE = re.compile(r"\b(\d{1,5})[^\S\r\n]*words?\b", re.IGNORECASE)
_PARAGRAPH_LIMIT_RE = re.compile(r"\b(\d{1,3})[^\S\r\n]*paragraphs?\b", re.IGNORECASE)
_SENTENCE_LIMIT_RE = re.compile(r"\b(\d{1,3})[^\S\r\n]*sentences?\b", re.IGNORECASE)




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
        # Ensure a floor of at least 10 tokens
        tokens = max(10, n)
        return OutputPrediction(tokens, f'Prompt explicitly asks for ~{n} tokens')

    if match := _WORD_LIMIT_RE.search(text):
        n = int(match.group(1))
        # Ensure a floor of at least 10 tokens
        tokens = max(10, round(n * 1.3))
        return OutputPrediction(tokens, f"Prompt asks for ~{n} words (~1.3 tokens/word)")

    if match := _PARAGRAPH_LIMIT_RE.search(text):
        n = int(match.group(1))
        # Ensure a floor of at least 15 tokens
        tokens = max(15, round(n * 75))
        return OutputPrediction(tokens, f"Prompt asks for {n} paragraph(s) (~75 tokens/paragraph)")

    if match := _SENTENCE_LIMIT_RE.search(text):
        n = int(match.group(1))
        # Ensure a floor of at least 10 tokens
        tokens = max(10, round(n * 20))
        return OutputPrediction(tokens, f"Prompt asks for {n} sentence(s) (~20 tokens/sentence)")

    line_count = len(text.splitlines())
    word_count = len(text.split())

    if line_count >= 1000:
        # For prompts over 1000 lines, provide a generous capacity scaling (15% of words, floor of 2000, ceil of 8000)
        scaled = max(2000, min(8000, round(word_count * 0.15)))
        reason = "Large prompt (>1000 lines) -- scaled from prompt length with high-capacity floor"
    else:
        # Standard fallback scaling based on word count
        if word_count < 500:
            # Scale small-to-medium prompts continuously (1.2 tokens per word, floor of 50)
            scaled = max(50, round(word_count * 1.2))
        else:
            # Scale larger prompts continuously up to 4096 tokens
            scaled = min(4096, 600 + round((word_count - 500) * 0.15))
        reason = "No explicit length cue -- scaled from prompt length"

    return OutputPrediction(scaled, reason)
