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


def test_small_prompt_scales_down():
    # 10 words prompt scales to floor of 50 tokens
    result = predict_output_tokens("hello world " * 5)
    assert result.tokens == 50

    # 100 words prompt scales to 120 tokens (100 * 1.2)
    result = predict_output_tokens("word " * 100)
    assert result.tokens == 120


def test_fallback_scales_with_prompt_length_within_bounds():
    result = predict_output_tokens("word " * 1000)
    # The new scaling fallback scales up past 600 for larger inputs, capped at 4096.
    assert 150 <= result.tokens <= 4096
    assert result.tokens == 675  # 600 + (1000 - 500) * 0.15


def test_1000_line_prompt_scales_generously():
    # Construct a prompt with 1050 lines and 15000 words
    prompt_lines = ["word word word word word word word word word word word word word word word"] * 1050
    prompt = "\n".join(prompt_lines)
    result = predict_output_tokens(prompt)
    assert result.tokens >= 2000
    assert "Large prompt (>1000 lines)" in result.reason


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

