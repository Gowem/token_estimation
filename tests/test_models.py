from pathlib import Path

from token_estimator.models import ModelRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "token_estimator" / "models.yaml"


def test_registry_loads_groq_models():
    registry = ModelRegistry.from_yaml(REGISTRY_PATH)
    grouped = registry.list_by_provider()
    assert "groq" in grouped
    assert "gpt" in grouped
    assert "meta" in grouped
    assert len(registry.all()) >= 4


def test_get_returns_none_for_unknown_model():
    registry = ModelRegistry.from_yaml(REGISTRY_PATH)
    assert registry.get("not-a-real-model") is None


def test_get_returns_model_for_known_id():
    registry = ModelRegistry.from_yaml(REGISTRY_PATH)
    model = registry.get("llama-3.1-8b-instant")
    assert model is not None
    assert model.provider == "meta"


def test_duplicate_model_id_rejected():
    from token_estimator.models import ModelConfig

    dup = ModelConfig(
        provider="a",
        model_id="same-id",
        display_name="A",
        input_price_per_million=1.0,
        output_price_per_million=1.0,
        tokenizer="heuristic",
    )
    dup2 = ModelConfig(
        provider="b",
        model_id="same-id",
        display_name="B",
        input_price_per_million=1.0,
        output_price_per_million=1.0,
        tokenizer="heuristic",
    )
    try:
        ModelRegistry([dup, dup2])
        assert False, "expected ValueError for duplicate model_id"
    except ValueError:
        pass
