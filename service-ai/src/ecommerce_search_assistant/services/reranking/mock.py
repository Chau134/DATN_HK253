from dataclasses import dataclass
from hashlib import blake2b


@dataclass(frozen=True)
class MockRerankService:
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        return [_deterministic_score(query, document) for document in documents]

    def warmup(self) -> None:
        return None


def _deterministic_score(query: str, document: str) -> float:
    digest = blake2b(f"{query}\x00{document}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)
