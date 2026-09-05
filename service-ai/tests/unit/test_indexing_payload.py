from datetime import UTC, datetime
from threading import Barrier, get_ident

import pytest

from ecommerce_search_assistant.schemas.product import ProductIndexItem
from ecommerce_search_assistant.services.embeddings.mock import MockImageEmbeddingService
from ecommerce_search_assistant.services.indexing.product import ProductIndexingService, _product_payload


class _RecordingImageEmbeddingService:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []
        self.delegate = MockImageEmbeddingService(dimensions=8)

    def embed_documents(self, images):
        self.batch_sizes.append(len(images))
        return self.delegate.embed_documents(images)


def test_qdrant_product_payload_builder_uses_spring_contract_keys() -> None:
    item = ProductIndexItem(
        product_id="P-42",
        product_display_name="Black Hoodie",
        product_display_name_vi="Ao hoodie den",
        description="Soft cotton hoodie",
        description_vi="Ao hoodie cotton mem",
        categories=[
            {
                "category_code": "hoodie_sweatshirt",
                "category_level": "article_type",
                "category_name": "Hoodies & Sweatshirts",
                "category_name_vi": "Áo hoodie & áo nỉ",
            }
        ],
        brand_name="Codex",
        base_colour="black",
        base_colour_vi="den",
        material="cotton",
        material_vi="vai cotton",
        fit="regular",
        fit_vi="vua van",
        gender="women",
        gender_vi="nu",
        season="winter",
        season_vi="mua dong",
        product_usage="casual",
        product_usage_vi="hang ngay",
        option_value=["M", "L"],
        unified_size=["EU-M", "EU-L"],
        image_urls=["https://cdn.test/p-42.png"],
        selling_price=399000.00,
        vat=10,
        inventory_count=8,
        available=True,
        active=True,
        updated_at=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
    )

    payload = _product_payload(item)

    assert payload["product_id"] == "P-42"
    assert payload["selling_price"] == 399000.0
    assert payload["vat"] == 10.0
    assert payload["category_names"] == ["Hoodies & Sweatshirts"]
    assert payload["category_names_vi"] == ["Áo hoodie & áo nỉ"]
    assert payload["category_levels"] == ["article_type"]
    assert payload["category_codes"] == ["hoodie_sweatshirt"]
    assert payload["category_keys"] == ["hoodie", "sweatshirt"]
    assert "ao hoodie" in payload["category_aliases"]
    assert payload["source_category_keys"] == ["hoodie", "sweatshirt"]
    assert payload["brand_name"] == "Codex"
    assert payload["brand_key"] == "codex"
    assert payload["base_colour_vi"] == "den"
    assert payload["color_keys"] == ["black"]
    assert payload["material"] == "cotton"
    assert payload["material_keys"] == ["cotton"]
    assert payload["use_case_keys"] == ["casual", "winter"]
    assert payload["option_value"] == ["M", "L"]
    assert payload["unified_size"] == ["EU-M", "EU-L"]
    assert payload["size_keys"] == ["m", "l", "eu-m", "eu-l"]
    assert payload["gender_key"] == "women"
    assert payload["audience_keys"] == ["women"]
    assert payload["normalized_title"] == "black hoodie"
    assert payload["normalized_title_vi"] == "ao hoodie den"
    assert payload["normalized_title_tokens"] == ["ao", "hoodie", "den", "black"]
    assert payload["title_tokens"] == ["ao", "hoodie", "den", "black"]
    assert payload["metadata_schema_version"] == 7
    assert payload["canonicalizer_version"]
    assert payload["inventory_count"] == 8
    assert payload["active"] is True
    assert payload["updated_at"] == "2026-05-13T08:00:00+00:00"
    assert "title" not in payload
    assert "description" not in payload
    assert "categories" not in payload
    assert "image_urls" not in payload
    assert "attributes" not in payload
    assert "product_display_name" not in payload


def test_text_upsert_payload_includes_embedding_text(
    indexing_service: ProductIndexingService,
    fake_qdrant_client,
) -> None:
    item = ProductIndexItem(
        product_id="P-EMB-1",
        product_display_name="Blue Jacket",
        product_display_name_vi="Ao khoac xanh",
        image_urls=[],
    )

    indexing_service.index_products([item])

    text_upserts = [
        upsert
        for upsert in fake_qdrant_client.upserts
        if "text" in upsert["collection_name"]
    ]
    assert text_upserts, "expected a text-collection upsert"
    payload = text_upserts[0]["points"][0].payload
    assert payload["source"] == "text"
    assert "Product display name: Blue Jacket" in payload["embedding_text"]


