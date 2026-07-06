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


def normalize_prompt_for_estimation(prompt: str) -> str:
    """Normalize the prompt for token estimation: collapse consecutive blank lines

    and strip leading/trailing whitespace per line.
    """
    lines = prompt.splitlines()
    stripped_lines = [line.strip() for line in lines]
    
    cleaned_lines = []
    prev_was_empty = False
    for line in stripped_lines:
        if line == "":
            if not prev_was_empty:
                cleaned_lines.append("")
                prev_was_empty = True
        else:
            cleaned_lines.append(line)
            prev_was_empty = False

    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def predict_output_tokens(prompt: str) -> OutputPrediction:
    """Predict a reasonable expected-output-token count from the prompt itself.

    Always a heuristic default for the cost estimate -- never used to block
    or alter execution, and the caller is free to override the number.
    Priority: explicit length instructions in the prompt > proportional scaling
    based on normalized input length.
    """
    normalized_text = normalize_prompt_for_estimation(prompt)
    if not normalized_text:
        return OutputPrediction(DEFAULT_TOKENS, "No prompt yet -- conservative default")

    if match := _TOKEN_LIMIT_RE.search(normalized_text):
        n = int(match.group(1))
        # Ensure a floor of at least 10 tokens
        tokens = max(10, n)
        return OutputPrediction(tokens, f'Prompt explicitly asks for ~{n} tokens')

    if match := _WORD_LIMIT_RE.search(normalized_text):
        n = int(match.group(1))
        # Ensure a floor of at least 10 tokens
        tokens = max(10, round(n * 1.3))
        return OutputPrediction(tokens, f"Prompt asks for ~{n} words (~1.3 tokens/word)")

    if match := _PARAGRAPH_LIMIT_RE.search(normalized_text):
        n = int(match.group(1))
        # Ensure a floor of at least 15 tokens
        tokens = max(15, round(n * 75))
        return OutputPrediction(tokens, f"Prompt asks for {n} paragraph(s) (~75 tokens/paragraph)")

    if match := _SENTENCE_LIMIT_RE.search(normalized_text):
        n = int(match.group(1))
        # Ensure a floor of at least 10 tokens
        tokens = max(10, round(n * 20))
        return OutputPrediction(tokens, f"Prompt asks for {n} sentence(s) (~20 tokens/sentence)")

    word_count = len(normalized_text.split())
    # Heuristic: 1.35 tokens per word for English text and code
    input_token_estimate = round(word_count * 1.35)

    # Base the expected output on 30% of the estimated input tokens,
    # bounded between a minimum of 150 tokens and a maximum of 4096 tokens.
    scaled = max(150, min(4096, round(input_token_estimate * 0.30)))
    reason = "No explicit length cue -- scaled proportionally from input length"

    return OutputPrediction(scaled, reason)
