from dataclasses import dataclass, field
from typing import Any

from ecommerce_search_assistant.core.config import Settings, get_settings


@dataclass
class SentenceTransformerTextEmbeddingService:
    settings: Settings = field(default_factory=get_settings)
    _model: Any | None = field(default=None, init=False, repr=False)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self._apply_query_prompt(text)])[0]

    def warmup(self) -> None:
        self._get_model()

    def _apply_query_prompt(self, text: str) -> str:
        if not self.settings.text_embedding_use_prompt:
            return text
        return self.settings.text_embedding_query_prompt.format(
            task=self.settings.text_embedding_query_instruction,
            text=text,
        )

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=self.settings.embedding_batch_size,
            convert_to_numpy=True,
            device=self.settings.embedding_device,
            normalize_embeddings=self.settings.normalize_embeddings,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector.tolist()] for vector in embeddings]

    def _get_model(self) -> Any:
        if self._model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            from ecommerce_search_assistant.services.embeddings.dtype import resolve_torch_dtype

            if self.settings.embedding_device == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("EMBEDDING_DEVICE=cuda requires an available CUDA runtime")

            self._model = SentenceTransformer(
                self.settings.text_embedding_model_name,
                device=self.settings.embedding_device,
                model_kwargs={"torch_dtype": resolve_torch_dtype(torch, self.settings.embedding_dtype)},
            )
        return self._model