def test_product_images_are_embedded_in_one_batch_per_product(
    indexing_service: ProductIndexingService,
    fake_qdrant_client,
) -> None:
    recorder = _RecordingImageEmbeddingService()
    indexing_service.image_embedding_service = recorder  # type: ignore[assignment]
    item = ProductIndexItem(
        product_id="P-IMAGE-BATCH",
        product_display_name="Batch images",
        image_urls=[
            "https://assets.test/one.jpg",
            "https://assets.test/two.jpg",
            "https://assets.test/three.jpg",
        ],
    )

    result = indexing_service.index_products([item])

    assert recorder.batch_sizes == [3]
    assert result.image_indexed_count == 3
    image_upserts = [
        upsert for upsert in fake_qdrant_client.upserts if "image" in upsert["collection_name"]
    ]
    assert len(image_upserts) == 1
    assert len(image_upserts[0]["points"]) == 3


def test_product_batch_uses_configured_parallel_workers(
    indexing_service: ProductIndexingService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexing_service.settings = indexing_service.settings.model_copy(
        update={"product_index_workers": 2}
    )
    barrier = Barrier(2)
    worker_threads: set[int] = set()

    def fake_index_product(_product: ProductIndexItem) -> tuple[list, int]:
        worker_threads.add(get_ident())
        barrier.wait(timeout=2)
        return [], 0

    monkeypatch.setattr(indexing_service, "_index_product", fake_index_product)
    products = [
        ProductIndexItem(product_id="P-PARALLEL-1", product_display_name="One"),
        ProductIndexItem(product_id="P-PARALLEL-2", product_display_name="Two"),
    ]

    result = indexing_service.index_products(products)

    assert len(worker_threads) == 2
    assert result.indexed_count == 2
    assert result.failed_count == 0


def test_product_images_are_prepared_with_parallel_download_workers(
    indexing_service: ProductIndexingService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = Barrier(3)
    worker_threads: set[int] = set()

    def fake_prepare_image_crops(
        _product_id: str,
        _image_url: str,
        _image_index: int,
    ) -> tuple[list, list]:
        worker_threads.add(get_ident())
        barrier.wait(timeout=2)
        return [], []

    monkeypatch.setattr(
        indexing_service,
        "_prepare_image_crops",
        fake_prepare_image_crops,
    )
    item = ProductIndexItem(
        product_id="P-PARALLEL-IMAGES",
        product_display_name="Parallel images",
        image_urls=[
            "https://assets.test/one.jpg",
            "https://assets.test/two.jpg",
            "https://assets.test/three.jpg",
        ],
    )

    result = indexing_service.index_products([item])

    assert len(worker_threads) == 3
    assert result.indexed_count == 1
    assert result.failed_count == 0


def test_product_index_item_accepts_localized_spring_contract_payload() -> None:
    item = ProductIndexItem(
        product_id="P-VI-1",
        product_display_name_vi="Ao so mi trang",
        image_urls=[],
    )

    assert item.product_id == "P-VI-1"
    assert item.product_display_name_vi == "Ao so mi trang"
    assert item.model_dump()["product_id"] == "P-VI-1"


def test_product_payload_falls_back_to_full_category_names_for_legacy_contract() -> None:
    item = ProductIndexItem(
        product_id="P-LEGACY-CATEGORY",
        product_display_name="Legacy shirt",
        categories=[
            {
                "category_level": "article_type",
                "category_name": "Shirts & Blouses",
                "category_name_vi": "Áo sơ mi & áo kiểu",
            }
        ],
    )

    payload = _product_payload(item)

    assert payload["category_codes"] == []
    assert payload["category_keys"] == ["shirt", "blouse"]


def test_title_article_type_repairs_conflicting_source_category_for_search() -> None:
    item = ProductIndexItem(
        product_id="113",
        product_display_name="DENIM SHIRT",
        product_display_name_vi="Áo sơ mi denim xanh Zara",
        categories=[{"category_code": "jeans", "category_name": "Jeans"}],
    )

    payload = _product_payload(item)

    assert payload["source_category_keys"] == ["jeans"]
    assert payload["category_keys"] == ["shirt"]


def test_title_tshirt_overrides_conflicting_sweater_source_category() -> None:
    item = ProductIndexItem(
        product_id="982",
        product_display_name="CINNAMOROLL SLUB KNIT T-SHIRT",
        product_display_name_vi="áo thun nữ Cinamoroll họa tiết in hình",
        categories=[
            {
                "category_code": "sweater_cardigan",
                "category_name": "Sweaters & Cardigans",
            }
        ],
    )

    payload = _product_payload(item)

    assert payload["source_category_keys"] == ["sweater", "cardigan"]
    assert payload["category_keys"] == ["tshirt"]
    assert "ao thun" in payload["category_aliases"]
    assert "ao len" not in payload["category_aliases"]

def test_vietnamese_romper_title_preserves_jumpsuit_category() -> None:
    item = ProductIndexItem(
        product_id="488",
        product_display_name="CHECKED PLAYSUIT",
        product_display_name_vi="Dam lien quan mau trang nga va nau caro",
        categories=[
            {
                "category_code": "jumpsuit_romper",
                "category_name": "Jumpsuits & Playsuits",
            }
        ],
    )

    payload = _product_payload(item)

    assert payload["source_category_keys"] == ["jumpsuit", "romper"]
    assert payload["category_keys"] == ["jumpsuit", "romper"]


@pytest.mark.parametrize(
    ("title", "title_vi", "source_code", "expected_key"),
    [
        ("STRIPED JOHNNY COLLAR BLOUSE", "áo blouse sọc", "polo", "blouse"),
        ("CAPE SLEEVE T-SHIRT", "áo thun tay cape", "jacket", "tshirt"),
        ("HIGH NECK MAXI DRESS", "đầm maxi cổ cao", "shirt_blouse", "dress"),
        ("WIDE LEG JEANS", "quần jeans ống rộng", "pants", "jeans"),
        ("LONG STRIPED SKORT", "váy quần dài kẻ sọc", "skirt", "skort"),
        ("SHOULDER PAD GILET", "áo gi lê vai nâng", "t-shirt", "vest"),
        ("POPLIN CROP TOP", "áo crop tay phồng", "t-shirt", "blouse"),
    ],
)
def test_title_article_type_repairs_multiple_conflicting_taxonomy_families(
    title: str,
    title_vi: str,
    source_code: str,
    expected_key: str,
) -> None:
    item = ProductIndexItem(
        product_id="P-CONFLICT",
        product_display_name=title,
        product_display_name_vi=title_vi,
        categories=[{"category_code": source_code, "category_name": source_code}],
    )

    payload = _product_payload(item)

    assert expected_key in payload["category_keys"]


@pytest.mark.parametrize(
    ("title", "title_vi"),
    [
        ("HALTER TOP WITH OPEN BACK", "Áo yếm hở lưng"),
        ("PRINTED TOP", "Áo cổ yếm họa tiết"),
    ],
)
def test_halter_title_is_indexed_with_the_tank_cami_family(
    title: str,
    title_vi: str,
) -> None:
    item = ProductIndexItem(
        product_id="P-HALTER",
        product_display_name=title,
        product_display_name_vi=title_vi,
        categories=[{"category_code": "tank_cami", "category_name": "Tank, Cami & Halter Tops"}],
    )

    payload = _product_payload(item)

    assert set(payload["category_keys"]) == {"tank top", "cami", "halter"}


@pytest.mark.parametrize(
    ("title", "title_vi", "source_code", "expected_key"),
    [
        (
            "SATIN HALTER-NECK BODYSUIT",
            "Bodysuit satin màu đen cổ yếm viền ren",
            "bodysuit",
            "bodysuit",
        ),
        (
            "HALTER-NECK MIDI DRESS",
            "Đầm midi cổ yếm màu trắng ngà",
            "dress",
            "dress",
        ),
    ],
)
def test_product_head_noun_wins_over_halter_neckline(
    title: str,
    title_vi: str,
    source_code: str,
    expected_key: str,
) -> None:
    item = ProductIndexItem(
        product_id="P-HALTER-NECKLINE",
        product_display_name=title,
        product_display_name_vi=title_vi,
        categories=[{"category_code": source_code, "category_name": source_code}],
    )

    payload = _product_payload(item)

    assert payload["category_keys"] == [expected_key]


def test_dark_color_adjective_is_not_misread_as_dress() -> None:
    item = ProductIndexItem(
        product_id="P-DARK-JACKET",
        product_display_name="DARK BROWN JACKET",
        product_display_name_vi="Áo khoác màu nâu đậm hai mặt",
        categories=[{"category_code": "jacket", "category_name": "Jackets"}],
    )

    payload = _product_payload(item)

    assert payload["category_keys"] == ["jacket"]


def test_knitwear_head_noun_wins_over_generic_fashion_top_prefix() -> None:
    item = ProductIndexItem(
        product_id="P-KNIT-TOP",
        product_display_name="KNIT COLOR ORANGE BLOUSE",
        product_display_name_vi="Áo kiểu dệt kim màu cam cổ polo gấu phồng",
        categories=[
            {
                "category_code": "sweater_cardigan",
                "category_name": "Knitwear & Cardigans",
            }
        ],
    )

    payload = _product_payload(item)

    assert payload["category_keys"] == ["sweater", "cardigan"]
    assert "ao kieu" not in payload["category_aliases"]


def test_missing_business_flags_default_to_conservative_inactive_state() -> None:
    item = ProductIndexItem(
        product_id="P-NO-SELLABILITY",
        product_display_name="Unverified product",
    )

    assert item.active is False
    assert item.available is False
