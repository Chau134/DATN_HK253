from typing import Protocol


class RerankService(Protocol):
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """Return one relevance score per document, aligned with the input order."""
        ...

    def warmup(self) -> None:
        ...
