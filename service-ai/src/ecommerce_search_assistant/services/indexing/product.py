from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import logging
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.infrastructure.qdrant import build_qdrant_client
from ecommerce_search_assistant.schemas.indexing import IndexFailure, ProductDeleteResponse, ProductIndexResponse
from ecommerce_search_assistant.schemas.product import ProductIndexItem
from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
from ecommerce_search_assistant.services.cropping.yolo import CropResult, CropService
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)
from ecommerce_search_assistant.services.embeddings.formatting import build_product_embedding_text
from ecommerce_search_assistant.services.embeddings.interfaces import ImageEmbeddingService, TextEmbeddingService
from ecommerce_search_assistant.services.indexing.image_loader import ImageLoadService
from ecommerce_search_assistant.services.search.category_taxonomy import (
    canonicalize_category_codes,
    category_aliases_for_keys,
    category_keys_for_category,
)
from ecommerce_search_assistant.services.search.canonicalization import (
    CANONICALIZER_VERSION,
    METADATA_SCHEMA_VERSION,
    audience_keys_for_gender,
    canonicalize_brand_key,
    catalog_product_color_keys,
    canonicalize_gender_key,
    canonicalize_material_keys,
    canonicalize_size_keys,
    canonicalize_use_case_keys,
)
from ecommerce_search_assistant.services.search.normalization import normalize_query_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _PreparedImageCrop:
    image_url: str
    image_index: int
    crop_index: int
    crop: CropResult


