from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from token_estimator.estimator import GuardrailError, estimate
from token_estimator.executors import ExecutionError, get_executor
from token_estimator.models import ModelRegistry
from token_estimator.output_predictor import predict_output_tokens

REGISTRY_PATH = Path(__file__).parent / "token_estimator" / "models.yaml"
MAX_PROMPT_CHARS = 400_000  # soft ceiling; warns instead of hard-blocking

TOKENIZER_LABELS = {
    "heuristic": "Heuristic character-count estimate (no pre-execution tokenizer endpoint for this provider)",
}


def load_registry() -> ModelRegistry:
    return ModelRegistry.from_yaml(REGISTRY_PATH)


st.set_page_config(page_title="Prompt Token Estimator", page_icon="\U0001f9ee", layout="wide")

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; max-width: 1100px; }
        div[data-testid="stMetric"] {
            background: rgba(127, 127, 127, 0.08);
            border-radius: 10px;
            padding: 0.75rem 1rem;
        }
        div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

for key, default in {
    "estimation": None,
    "estimation_key": None,
    "execution_result": None,
    "execution_error": None,
    "executed_key": None,
    "_last_predicted_for": None,
    "expected_output_tokens": 200,
}.items():
    st.session_state.setdefault(key, default)

registry = load_registry()


def on_tokens_changed():
    st.session_state["expected_output_tokens"] = st.session_state["expected_output_tokens_widget"]


# The prompt widget is instantiated further down (in the main column), but
# its value from the previous run is already in session_state by this point
# -- read it here so the sidebar's output-token predictor can react to it.
current_prompt_text = st.session_state.get("prompt_text", "")
prediction = predict_output_tokens(current_prompt_text)

# Auto-sync the output-token field to the prediction whenever the prompt
# changes, so it tracks the prompt instead of sitting on a fixed default.
# A manual edit persists until the prompt itself changes again.
if st.session_state["_last_predicted_for"] != current_prompt_text:
    st.session_state["expected_output_tokens"] = prediction.tokens
    st.session_state["_last_predicted_for"] = current_prompt_text

st.title("\U0001f9ee Prompt Token Estimator")
st.caption(
    "Estimate token usage and cost before you spend it. The prompt is only sent to a model "
    "after you explicitly confirm."
)

# --- Sidebar: model + run configuration --------------------------------
with st.sidebar:
    st.header("Configuration")

    grouped = registry.list_by_provider()
    if not grouped:
        st.error("No models configured in token_estimator/models.yaml.")
        st.stop()

    provider = st.selectbox("Model family", sorted(grouped.keys()))
    model_options = {m.display_name: m for m in grouped[provider]}
    model_display = st.selectbox("Model", list(model_options.keys()))
    model = model_options[model_display]

    expected_output_tokens = st.number_input(
        "Expected output tokens",
        min_value=0,
        max_value=200_000,
        value=int(st.session_state["expected_output_tokens"]),
        step=100,
        key="expected_output_tokens_widget",
        on_change=on_tokens_changed,
        help="Predicted from the prompt's content and any length cues in it (e.g. 'in 3 "
        "sentences', 'write a function'). Re-predicted whenever you edit the prompt; you can "
        "still adjust it by hand. Only used to estimate cost before running -- the real output "
        "length is never known until the model responds.",
     )
    st.caption(f"Predicted: {prediction.reason}")

    st.divider()
    st.caption(f"**Token counting:** {TOKENIZER_LABELS.get(model.tokenizer, model.tokenizer)}")
    st.caption(
        f"**Context window:** {f'{model.context_window:,} tokens' if model.context_window else 'not verified for this model'}"
    )
    st.caption(
        f"**Pricing:** ${model.input_price_per_million:.3f}/1M in · "
        f"${model.output_price_per_million:.3f}/1M out"
    )

