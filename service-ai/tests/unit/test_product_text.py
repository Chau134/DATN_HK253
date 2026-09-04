from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.schemas.product import ProductIndexItem
from ecommerce_search_assistant.services.embeddings.formatting import build_product_embedding_text
from ecommerce_search_assistant.services.embeddings.text import SentenceTransformerTextEmbeddingService


def test_product_text_document_builder_matches_embedding_contract() -> None:
    item = ProductIndexItem(
        product_id="P-100",
        product_display_name="Retro Tee",
        product_display_name_vi="Ao thun retro",
        brand_name="Codex",
        base_colour="black",
        base_colour_vi="den",
        material="cotton",
        material_vi="vai cotton",
        fit="oversized",
        fit_vi="form rong",
        season="summer",
        season_vi="mua he",
        product_usage="casual",
        product_usage_vi="hang ngay",
        gender="women",
        gender_vi="nu",
        description="Oversized cotton shirt",
        description_vi="Ao cotton form rong",
        categories=[
            {
                "category_level": "article_type",
                "category_name": "shirt",
                "category_name_vi": "ao so mi",
            },
            {
                "category_level": "master_category",
                "category_name": "topwear",
                "category_name_vi": "do mac tren",
            },
        ],
        option_value=["M", "L"],
        unified_size=["EU-M", "EU-L"],
    )

    document = build_product_embedding_text(item)

    assert document == "\n".join(
        [
            "Product display name: Retro Tee",
            "Vietnamese product display name: Ao thun retro",
            "Brand name: Codex",
            "Base colour: black",
            "Vietnamese base colour: den",
            "Material: cotton",
            "Vietnamese material: vai cotton",
            "Fit: oversized",
            "Vietnamese fit: form rong",
            "Season: summer",
            "Vietnamese season: mua he",
            "Product usage: casual",
            "Vietnamese product usage: hang ngay",
            "Gender: women",
            "Vietnamese gender: nu",
            "Description: Oversized cotton shirt",
            "Vietnamese description: Ao cotton form rong",
            "Category names: shirt, topwear",
            "Vietnamese category names: ao so mi, do mac tren",
            "Category levels: article_type, master_category",
            "Option values: M, L",
            "Unified sizes: EU-M, EU-L",
            "Search attributes: ",
        ]
    )


def test_product_text_document_uses_only_selected_search_attributes() -> None:
    item = ProductIndexItem(
        product_id="P-200",
        product_display_name="Floral Satin Shirt",
        product_display_name_vi="Ao so mi satin hoa",
        image_urls=["https://cdn.test/p-200.jpg"],
        attributes={
            "search_category": "women shirts",
            "search_attributes": "satin, floral",
            "ignored_attribute": "must not be embedded",
        },
        attributes_vi={
            "search_category_vi": "ao so mi nu, ao kieu nu",
            "search_keywords_vi": "ao hoa, ao satin",
            "search_attributes_vi": "satin, hoa tiet hoa",
            "search_use_cases_vi": "must not be embedded",
        },
    )

    document = build_product_embedding_text(item)

    assert (
        "Search attributes: women shirts, ao so mi nu, ao kieu nu, satin, floral, "
        "satin, hoa tiet hoa, ao hoa, ao satin" in document
    )
    assert "must not be embedded" not in document


class _CapturingEncoder:
    """Stand-in for SentenceTransformer that records the texts passed to encode()."""

    def __init__(self) -> None:
        self.captured: list[str] = []

    def encode(self, texts, **_: object):
        import numpy as np

        self.captured.extend(texts)
        return np.array([[0.0, 1.0] for _ in texts])


def _service_with_fake_encoder() -> tuple[SentenceTransformerTextEmbeddingService, _CapturingEncoder]:
    service = SentenceTransformerTextEmbeddingService(settings=Settings(_env_file=None))
    encoder = _CapturingEncoder()
    service._model = encoder
    return service, encoder


def test_embed_query_applies_instruction_prefix() -> None:
    service, encoder = _service_with_fake_encoder()

    service.embed_query("red sneakers")

    assert encoder.captured == [
        "Instruct: Given a shopping search query, retrieve relevant product descriptions\nQuery: red sneakers"
    ]


def test_embed_documents_have_no_prefix() -> None:
    service, encoder = _service_with_fake_encoder()

    service.embed_documents(["a product document"])

    assert encoder.captured == ["a product document"]


def test_embed_text_delegates_to_document_path_without_prefix() -> None:
    service, encoder = _service_with_fake_encoder()

    service.embed_text("indexed document")

    assert encoder.captured == ["indexed document"]
