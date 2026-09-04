from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings


@dataclass
class TransformersImageEmbeddingService:
    settings: Settings = field(default_factory=get_settings)
    _model: Any | None = field(default=None, init=False, repr=False)
    _processor: Any | None = field(default=None, init=False, repr=False)
    _torch: Any | None = field(default=None, init=False, repr=False)
    _backend: str = field(default="transformers", init=False, repr=False)

    def embed_image(self, image: Image.Image) -> list[float]:
        return self.embed_batch([image])[0]

    def warmup(self) -> None:
        self._get_components()

    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        if not images:
            return []

        model, processor, torch = self._get_components()
        if self._backend == "sentence_transformers":
            return self._embed_sentence_transformers(model, images)

        vectors: list[list[float]] = []
        for start in range(0, len(images), self.settings.embedding_batch_size):
            batch = images[start : start + self.settings.embedding_batch_size]

            with torch.inference_mode():
                if self._backend == "open_clip":
                    prepared = torch.stack([processor(image) for image in batch]).to(self.settings.embedding_device)
                    embeddings = _as_embedding_tensor(model.encode_image(prepared))
                else:
                    prepared = processor(images=batch, return_tensors="pt")
                    prepared = {
                        key: value.to(self.settings.embedding_device) if hasattr(value, "to") else value
                        for key, value in prepared.items()
                    }
                    embeddings = _as_embedding_tensor(model.get_image_features(**prepared))
                if self.settings.normalize_embeddings:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            vectors.extend(
                [float(value) for value in vector]
                for vector in embeddings.detach().cpu().tolist()
            )
        return vectors

    def embed_documents(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)

    def embed_queries(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)

    def _embed_sentence_transformers(self, model: Any, images: list[Image.Image]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(images), self.settings.embedding_batch_size):
            batch = images[start : start + self.settings.embedding_batch_size]
            embeddings = model.encode(
                batch,
                batch_size=self.settings.embedding_batch_size,
                convert_to_numpy=True,
                device=self.settings.embedding_device,
                normalize_embeddings=self.settings.normalize_embeddings,
                show_progress_bar=False,
            )
            vectors.extend([float(value) for value in vector.tolist()] for vector in embeddings)
        return vectors

    def _get_components(self) -> tuple[Any, Any, Any]:
        if self._model is None or self._torch is None:
            import torch

            from ecommerce_search_assistant.services.embeddings.dtype import resolve_torch_dtype

            if self.settings.embedding_device == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("EMBEDDING_DEVICE=cuda requires an available CUDA runtime")

            torch_dtype = resolve_torch_dtype(torch, self.settings.embedding_dtype)

            if self.settings.image_embedding_model_name == "Marqo/marqo-fashionSigLIP":
                import open_clip

                self._model, _, self._processor = open_clip.create_model_and_transforms(
                    f"hf-hub:{self.settings.image_embedding_model_name}",
                    device=self.settings.embedding_device,
                )
                self._model.eval()
                self._backend = "open_clip"
            elif _is_sentence_transformer_image_model(self.settings.image_embedding_model_name):
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    self.settings.image_embedding_model_name,
                    device=self.settings.embedding_device,
                    trust_remote_code=self.settings.image_embedding_trust_remote_code,
                    model_kwargs={"torch_dtype": torch_dtype},
                )
                self._processor = None
                self._backend = "sentence_transformers"
            else:
                from transformers import AutoModel, AutoProcessor

                self._processor = AutoProcessor.from_pretrained(
                    self.settings.image_embedding_model_name,
                    trust_remote_code=self.settings.image_embedding_trust_remote_code,
                )
                self._model = AutoModel.from_pretrained(
                    self.settings.image_embedding_model_name,
                    trust_remote_code=self.settings.image_embedding_trust_remote_code,
                    torch_dtype=torch_dtype,
                )
                self._model.eval()
                self._model.to(self.settings.embedding_device)
                self._backend = "transformers"
            self._torch = torch

        return self._model, self._processor, self._torch


def _is_sentence_transformer_image_model(model_name: str) -> bool:
    return "qwen3-vl-embedding" in model_name.lower()


def _as_embedding_tensor(output: Any) -> Any:
    if hasattr(output, "detach"):
        return output
    if hasattr(output, "pooler_output"):
        return output.pooler_output
    if hasattr(output, "image_embeds"):
        return output.image_embeds
    raise TypeError(f"image embedding model returned unsupported output type: {type(output)!r}")