# --- Main: prompt input --------------------------------------------------
prompt = st.text_area(
    "Prompt",
    height=280,
    placeholder="Paste your professional prompt here...",
    key="prompt_text",
)
char_count = len(prompt)
word_count = len(prompt.split()) if prompt.strip() else 0
st.caption(f"{char_count:,} characters · {word_count:,} words")
if char_count > MAX_PROMPT_CHARS:
    st.warning(
        f"This prompt is very large ({char_count:,} characters). Estimation will still run, "
        "but consider chunking the input for reliability and cost control."
    )

current_key = (prompt, model.provider, model.model_id, int(expected_output_tokens))

if st.button("Estimate tokens", type="primary", use_container_width=True):
    try:
        result = estimate(prompt, model, int(expected_output_tokens))
        st.session_state.estimation = result
        st.session_state.estimation_key = current_key
        st.session_state.execution_result = None
        st.session_state.execution_error = None
        st.session_state.executed_key = None
    except GuardrailError as exc:
        st.session_state.estimation = None
        st.error(str(exc))

estimation = st.session_state.estimation
stale = estimation is not None and st.session_state.estimation_key != current_key

if estimation and not stale:
    with st.container(border=True):
        st.subheader("Token & cost estimate")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Input tokens", f"{estimation.input_tokens:,}")
        m2.metric("Expected output", f"{estimation.expected_output_tokens:,}")
        m3.metric("Total tokens", f"{estimation.total_tokens:,}")
        m4.metric("Estimated cost", f"${estimation.total_cost:.5f}")

        st.caption(f"Input counting method: {estimation.input_token_method}")

        if estimation.context_window_pct is not None:
            st.progress(
                min(estimation.context_window_pct / 100, 1.0),
                text=f"{estimation.context_window_pct}% of {estimation.context_window:,}-token context window",
            )

        for warning in estimation.warnings:
            (st.error if estimation.exceeds_context else st.warning)(warning)

        already_executed = st.session_state.executed_key == st.session_state.estimation_key

        if already_executed:
            st.success("Executed with this estimate. Change the prompt or model, or re-estimate, to run again.")
        else:
            st.markdown("**Execute this prompt?**")
            c1, c2 = st.columns(2)
            confirm_yes = c1.button(
                "✅ Yes, run it",
                type="primary",
                use_container_width=True,
                disabled=estimation.exceeds_context,
            )
            confirm_no = c2.button("❌ No, cancel", use_container_width=True)

            if estimation.exceeds_context:
                st.caption("Execution is disabled until the prompt fits within the model's context window.")

            if confirm_no:
                st.session_state.estimation = None
                st.info("Execution cancelled. No request was sent to any model.")

            if confirm_yes:
                try:
                    executor = get_executor(model.provider)
                    with st.spinner(f"Running prompt on {model.display_name} via {model.provider}..."):
                        result = executor.execute(prompt, model, int(expected_output_tokens))
                    st.session_state.execution_result = result
                    st.session_state.execution_error = None
                    st.session_state.executed_key = st.session_state.estimation_key
                except ExecutionError as exc:
                    st.session_state.execution_error = str(exc)
                    st.session_state.execution_result = None
elif stale and estimation:
    st.info("The prompt, model, or output setting changed since the last estimate. Click **Estimate tokens** again.")

if st.session_state.execution_error:
    st.error(st.session_state.execution_error)

if st.session_state.execution_result:
    with st.container(border=True):
        st.subheader("Output")
        result = st.session_state.execution_result
        st.write(result.text if result.text else "*(empty response)*")

        if result.input_tokens is not None and result.output_tokens is not None:
            actual_cost = (
                (result.input_tokens / 1_000_000) * model.input_price_per_million
                + (result.output_tokens / 1_000_000) * model.output_price_per_million
            )
            a1, a2 = st.columns(2)
            a1.metric("Actual output tokens", f"{result.output_tokens:,}")
            a2.metric("Actual cost", f"${actual_cost:.5f}")
            st.caption(f"Reported by {result.reported_model}")
