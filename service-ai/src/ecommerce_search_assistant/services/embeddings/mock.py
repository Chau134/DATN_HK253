from dataclasses import dataclass
from hashlib import blake2b
from math import sqrt

from PIL import Image


def _normalized(values: list[float]) -> list[float]:
    magnitude = sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return values
    return [value / magnitude for value in values]


def _hash_embedding(seed: bytes, dimensions: int, normalize: bool) -> list[float]:
    digest_size = max(16, min(64, dimensions))
    digest = blake2b(seed, digest_size=digest_size).digest()
    values = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(dimensions)]
    return _normalized(values) if normalize else values


@dataclass(frozen=True)
class MockTextEmbeddingService:
    dimensions: int = 8
    normalize_embeddings: bool = True

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            _hash_embedding(text.encode("utf-8"), self.dimensions, self.normalize_embeddings)
            for text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def warmup(self) -> None:
        return None


@dataclass(frozen=True)
class MockImageEmbeddingService:
    dimensions: int = 8
    normalize_embeddings: bool = True

    def embed_image(self, image: Image.Image) -> list[float]:
        return self.embed_batch([image])[0]

    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        return [
            _hash_embedding(image.tobytes(), self.dimensions, self.normalize_embeddings)
            for image in images
        ]

    def embed_documents(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)

    def embed_queries(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)

    def warmup(self) -> None:
        return None