@dataclass
class ProductIndexingService:
    settings: Settings = field(default_factory=get_settings)
    qdrant_client: QdrantClient = field(default_factory=lambda: build_qdrant_client(get_settings()))
    text_embedding_service: TextEmbeddingService = field(default_factory=get_text_embedding_service)
    image_embedding_service: ImageEmbeddingService = field(default_factory=get_image_embedding_service)
    yolo_crop_service: CropService = field(default_factory=get_yolo_crop_service)
    image_loader: ImageLoadService = field(default_factory=ImageLoadService)

    def index_products(self, products: list[ProductIndexItem]) -> ProductIndexResponse:
        if not products:
            return ProductIndexResponse(indexed_count=0, failed_count=0)

        worker_count = min(len(products), self.settings.product_index_workers)
        if worker_count == 1:
            results = [self._index_product(product) for product in products]
        else:
            with ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix="product-index",
            ) as executor:
                results = list(executor.map(self._index_product, products))

        indexed_count = 0
        failed_count = 0
        image_indexed_count = 0
        failures: list[IndexFailure] = []

        for product_failures, product_image_indexed_count in results:
            image_indexed_count += product_image_indexed_count
            product_hard_failures = [
                failure
                for failure in product_failures
                if failure.stage in {"text_embedding", "text_upsert", "image_embedding", "image_upsert"}
                and failure.image_url is None
            ]
            failures.extend(product_failures)
            if product_hard_failures:
                failed_count += 1
            else:
                indexed_count += 1

        return ProductIndexResponse(
            indexed_count=indexed_count,
            failed_count=failed_count,
            image_indexed_count=image_indexed_count,
            image_failed_count=sum(1 for failure in failures if failure.image_url is not None),
            failures=failures,
        )

    def update_product(self, product: ProductIndexItem) -> ProductIndexResponse:
        delete_failure = self._delete_product_vectors(product.product_id)
        if delete_failure is not None:
            return ProductIndexResponse(
                indexed_count=0,
                failed_count=1,
                failures=[delete_failure],
            )
        return self.index_products([product])

    def reindex_products(self, products: list[ProductIndexItem]) -> ProductIndexResponse:
        indexed_count = 0
        failed_count = 0
        image_indexed_count = 0
        failures: list[IndexFailure] = []

        for product in products:
            delete_failure = self._delete_product_vectors(product.product_id)
            if delete_failure is not None:
                failures.append(delete_failure)
                failed_count += 1
                continue

            result = self.index_products([product])
            indexed_count += result.indexed_count
            failed_count += result.failed_count
            image_indexed_count += result.image_indexed_count
            failures.extend(result.failures)

        return ProductIndexResponse(
            indexed_count=indexed_count,
            failed_count=failed_count,
            image_indexed_count=image_indexed_count,
            image_failed_count=sum(1 for failure in failures if failure.image_url is not None),
            failures=failures,
        )

    def delete_product(self, product_id: str) -> ProductDeleteResponse:
        failure = self._delete_product_vectors(product_id)
        if failure is not None:
            raise RuntimeError(failure.reason)
        return ProductDeleteResponse(product_id=product_id)

    def _index_product(self, product: ProductIndexItem) -> tuple[list[IndexFailure], int]:
        failures: list[IndexFailure] = []
        embedding_text = build_product_embedding_text(product)
        try:
            text_vector = self.text_embedding_service.embed_text(embedding_text)
        except Exception as exc:
            logger.exception("product_text_index_failed", extra={"product_id": product.product_id})
            return [
                IndexFailure(
                    product_id=product.product_id,
                    stage="text_embedding",
                    reason=str(exc),
                )
            ], 0

        try:
            self._upsert_text_point(product, text_vector, embedding_text)
        except Exception as exc:
            logger.exception("product_text_upsert_failed", extra={"product_id": product.product_id})
            return [
                IndexFailure(
                    product_id=product.product_id,
                    stage="text_upsert",
                    reason=str(exc),
                )
            ], 0

        image_inputs = list(enumerate(product.image_urls))
        image_worker_count = min(
            len(image_inputs),
            self.settings.product_image_download_workers,
        )
        if image_worker_count <= 1:
            prepared_images = [
                self._prepare_image_crops(product.product_id, image_url, image_index)
                for image_index, image_url in image_inputs
            ]
        else:
            with ThreadPoolExecutor(
                max_workers=image_worker_count,
                thread_name_prefix="product-image-download",
            ) as executor:
                prepared_images = list(
                    executor.map(
                        lambda image_input: self._prepare_image_crops(
                            product.product_id,
                            image_input[1],
                            image_input[0],
                        ),
                        image_inputs,
                    )
                )

        prepared_crops: list[_PreparedImageCrop] = []
        for image_failures, crops in prepared_images:
            failures.extend(image_failures)
            prepared_crops.extend(crops)

        image_points: list[models.PointStruct] = []
        if prepared_crops:
            try:
                vectors = self.image_embedding_service.embed_documents(
                    [prepared.crop.image for prepared in prepared_crops]
                )
                image_points = [
                    self._build_image_point(
                        product,
                        prepared.image_url,
                        prepared.image_index,
                        prepared.crop_index,
                        prepared.crop,
                        vector,
                    )
                    for prepared, vector in zip(prepared_crops, vectors, strict=True)
                ]
            except Exception as exc:
                logger.exception(
                    "product_image_embedding_failed",
                    extra={"product_id": product.product_id},
                )
                failed_image_urls = dict.fromkeys(
                    prepared.image_url for prepared in prepared_crops
                )
                failures.extend(
                    IndexFailure(
                        product_id=product.product_id,
                        image_url=image_url,
                        stage="image_embedding",
                        reason=str(exc),
                    )
                    for image_url in failed_image_urls
                )

        image_indexed_count = 0
        if image_points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.settings.qdrant_image_collection,
                    points=image_points,
                    wait=True,
                )
                image_indexed_count = len(image_points)
            except Exception as exc:
                logger.exception("product_image_upsert_failed", extra={"product_id": product.product_id})
                failures.append(
                    IndexFailure(
                        product_id=product.product_id,
                        stage="image_upsert",
                        reason=str(exc),
                    )
                )

        return failures, image_indexed_count

    def _prepare_image_crops(
        self,
        product_id: str,
        image_url: str,
        image_index: int,
    ) -> tuple[list[IndexFailure], list[_PreparedImageCrop]]:
        try:
            image = self.image_loader.load_from_url(image_url)
        except Exception as exc:
            return [
                IndexFailure(
                    product_id=product_id,
                    image_url=image_url,
                    stage="image_download",
                    reason=str(exc),
                )
            ], []

        try:
            crops = self.yolo_crop_service.detect_and_crop(image)
        except Exception as exc:
            return [
                IndexFailure(
                    product_id=product_id,
                    image_url=image_url,
                    stage="yolo_crop",
                    reason=str(exc),
                )
            ], []

        prepared_crops = [
            _PreparedImageCrop(
                image_url=image_url,
                image_index=image_index,
                crop_index=crop_index,
                crop=crop,
            )
            for crop_index, crop in enumerate(crops)
        ]
        return [], prepared_crops

    def _upsert_text_point(self, product: ProductIndexItem, vector: list[float], embedding_text: str) -> None:
        self.qdrant_client.upsert(
            collection_name=self.settings.qdrant_text_collection,
            points=[
                models.PointStruct(
                    id=_point_id("text", product.product_id),
                    vector=vector,
                    payload={
                        **_product_payload(product),
                        "source": "text",
                        "embedding_text": embedding_text,
                    },
                )
            ],
            wait=True,
        )

    def _build_image_point(
        self,
        product: ProductIndexItem,
        image_url: str,
        image_index: int,
        crop_index: int,
        crop: CropResult,
        vector: list[float],
    ) -> models.PointStruct:
        image_id = f"{product.product_id}:{image_index}:{crop_index}"
        payload = {
            **_product_payload(product),
            "source": "image",
            "image_id": image_id,
            "image_url": image_url,
            "image_index": image_index,
            "crop_index": crop_index,
            "bbox": list(crop.bbox),
            "confidence": crop.confidence,
            "class_id": crop.class_id,
            "is_fallback_crop": crop.is_fallback,
        }
        return models.PointStruct(
            id=_point_id("image", product.product_id, image_url, str(crop_index)),
            vector=vector,
            payload=payload,
        )

    def _delete_product_vectors(self, product_id: str) -> IndexFailure | None:
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="product_id",
                        match=models.MatchValue(value=product_id),
                    )
                ]
            )
        )
        try:
            for collection_name in (
                self.settings.qdrant_text_collection,
                self.settings.qdrant_image_collection,
            ):
                self.qdrant_client.delete(
                    collection_name=collection_name,
                    points_selector=selector,
                    wait=True,
                )
        except Exception as exc:
            logger.exception("product_vectors_delete_failed", extra={"product_id": product_id})
            return IndexFailure(product_id=product_id, stage="delete", reason=str(exc))
        return None


