from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

import yaml


@dataclasses.dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    display_name: str
    input_price_per_million: float
    output_price_per_million: float
    tokenizer: str  # key into token_estimator.tokenizers.TOKENIZERS
    context_window: Optional[int] = None  # None = unverified; disables the context-limit guardrail
    notes: str = ""


class ModelRegistry:
    """Configurable, provider-agnostic catalog of models.

    Loaded from a YAML file so new models/providers can be added without
    touching estimator, executor, or UI code.
    """

    def __init__(self, models: list[ModelConfig]):
        self._by_id: dict[str, ModelConfig] = {}
        for model in models:
            if model.model_id in self._by_id:
                raise ValueError(f"Duplicate model_id in registry: {model.model_id!r}")
            self._by_id[model.model_id] = model

    @classmethod
    def from_yaml(cls, path: Path) -> "ModelRegistry":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        raw_models = data.get("models", [])
        models = [ModelConfig(**entry) for entry in raw_models]
        return cls(models)

    def get(self, model_id: str) -> Optional[ModelConfig]:
        return self._by_id.get(model_id)

    def all(self) -> list[ModelConfig]:
        return list(self._by_id.values())

    def list_by_provider(self) -> dict[str, list[ModelConfig]]:
        grouped: dict[str, list[ModelConfig]] = {}
        for model in self._by_id.values():
            grouped.setdefault(model.provider, []).append(model)
        for entries in grouped.values():
            entries.sort(key=lambda m: m.display_name)
        return grouped
