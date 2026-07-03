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


def test_short_answer_marker_predicts_small_output():
    result = predict_output_tokens("Answer with one word: is the sky blue?")
    assert result.tokens <= 50


def test_code_marker_predicts_larger_output():
    result = predict_output_tokens("Write a function that reverses a linked list in Python.")
    assert result.tokens >= 500


def test_long_form_marker_predicts_large_output():
    result = predict_output_tokens("Write a comprehensive essay on the history of the printing press.")
    assert result.tokens >= 700


def test_fallback_scales_with_prompt_length_within_bounds():
    result = predict_output_tokens("word " * 1000)
    assert 150 <= result.tokens <= 600
