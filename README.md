# Prompt Token Estimator

A small web app that estimates token usage and cost for a prompt against a
configurable list of Groq models, asks for explicit confirmation, and only
then sends the prompt to the model.

## Flow

1. Paste a prompt and pick a model.
2. Click **Estimate tokens** — shows input/output/total token counts, cost,
   percentage of the model's context window used, and exactly how the token
   count was computed.
3. If the prompt fits, confirm **Yes, run it** / **No, cancel**. Nothing is
   sent to any API until you click Yes.
4. On execution, the real usage reported by the API is shown next to the
   estimate so you can see how accurate it was.

## Architecture

```
token_estimator/
  models.py        # ModelConfig + ModelRegistry (loaded from models.yaml)
  models.yaml       # the configurable model list -- add/remove models here, no code changes
  tokenizers.py      # TokenizerStrategy abstraction; currently one Groq heuristic implementation
  estimator.py       # pure estimation logic + guardrails (empty prompt, unsupported
                      # model, context-window overflow); no network calls
  executors.py        # Executor abstraction; currently one Groq implementation
app.py                # Streamlit UI wiring the above together
```

This deployment is scoped to Groq (the only provider with a configured key),
but the estimator, guardrails, and UI are provider-agnostic. Adding a new
model is a YAML edit. Adding a new *provider* means implementing one
`TokenizerStrategy` subclass in `tokenizers.py` and one `Executor` subclass
in `executors.py`, then registering each in its module-level dict — nothing
else in the codebase changes.

### How token counting works

Groq has no pre-execution tokenizer endpoint, so the app uses a
character-count heuristic (~4 characters per token, adjusted upward for code
or structured/JSON content) and always labels it as an **estimate**. The
real count is shown after execution, taken from the API's own usage report.

### Guardrails

- Empty prompt, no model selected, or a negative output-token value are
  rejected with a clear message before any estimate is computed.
- If the estimated total tokens exceed a model's known context window, the
  **Yes, run it** button is disabled until the prompt is trimmed.
- If a model's context window isn't verified in `models.yaml`
  (`context_window: null`), the limit check is skipped and the UI says so
  explicitly rather than guessing.
- A missing `GROQ_API_KEY` or an API failure surfaces as a clean message, not
  a stack trace.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your GROQ_API_KEY
streamlit run app.py
```

## Tests

```bash
pytest
```

## Deploying on Render

This is a single Streamlit app (frontend and backend in one process, no
separate API layer) -- Render runs it as a persistent web service basically
unchanged. `render.yaml` in this repo is a Render Blueprint that defines the
service; Render reads it automatically when you create a Blueprint deploy.

1. Push this repo to GitHub (don't commit `.env` -- it's gitignored).
2. In the Render dashboard: **New > Blueprint**, connect the repo. Render
   will pick up `render.yaml` and configure the service automatically.
3. Before the first deploy finishes, open the service's **Environment** tab
   and set `GROQ_API_KEY` (it's declared in `render.yaml` with `sync: false`
   specifically so Render prompts you for it instead of expecting it in the
   repo).
4. Deploy. Render builds with `pip install -r requirements.txt` and starts
   the app with `streamlit run app.py --server.port $PORT --server.address
   0.0.0.0`.

Note: Vercel is not a fit for this app -- it's a serverless platform (short
request/response cycles), while Streamlit needs a long-running process with
a persistent WebSocket connection per session. Render (or any host that runs
persistent containers/processes) is what this architecture needs.