def _point_id(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, ":".join(parts)))


def _product_payload(product: ProductIndexItem) -> dict[str, Any]:
    category_codes = canonicalize_category_codes(category.code for category in product.categories)
    category_names = [category.name for category in product.categories if category.name]
    category_names_vi = [category.name_vi for category in product.categories if category.name_vi]
    category_levels = [category.level for category in product.categories if category.level]
    source_category_keys = list(
        dict.fromkeys(
            key
            for category in product.categories
            for key in category_keys_for_category(category.code, category.name, category.name_vi)
        )
    )
    gender_key = canonicalize_gender_key(product.gender) or canonicalize_gender_key(product.gender_vi)
    normalized_title = normalize_query_text(product.product_display_name)
    normalized_title_vi = normalize_query_text(product.product_display_name_vi)
    title_category_keys = _title_article_type_keys(normalized_title, normalized_title_vi)
    category_keys = _resolve_article_type_category_keys(
        source_category_keys,
        title_category_keys,
    )
    normalized_title_tokens = list(
        dict.fromkeys(
            token
            for title in (normalized_title_vi, normalized_title)
            for token in title.split()
            if token
        )
    )

    return {
        "product_id": product.product_id,
        "brand_name": product.brand_name,
        "base_colour": product.base_colour,
        "base_colour_vi": product.base_colour_vi,
        "material": product.material,
        "material_vi": product.material_vi,
        "fit": product.fit,
        "fit_vi": product.fit_vi,
        "gender": product.gender,
        "gender_vi": product.gender_vi,
        "season": product.season,
        "season_vi": product.season_vi,
        "product_usage": product.product_usage,
        "product_usage_vi": product.product_usage_vi,
        "category_names": category_names,
        "category_names_vi": category_names_vi,
        "category_levels": category_levels,
        "category_codes": category_codes,
        "category_keys": category_keys,
        "category_aliases": category_aliases_for_keys(category_keys),
        "source_category_keys": source_category_keys,
        "brand_key": canonicalize_brand_key(product.brand_name),
        "color_keys": catalog_product_color_keys(
            product.base_colour, product.base_colour_vi
        ),
        "material_keys": canonicalize_material_keys([product.material, product.material_vi]),
        "use_case_keys": canonicalize_use_case_keys(
            [
                product.product_usage,
                product.product_usage_vi,
                product.season,
                product.season_vi,
            ]
        ),
        "size_keys": canonicalize_size_keys([*product.option_value, *product.unified_size]),
        "gender_key": gender_key,
        "audience_keys": audience_keys_for_gender(gender_key),
        "normalized_title": normalized_title or None,
        "normalized_title_vi": normalized_title_vi or None,
        "normalized_title_tokens": normalized_title_tokens,
        "title_tokens": normalized_title_tokens,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "canonicalizer_version": CANONICALIZER_VERSION,
        "option_value": list(product.option_value),
        "unified_size": list(product.unified_size),
        "inventory_count": product.inventory_count,
        "available": product.available,
        "active": product.active,
        "selling_price": product.selling_price,
        "vat": product.vat,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


def _title_article_type_keys(normalized_title: str, normalized_title_vi: str) -> list[str]:
    """Add only high-precision article-type hints; never infer accessory words in descriptions."""
    vi_title = f" {normalized_title_vi} "
    english_title = f" {normalized_title} "
    if normalized_title_vi.startswith(("dam jumpsuit ", "jumpsuit ", "dam lien quan ")):
        return ["jumpsuit", "romper"]
    if normalized_title_vi.startswith(("dam ", "vay lien ")):
        return ["dress"]
    vi_rules = (
        ((" ao bodysuit ", " ao body ", " bodysuit "), ["bodysuit"]),
        ((" dam jumpsuit ", " jumpsuit "), ["jumpsuit", "romper"]),
        ((" vay quan ", " quan vay "), ["skort"]),
        ((" ao so mi ",), ["shirt"]),
        # ``áo kiểu`` is sometimes a generic merchandising prefix before the
        # real article type. Prefer the more specific knitwear head noun so the
        # title repair does not overwrite a correct sweater/cardigan source
        # category with the broad blouse category.
        ((" ao kieu det kim ", " ao det kim "), ["sweater", "cardigan"]),
        ((" ao blouse ", " ao kieu ", " ao crop "), ["blouse"]),
        ((" ao thun ", " ao phong "), ["tshirt"]),
        ((" ao cardigan ",), ["cardigan"]),
        ((" ao hoodie ",), ["hoodie", "sweatshirt"]),
        ((" ao blazer ",), ["blazer"]),
        ((" ao gi le ", " ao gile ", " ghi le "), ["vest"]),
        ((" ao khoac ",), ["jacket"]),
        ((" ao polo ",), ["polo"]),
        ((" ao yem ", " co yem "), ["halter"]),
        ((" ao hai day ", " ao ba lo "), ["cami", "tank top"]),
        ((" ao len ",), ["sweater"]),
        ((" quan jeans ", " quan jean ", " quan bo "), ["jeans"]),
        ((" quan short ", " bermuda "), ["shorts"]),
        ((" quan legging ",), ["leggings"]),
        ((" quan culotte ", " quan dai ", " quan tay "), ["pants"]),
        ((" chan vay ",), ["skirt"]),
    )
    english_rules = (
        ((" bodysuit ", " body suit "), ["bodysuit"]),
        ((" jumpsuit ", " romper "), ["jumpsuit", "romper"]),
        ((" skort ",), ["skort"]),
        ((" cardigan ",), ["cardigan"]),
        ((" hoodie ", " sweatshirt "), ["hoodie", "sweatshirt"]),
        ((" blazer ",), ["blazer"]),
        ((" jacket ", " coat "), ["jacket"]),
        ((" blouse ",), ["blouse"]),
        ((" t shirt ", " tee "), ["tshirt"]),
        ((" polo shirt ",), ["polo"]),
        ((" shirt ",), ["shirt"]),
        ((" halter top ",), ["halter"]),
        ((" camisole ", " tank top "), ["cami", "tank top"]),
        ((" sweater ", " knitwear "), ["sweater"]),
        ((" jeans ", " jean "), ["jeans"]),
        ((" shorts ", " bermuda "), ["shorts"]),
        ((" leggings ", " legging "), ["leggings"]),
        ((" culotte ", " trousers ", " pants "), ["pants"]),
        ((" skirt ",), ["skirt"]),
        ((" dress ",), ["dress"]),
    )
    for title, rules in ((vi_title, vi_rules), (english_title, english_rules)):
        for phrases, keys in rules:
            if any(phrase in title for phrase in phrases):
                return keys
    return []


def _resolve_article_type_category_keys(
    source_category_keys: list[str],
    title_category_keys: list[str],
) -> list[str]:
    """Prefer high-precision title evidence when source taxonomy contradicts it."""
    normalized_source_keys = list(dict.fromkeys(source_category_keys))
    normalized_title_keys = list(dict.fromkeys(title_category_keys))
    if not normalized_title_keys:
        return normalized_source_keys
    if set(normalized_source_keys).intersection(normalized_title_keys):
        return list(dict.fromkeys([*normalized_source_keys, *normalized_title_keys]))
    return normalized_title_keys
