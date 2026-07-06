from token_estimator.output_predictor import DEFAULT_TOKENS, predict_output_tokens


def test_empty_prompt_returns_conservative_default():
    result = predict_output_tokens("")
    assert result.tokens == DEFAULT_TOKENS


def test_explicit_token_count_is_respected():
    result = predict_output_tokens("Summarize this in about 300 tokens.")
    assert result.tokens == 300


def test_explicit_word_count_scales_to_tokens():
    result = predict_output_tokens("Write a bio in 100 words.")
    assert result.tokens == round(100 * 1.3)


def test_explicit_sentence_count_scales_to_tokens():
    result = predict_output_tokens("Answer in 2 sentences.")
    assert result.tokens == 40


def test_floor_limits_for_explicit_cues():
    # 1 word limit matches floor of 10
    result_word = predict_output_tokens("Answer in 1 word.")
    assert result_word.tokens == 10

    # 1 token limit matches floor of 10
    result_token = predict_output_tokens("Give me response in 1 token.")
    assert result_token.tokens == 10

    # 1 paragraph limit matches floor of 15
    result_paragraph = predict_output_tokens("Answer in 1 paragraph.")
    assert result_paragraph.tokens == 75  # 1 * 75 = 75 which is >= 15 floor

    # 1 sentence limit matches floor of 10
    result_sentence = predict_output_tokens("Answer in 1 sentence.")
    assert result_sentence.tokens == 20  # 1 * 20 = 20 which is >= 10 floor


def test_numbers_and_units_on_different_lines_do_not_match():
    prompt = "There are 10\nwords in this list."
    result = predict_output_tokens(prompt)
    # The new floor is 150 for fallback estimates
    assert result.tokens == 150
    assert "No explicit length cue" in result.reason


def test_proportional_scaling_bounds():
    # Small prompt (10 words) -> ~14 input tokens -> floored at 150
    result_small = predict_output_tokens("word " * 10)
    assert result_small.tokens == 150

    # Medium prompt (1000 words) -> ~1350 input tokens -> ~405 expected output tokens
    result_medium = predict_output_tokens("word " * 1000)
    assert result_medium.tokens == 405

    # Massive prompt (20000 words) -> ~27000 input tokens -> 8100 expected -> capped at 4096
    result_massive = predict_output_tokens("word " * 20000)
    assert result_massive.tokens == 4096


def test_messy_multiline_vs_clean_single_paragraph_prompt():
    # Clean single paragraph prompt of 300 words
    clean_prompt = "word " * 300

    # Messy prompt of 300 words with 50+ blank lines and irregular spacing
    prompt_words = ["word"] * 300
    messy_lines = []
    for i, word in enumerate(prompt_words):
        messy_lines.append(word)
        if i % 5 == 0:
            messy_lines.append("")  # insert empty line
            messy_lines.append("   ")  # line with spaces
    messy_prompt = "\n".join(messy_lines)

    result_clean = predict_output_tokens(clean_prompt)
    result_messy = predict_output_tokens(messy_prompt)

    # Assert messy prompt estimate is NOT anomalously small (e.g. not close to 10)
    assert result_messy.tokens >= 150
    # Assert they produce the exact same (or very close) token estimate
    assert result_clean.tokens == result_messy.tokens


