from typing import Protocol

from PIL import Image


class TextEmbeddingService(Protocol):
    def embed_text(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def warmup(self) -> None:
        ...


class ImageEmbeddingService(Protocol):
    def embed_image(self, image: Image.Image) -> list[float]:
        ...

    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        ...

    def embed_documents(self, images: list[Image.Image]) -> list[list[float]]:
        ...

    def embed_queries(self, images: list[Image.Image]) -> list[list[float]]:
        ...

    def warmup(self) -> None:
        ...
