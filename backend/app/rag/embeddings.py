"""
Embedding model wrapper.

Uses `fastembed` (ONNX Runtime, no PyTorch) so the default deployment stays
CPU-friendly and light enough for Render Free (§10, §75). The model name is
fully configurable via EMBEDDING_MODEL — swapping embedding models never
requires touching the rest of the app.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.config import get_settings


class EmbeddingModel:
    def __init__(self, model_name: str) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype="float32")
        vectors = list(self._model.embed(texts))
        arr = np.array(vectors, dtype="float32")
        return _l2_normalize(arr)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        # bge-small-en-v1.5 = 384 dims; kept generic in case EMBEDDING_MODEL changes.
        return 384


def _l2_normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    return EmbeddingModel(settings.EMBEDDING_MODEL)
