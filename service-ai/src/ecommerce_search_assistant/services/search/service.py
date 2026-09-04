from __future__ import annotations

from base64 import b64decode
from binascii import Error as BinasciiError
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from hashlib import sha256
from io import BytesIO
import logging
import math
from threading import Lock
from time import monotonic
import unicodedata
from typing import Any, Iterable

from PIL import Image, ImageOps, UnidentifiedImageError
from qdrant_client import QdrantClient, models

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.core.metrics import search_metrics
from ecommerce_search_assistant.infrastructure.qdrant import build_qdrant_client
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.schemas.search import (
    AutoSearchRequest,
    HybridSearchRequest,
    ImageBoundingBox,
    ImageDetectionBox,
    ImageDetectionRequest,
    ImageDetectionResponse,
    ImageSearchRequest,
    SearchFilter,
    SearchResponse,
    SearchResultItem,
    TextSearchRequest,
)
from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
from ecommerce_search_assistant.services.cropping.yolo import CropResult, CropService
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)
from ecommerce_search_assistant.services.embeddings.interfaces import ImageEmbeddingService, TextEmbeddingService
from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.llm.interfaces import LlmService
from ecommerce_search_assistant.services.reranking.factory import get_rerank_service
from ecommerce_search_assistant.services.reranking.interfaces import RerankService
from ecommerce_search_assistant.services.search.filtering import (
    CatalogMetadata,
    QueryAnalysis,
    analyze_query,
    detect_catalog_feasibility_rejection,
    explicit_query_filters,
    merge_missing_filters,
    merge_filters,
    normalize_filter_values,
    normalize_gender,
    sanitize_llm_attribute_filters,
)
from ecommerce_search_assistant.services.search.canonicalization import (
    CANONICALIZER_VERSION,
    METADATA_SCHEMA_VERSION,
    canonicalize_brand_key,
    canonicalize_color_keys,
    color_filter_keys,
    canonicalize_gender_key,
    canonicalize_material_keys,
    canonicalize_size_keys,
    canonicalize_use_case_keys,
    is_exact_color_shade,
)
from ecommerce_search_assistant.services.search.category_taxonomy import (
    category_display_name_vi,
    category_filter_keys,
)
from ecommerce_search_assistant.services.search.constraints import (
    ResolvedSearchConstraints,
    resolve_search_constraints,
)
from ecommerce_search_assistant.services.search.normalization import contains_token, normalize_query_text
from ecommerce_search_assistant.services.search.routing import SearchRoute, decide_search_route

logger = logging.getLogger(__name__)

_CATALOG_PRODUCT_TOKENS = {
    "ao",
    "blouse",
    "bodysuit",
    "cardigan",
    "croptop",
    "dam",
    "dress",
    "hoodie",
    "jumpsuit",
    "legging",
    "polo",
    "quan",
    "shirt",
    "short",
    "skirt",
    "thun",
    "vay",
}
_GENERIC_RANKING_TOKENS = {
    "ao",
    "co",
    "cua",
    "dai",
    "de",
    "giup",
    "hang",
    "mac",
    "mau",
    "minh",
    "muon",
    "nam",
    "ngan",
    "ngay",
    "nu",
    "quan",
    "san",
    "pham",
    "tay",
    "tim",
    "vay",
}


def _should_use_text_fast_path(analysis: QueryAnalysis, settings: Settings) -> bool:
    if not settings.text_llm_fast_path_enabled:
        return False
    if analysis.intent not in {"search_product", "recommend_product"}:
        return False
    if any(warning.startswith("hard_conflict:") for warning in analysis.warnings):
        return False
    tokens = set(analysis.corrected_query.split())
    if len(tokens) < settings.text_llm_fast_path_min_tokens:
        return False
    return bool(analysis.filters.category or tokens & _CATALOG_PRODUCT_TOKENS)


def _out_of_catalog_warnings(warnings: Iterable[str]) -> list[str]:
    return [
        warning
        for warning in warnings
        if warning.startswith("invalid_") or warning == "price_outside_catalog"
    ]


def _catalog_has_lexical_evidence(query: str, catalog: CatalogMetadata) -> bool:
    query_tokens = {
        token
        for token in normalize_query_text(query).split()
        if len(token) > 1 and token not in _GENERIC_RANKING_TOKENS
    }
    if len(query_tokens) < 2:
        return False
    for title in catalog.normalized_titles:
        title_tokens = set(title.split())
        if len(query_tokens.intersection(title_tokens)) / len(query_tokens) >= 0.6:
            return True
    return False


def _should_reject_out_of_catalog(
    *,
    query: str,
    warnings: Iterable[str],
    catalog: CatalogMetadata,
) -> bool:
    blocking_warnings = _out_of_catalog_warnings(warnings)
    if not blocking_warnings:
        return False
    if any(
        warning in {"invalid_brand", "price_outside_catalog"}
        for warning in blocking_warnings
    ):
        return True
    return not _catalog_has_lexical_evidence(query, catalog)


class SearchTopKExceededError(ValueError):
    def __init__(self, requested: int, maximum: int) -> None:
        self.requested = requested
        self.maximum = maximum
        super().__init__(f"top_k must be less than or equal to MAX_SEARCH_TOP_K={maximum}")


@dataclass
class _Candidate:
    product_id: str
    text_similarity: float = 0.0
    image_similarity: float = 0.0
    embedding_text: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    present_in_text: bool = False
    present_in_image: bool = False


@dataclass(frozen=True)
class CatalogCategoryCount:
    code: str
    name_vi: str
    count: int


@dataclass
class SearchService:
    settings: Settings = field(default_factory=get_settings)
    qdrant_client: QdrantClient = field(default_factory=lambda: build_qdrant_client(get_settings()))
    text_embedding_service: TextEmbeddingService = field(default_factory=get_text_embedding_service)
    image_embedding_service: ImageEmbeddingService = field(default_factory=get_image_embedding_service)
    yolo_crop_service: CropService = field(default_factory=get_yolo_crop_service)
    llm_service: LlmService = field(default_factory=get_llm_service)
    rerank_service: RerankService = field(default_factory=get_rerank_service)
    _catalog_metadata_cache: CatalogMetadata | None = field(default=None, init=False, repr=False)
    _catalog_metadata_loaded_at: float = field(default=0.0, init=False, repr=False)
    _query_analysis_cache: OrderedDict[str, QueryAnalysis] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )
    _llm_analysis_cache: OrderedDict[str, tuple[float, Any]] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )
    _image_embedding_cache: OrderedDict[str, tuple[float, list[float]]] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )
    _cache_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def catalog_category_counts(self) -> list[CatalogCategoryCount]:
        response = self.qdrant_client.facet(
            collection_name=self.settings.qdrant_text_collection,
            key="category_codes",
            facet_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="active",
                        match=models.MatchValue(value=True),
                    ),
                    models.FieldCondition(
                        key="available",
                        match=models.MatchValue(value=True),
                    ),
                ]
            ),
            limit=100,
            exact=True,
        )
        categories = [
            CatalogCategoryCount(
                code=str(hit.value),
                name_vi=category_display_name_vi(str(hit.value)),
                count=int(hit.count),
            )
            for hit in response.hits
            if str(hit.value).strip() and int(hit.count) > 0
        ]
        return sorted(categories, key=lambda item: (-item.count, item.name_vi.casefold()))

    def resolve_catalog_title_ids(
        self,
        titles: Iterable[str],
        *,
        min_similarity: float = 0.88,
    ) -> dict[str, list[str]]:
        """Resolve exact/near-exact catalog titles without an embedding call."""
        metadata = self._catalog_metadata()
        title_map = metadata.title_product_ids
        resolved: dict[str, list[str]] = {}
        for raw_title in titles:
            title = _normalize_text(raw_title).strip()
            if not title:
                resolved[str(raw_title)] = []
                continue
            exact_ids = title_map.get(title)
            if exact_ids:
                resolved[str(raw_title)] = list(exact_ids)
                continue

            ranked = sorted(
                (
                    (SequenceMatcher(None, title, candidate).ratio(), candidate)
                    for candidate in title_map
                ),
                reverse=True,
            )
            if not ranked or ranked[0][0] < min_similarity:
                resolved[str(raw_title)] = []
                continue
            # Reject ambiguous fuzzy matches instead of silently binding the
            # question to a neighboring product title.
            if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.03:
                resolved[str(raw_title)] = []
                continue
            resolved[str(raw_title)] = list(title_map[ranked[0][1]])
        return resolved

    def resolve_exact_catalog_title_ids(
        self,
        titles: Iterable[str],
    ) -> dict[str, list[str]]:
        """Resolve only normalized exact titles for high-stakes attribute queries."""
        title_map = self._catalog_metadata().title_product_ids
        return {
            str(raw_title): list(title_map.get(_normalize_text(raw_title).strip(), ()))
            for raw_title in titles
        }

    def resolve_catalog_identifier_ids(
        self,
        identifiers: Iterable[str],
    ) -> dict[str, list[str]]:
        """Resolve product IDs exactly; unknown external-style codes stay unresolved."""
        known_ids = set(self._catalog_metadata().product_filter_payloads)
        resolved: dict[str, list[str]] = {}
        for raw_identifier in identifiers:
            identifier = str(raw_identifier).strip()
            canonical = identifier if identifier in known_ids else ""
            resolved[str(raw_identifier)] = [canonical] if canonical else []
        return resolved

    def filter_catalog_product_ids(
        self,
        product_ids: Iterable[str],
        filters: SearchFilter | None,
    ) -> list[str]:
        """Apply a follow-up filter to the previous candidate set without embedding."""
        if filters is None or not filters.model_dump(exclude_none=True):
            return list(dict.fromkeys(str(product_id) for product_id in product_ids))
        payloads = self._catalog_metadata().product_filter_payloads
        return [
            product_id
            for product_id in dict.fromkeys(str(value) for value in product_ids)
            if product_id in payloads
            and _inferred_filter_match_ratio(
                dict(payloads[product_id]),
                filters,
            )
            >= 0.999
        ]

    def search_text(self, request: TextSearchRequest) -> SearchResponse:
        started_at = monotonic()
        catalog_metadata = self._catalog_metadata()
        analysis = analyze_query(
            request.query,
            catalog_metadata,
            typo_correction_enabled=self.settings.text_typo_correction_enabled,
        )
        analyzed_at = monotonic()
        out_of_catalog_warnings = _out_of_catalog_warnings(analysis.warnings)
        rejection_reason = None
        if self.settings.text_out_of_catalog_rejection_enabled and request.filters is None:
            rejection_reason = detect_catalog_feasibility_rejection(
                request.query,
                catalog_metadata,
            )
            if rejection_reason is None and _should_reject_out_of_catalog(
                query=request.query,
                warnings=out_of_catalog_warnings,
                catalog=catalog_metadata,
            ):
                rejection_reason = "invalid_catalog_constraint"
        if rejection_reason is not None:
            response = _response(
                analysis.semantic_query or analysis.corrected_query or request.query,
                analysis.filters if _has_user_filters(analysis.filters) else None,
                [],
            )
            total_ms = (monotonic() - started_at) * 1000
            search_metrics.observe_text_search(
                timings_ms={
                    "analyze_ms": (analyzed_at - started_at) * 1000,
                    "llm_ms": 0.0,
                    "embed_ms": 0.0,
                    "qdrant_ms": 0.0,
                    "score_ms": 0.0,
                    "rerank_ms": 0.0,
                },
                total_ms=total_ms,
                llm_used=False,
                recovery_triggered=False,
                result_count=0,
                rejection_reason=rejection_reason,
            )
            logger.info(
                "text_search_rejected reason=%s warnings=%s total=%.1fms",
                rejection_reason,
                out_of_catalog_warnings,
                total_ms,
            )
            return response
        llm_used = not _should_use_text_fast_path(analysis, self.settings)
        understood = (
            self._understand_query_cached(request.query, locale="vi-VN")
            if llm_used
            else None
        )
        llm_at = monotonic()
        rewritten_query = (
            understood.rewritten_query
            if understood is not None and understood.rewritten_query
            else analysis.semantic_query or analysis.corrected_query or request.query
        )
        llm_filters = sanitize_llm_attribute_filters(
            understood.filters if understood is not None else None,
            analysis.filters,
        )
        inferred_filters = merge_missing_filters(analysis.filters, llm_filters)
        filters = merge_filters(inferred_filters, request.filters)
        constraints = None
        if self.settings.text_inferred_filters_soft_enabled:
            raw_match_sources = analysis.metadata.get("match_sources", {})
            match_sources = raw_match_sources if isinstance(raw_match_sources, dict) else {}
            constraints = resolve_search_constraints(
                rule_filters=analysis.filters,
                llm_filters=llm_filters,
                explicit_filters=request.filters,
                confidences=analysis.confidences,
                match_sources={str(key): str(value) for key, value in match_sources.items()},
                category_ambiguous=any(
                    warning in {"ambiguous_category", "ambiguous_fuzzy_match"}
                    for warning in analysis.warnings
                ),
                allow_category_hard=True,
                allow_color_hard=self.settings.text_trusted_color_hard_filter_enabled,
            )
        response, timings = self.search_text_prepared(
            rewritten_query=rewritten_query,
            filters=filters,
            top_k=request.top_k,
            embedding_query=analysis.catalog_title_query or analysis.corrected_query or request.query,
            constraints=constraints,
        )
        total_ms = (monotonic() - started_at) * 1000
        timings["analyze_ms"] = (analyzed_at - started_at) * 1000
        timings["llm_ms"] = (llm_at - analyzed_at) * 1000
        search_metrics.observe_text_search(
            timings_ms=timings,
            total_ms=total_ms,
            llm_used=llm_used,
            recovery_triggered=bool(timings.get("recovery_triggered")),
            result_count=len(response.results),
            typo_correction_count=sum(
                warning.startswith("spell_corrected:")
                for warning in analysis.warnings
            ),
            category_match_type=analysis.category_match_type,
            category_filter_relaxed=bool(timings.get("category_filter_relaxed")),
            recovery_rescued_top5=bool(timings.get("recovery_rescued_top5")),
            top1_lexical_coverage=timings.get("top1_lexical_coverage"),
        )
        logger.info(
            "text_search_latency analyze=%.1fms llm=%.1fms embed=%.1fms qdrant=%.1fms score=%.1fms "
            "rerank=%.1fms total=%.1fms explicit_filters=%d inferred_filters=%d hard_filters=%d "
            "soft_filters=%d recovery=%s llm_used=%s collection=%s metadata_schema_version=%d",
            (analyzed_at - started_at) * 1000,
            (llm_at - analyzed_at) * 1000,
            timings["embed_ms"],
            timings["qdrant_ms"],
            timings["score_ms"],
            timings["rerank_ms"],
            total_ms,
            len(request.filters.model_dump(exclude_none=True)) if request.filters else 0,
            len(inferred_filters.model_dump(exclude_none=True)) if inferred_filters else 0,
            (
                len(constraints.hard_filters.model_dump(exclude_none=True))
                if constraints and constraints.hard_filters
                else 0
            ),
            (
                len(constraints.soft_filters.model_dump(exclude_none=True))
                if constraints and constraints.soft_filters
                else 0
            ),
            bool(timings.get("recovery_triggered")),
            llm_used,
            self.settings.qdrant_text_collection,
            METADATA_SCHEMA_VERSION,
        )
        return response

    def search_auto(self, request: AutoSearchRequest) -> SearchResponse:
        decision = decide_search_route(
            query=request.query,
            has_image=request.image is not None,
            request_filters=request.filters,
            llm_service=self.llm_service,
            locale=request.locale,
        )
        if decision.route == "text_search":
            response, _timings = self.search_text_prepared(
                rewritten_query=decision.rewritten_query or request.query or "",
                filters=decision.filters,
                top_k=request.top_k,
            )
            return _response_with_route(response, decision.route)
        if decision.route == "image_search" and request.image is not None:
            response = self.search_image(
                ImageSearchRequest(
                    image=request.image,
                    crop_box=request.crop_box,
                    filters=decision.filters,
                    top_k=request.top_k,
                )
            )
            return _response_with_route(response, decision.route, rewritten_query=decision.rewritten_query)
        if decision.route == "hybrid_search":
            response = self.search_hybrid_prepared(
                rewritten_query=decision.rewritten_query or request.query,
                image=request.image,
                crop_box=request.crop_box,
                filters=decision.filters,
                top_k=request.top_k,
            )
            return _response_with_route(response, decision.route)
        return SearchResponse(
            rewritten_query=decision.rewritten_query or request.query,
            filters=decision.filters if _has_user_filters(decision.filters) else None,
            route=decision.route,
        )

    def search_text_prepared(
        self,
        *,
        rewritten_query: str,
        filters: SearchFilter | None,
        top_k: int | None = None,
        embedding_query: str | None = None,
        constraints: ResolvedSearchConstraints | None = None,
    ) -> tuple[SearchResponse, dict[str, float]]:
        started_at = monotonic()
        output_top_k = _resolve_top_k(top_k, self.settings.text_top_k, self.settings)
        candidate_limit = min(
            self.settings.max_search_top_k,
            max(
                output_top_k,
                self.settings.text_candidate_pool_size,
                self.settings.rerank_top_k if self.settings.rerank_enabled else 0,
            ),
        )
        semantic_query = embedding_query or rewritten_query
        vector = self.text_embedding_service.embed_query(semantic_query)
        embedded_at = monotonic()
        hard_filters = constraints.hard_filters if constraints is not None else filters
        exact_title_filters = (
            constraints.explicit_hard_filters
            if constraints is not None
            else hard_filters
        )
        legacy_soft_attributes = (
            constraints is None and self.settings.text_soft_attribute_boost_enabled
        )
        exact_points: list[_ScoredPoint] = []
        normalized_exact_query = normalize_query_text(semantic_query)
        if self.settings.text_lexical_fusion_enabled and normalized_exact_query:
            exact_points = self._query_collection(
                collection_name=self.settings.qdrant_text_collection,
                vector=vector,
                # Inferred attributes extracted from a literal title must not
                # discard its exact lexical match. Explicit API filters remain
                # authoritative for this branch.
                filters=exact_title_filters,
                limit=output_top_k,
                soft_attributes=legacy_soft_attributes,
                exact_title=normalized_exact_query,
            )
        points = self._query_collection(
            collection_name=self.settings.qdrant_text_collection,
            vector=vector,
            filters=hard_filters,
            limit=candidate_limit,
            soft_attributes=legacy_soft_attributes,
        )
        points = exact_points + points
        primary_queried_at = monotonic()
        primary_points = list(points)
        primary_ids = {point.product_id for point in _dedupe_by_product(primary_points)}
        recovery_triggered = False
        category_filter_relaxed = False
        recovery_points: list[_ScoredPoint] = []
        recovery_reasons = _text_recovery_reasons(
            primary_points,
            semantic_query,
            constraints,
            self.settings,
        )
        primary_qdrant_ms = (primary_queried_at - embedded_at) * 1000
        recovery_budget_available = (
            self.settings.text_filter_recovery_time_budget_ms > 0
            and primary_qdrant_ms
            < self.settings.text_filter_recovery_time_budget_ms
        )
        if (
            constraints is not None
            and self.settings.text_filter_recovery_enabled
            and constraints.has_recoverable_inferred_hard_filters
            and recovery_reasons
            and recovery_budget_available
        ):
            recovery_triggered = True
            before_count = len(primary_ids)
            recovery_points = self._query_collection(
                collection_name=self.settings.qdrant_text_collection,
                vector=vector,
                filters=constraints.recovery_filters,
                limit=candidate_limit,
                soft_attributes=False,
            )
            if normalized_exact_query:
                recovery_points = self._query_collection(
                    collection_name=self.settings.qdrant_text_collection,
                    vector=vector,
                    filters=exact_title_filters,
                    limit=output_top_k,
                    soft_attributes=False,
                    exact_title=normalized_exact_query,
                ) + recovery_points
            points = [*primary_points, *recovery_points]
            category_filter_relaxed = any(
                item.field == "category"
                and item.mode == "hard"
                and item.source != "explicit"
                for item in constraints.constraints
            )
            logger.info(
                "search_recovery_triggered reasons=%s before=%d after=%d relaxed=%s",
                recovery_reasons,
                before_count,
                len(_dedupe_by_product(points)),
                [
                    item.field
                    for item in constraints.constraints
                    if item.mode == "hard" and item.source != "explicit"
                ],
            )
        queried_at = monotonic()
        deduped = _dedupe_by_product(points)
        ranking_filters = constraints.soft_filters if constraints is not None else filters
        results: list[SearchResultItem] = []
        for point in deduped:
            components = _text_score_components(
                point.payload,
                ranking_filters,
                self.settings,
                query=semantic_query,
            )
            results.append(
                SearchResultItem(
                    product_id=point.product_id,
                    score=point.score + sum(components.values()),
                    source="text",
                )
            )
            logger.debug(
                "text_search_score product_id=%s vector=%.6f components=%s",
                point.product_id,
                point.score,
                components,
            )
        results.sort(key=lambda item: item.score, reverse=True)
        scored_at = monotonic()
        results = self._rerank(semantic_query, results, _content_by_product(deduped))
        reranked_at = monotonic()
        payload_by_product = {
            point.product_id: point.payload
            for point in deduped
        }
        results = _filter_requested_color_shade(
            results,
            payload_by_product,
            query=semantic_query,
        )
        top_ids = {item.product_id for item in results[:output_top_k]}
        recovered_only_ids = {
            point.product_id for point in recovery_points
        } - primary_ids
        recovery_rescued_top5 = bool(top_ids.intersection(recovered_only_ids))
        top1_lexical_coverage = (
            _title_lexical_coverage(
                semantic_query,
                payload_by_product.get(results[0].product_id, {}),
            )
            if results
            else 0.0
        )
        response_filters = constraints.response_filters if constraints is not None else filters
        return _response(rewritten_query, response_filters, results[:output_top_k]), {
            "embed_ms": (embedded_at - started_at) * 1000,
            "qdrant_ms": (queried_at - embedded_at) * 1000,
            "primary_qdrant_ms": primary_qdrant_ms,
            "recovery_qdrant_ms": (queried_at - primary_queried_at) * 1000,
            "score_ms": (scored_at - queried_at) * 1000,
            "rerank_ms": (reranked_at - scored_at) * 1000,
            "recovery_triggered": float(recovery_triggered),
            "category_filter_relaxed": float(category_filter_relaxed),
            "recovery_rescued_top5": float(recovery_rescued_top5),
            "top1_lexical_coverage": top1_lexical_coverage,
        }

    def search_image(self, request: ImageSearchRequest) -> SearchResponse:
        started_at = monotonic()
        output_top_k = _resolve_top_k(request.top_k, self.settings.image_top_k, self.settings)
        filters = normalize_filter_values(request.filters)
        image = _image_payload_to_pil(request.image, self.settings)
        decoded_at = monotonic()
        crops = self._crops_for_search(image=image, crop_box=request.crop_box)
        cropped_at = monotonic()
        image_points = self._search_image_points(
            crops=crops,
            filters=filters,
            limit=output_top_k,
        )
        queried_at = monotonic()
        image_points = _rank_points_by_detected_category(image_points, crops, self.settings)
        grouped = _best_score_by_product(image_points)
        results = [
            SearchResultItem(product_id=product_id, score=score, source="image")
            for product_id, score in sorted(
                grouped.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        results = _boost_image_results(results, image_points, filters, self.settings)
        scored_at = monotonic()
        logger.info(
            "image_search_latency decode=%.1fms crop=%.1fms embed_qdrant=%.1fms score=%.1fms total=%.1fms "
            "image_width=%d image_height=%d crop_count=%d fallback_count=%d",
            (decoded_at - started_at) * 1000,
            (cropped_at - decoded_at) * 1000,
            (queried_at - cropped_at) * 1000,
            (scored_at - queried_at) * 1000,
            (scored_at - started_at) * 1000,
            image.width,
            image.height,
            len(crops),
            sum(1 for crop in crops if crop.is_fallback),
        )
        return _response(None, filters, results[:output_top_k], detections=_detections_from_crops(crops))

    def detect_image(self, request: ImageDetectionRequest) -> ImageDetectionResponse:
        started_at = monotonic()
        image = _image_payload_to_pil(request.image, self.settings)
        decoded_at = monotonic()
        crops = self.yolo_crop_service.detect_and_crop(image)
        cropped_at = monotonic()
        width, height = image.size
        logger.info(
            "image_detection_latency decode=%.1fms yolo=%.1fms total=%.1fms image_width=%d image_height=%d "
            "crop_count=%d fallback_count=%d",
            (decoded_at - started_at) * 1000,
            (cropped_at - decoded_at) * 1000,
            (cropped_at - started_at) * 1000,
            width,
            height,
            len(crops),
            sum(1 for crop in crops if crop.is_fallback),
        )
        return ImageDetectionResponse(
            image_width=width,
            image_height=height,
            detections=_detections_from_crops(crops),
        )

    def search_hybrid(self, request: HybridSearchRequest) -> SearchResponse:
        started_at = monotonic()
        analysis = (
            self._analyze_query_cached(request.query)
            if request.query
            else None
        )
        analyzed_at = monotonic()
        query_explicit_filters = explicit_query_filters(analysis)
        should_call_llm = bool(
            request.query
            and analysis
            and analysis.should_call_llm
            and not (
                analysis.intent == "find_similar"
                and (
                    query_explicit_filters is not None
                    or analysis.filters.use_cases
                )
            )
        )
        understood = (
            self.llm_service.analyze_user_query(request.query, locale="vi-VN")
            if should_call_llm and request.query
            else None
        )
        understood_at = monotonic()
        rewritten_query = (
            (understood.rewritten_query if understood else None)
            or (
                analysis.corrected_query
                if analysis and analysis.intent == "find_similar"
                else None
            )
            or (analysis.semantic_query if analysis else None)
            or request.query
        )
        llm_filters = sanitize_llm_attribute_filters(
            understood.filters if understood else None,
            analysis.filters if analysis else None,
        )
        extracted_filters = merge_missing_filters(
            analysis.filters if analysis else None,
            llm_filters,
        )
        filters = merge_filters(extracted_filters, request.filters)
        explicit_filters = merge_filters(query_explicit_filters, request.filters)
        constraints = None
        if self.settings.hybrid_inferred_filters_soft_enabled:
            raw_match_sources = analysis.metadata.get("match_sources", {}) if analysis else {}
            match_sources = raw_match_sources if isinstance(raw_match_sources, dict) else {}
            constraints = resolve_search_constraints(
                rule_filters=analysis.filters if analysis else None,
                llm_filters=llm_filters,
                explicit_filters=explicit_filters,
                confidences=analysis.confidences if analysis else {},
                match_sources={str(key): str(value) for key, value in match_sources.items()},
                category_ambiguous=bool(
                    analysis
                    and any(
                        warning in {"ambiguous_category", "ambiguous_fuzzy_match"}
                        for warning in analysis.warnings
                    )
                ),
            )
            for constraint in constraints.constraints:
                logger.info(
                    "hybrid_search_constraint field=%s value=%r source=%s confidence=%.3f mode=%s",
                    constraint.field,
                    constraint.value,
                    constraint.source,
                    constraint.confidence,
                    constraint.mode,
                )
        response = self.search_hybrid_prepared(
            rewritten_query=rewritten_query,
            original_query=request.query,
            image=request.image,
            crop_box=request.crop_box,
            filters=filters,
            top_k=request.top_k,
            constraints=constraints,
        )
        logger.info(
            "hybrid_search_latency analyze=%.1fms llm=%.1fms prepared=%.1fms total=%.1fms "
            "explicit_filters=%d hard_filters=%d soft_filters=%d parallel=%s",
            (analyzed_at - started_at) * 1000,
            (understood_at - analyzed_at) * 1000,
            (monotonic() - understood_at) * 1000,
            (monotonic() - started_at) * 1000,
            len(explicit_filters.model_dump(exclude_none=True)) if explicit_filters else 0,
            len(constraints.hard_filters.model_dump(exclude_none=True))
            if constraints and constraints.hard_filters
            else 0,
            len(constraints.soft_filters.model_dump(exclude_none=True))
            if constraints and constraints.soft_filters
            else 0,
            self.settings.hybrid_parallel_branches_enabled,
        )
        return response

    def search_hybrid_prepared(
        self,
        *,
        rewritten_query: str | None,
        original_query: str | None = None,
        image: ImagePayload | None,
        crop_box: ImageBoundingBox | None,
        filters: SearchFilter | None,
        top_k: int | None = None,
        constraints: ResolvedSearchConstraints | None = None,
    ) -> SearchResponse:
        started_at = monotonic()
        output_top_k = _resolve_top_k(top_k, self.settings.hybrid_top_k, self.settings)
        candidate_limit = _hybrid_candidate_limit(output_top_k, self.settings)
        hard_filters = constraints.hard_filters if constraints is not None else filters
        ranking_filters = constraints.soft_filters if constraints is not None else filters
        candidates: dict[str, _Candidate] = {}

        def retrieve_text(branch_filters: SearchFilter | None) -> list[_ScoredPoint]:
            if not rewritten_query:
                return []
            text_vector = self.text_embedding_service.embed_query(rewritten_query)
            exact_points: list[_ScoredPoint] = []
            exact_query = normalize_query_text(original_query or "")
            if self.settings.hybrid_lexical_fusion_enabled and exact_query:
                exact_points = self._query_collection(
                    collection_name=self.settings.qdrant_text_collection,
                    vector=text_vector,
                    filters=branch_filters,
                    limit=output_top_k,
                    soft_attributes=False,
                    exact_title=exact_query,
                )
            vector_points = self._query_collection(
                collection_name=self.settings.qdrant_text_collection,
                vector=text_vector,
                filters=branch_filters,
                limit=candidate_limit,
                soft_attributes=False,
            )
            return _dedupe_by_product([*exact_points, *vector_points])

        def retrieve_image(branch_filters: SearchFilter | None) -> list[_ScoredPoint]:
            if image is None:
                return []
            pil_image = _image_payload_to_pil(image, self.settings)
            crops = self._crops_for_search(image=pil_image, crop_box=crop_box)
            return _dedupe_by_product(
                self._search_image_points(
                    crops=crops,
                    filters=branch_filters,
                    limit=candidate_limit,
                    soft_attributes=False,
                )
            )

        branch_started_at = monotonic()
        if (
            rewritten_query
            and image is not None
            and self.settings.hybrid_parallel_branches_enabled
        ):
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="hybrid-search") as executor:
                text_future = executor.submit(retrieve_text, hard_filters)
                image_future = executor.submit(retrieve_image, hard_filters)
                text_points = text_future.result()
                image_points = image_future.result()
        else:
            text_points = retrieve_text(hard_filters)
            image_points = retrieve_image(hard_filters)
        branch_finished_at = monotonic()

        recovery_triggered = False
        relaxed_filter_names: list[str] = []
        if (
            constraints is not None
            and self.settings.hybrid_filter_recovery_enabled
            and constraints.has_recoverable_inferred_hard_filters
            and len({point.product_id for point in [*text_points, *image_points]}) < output_top_k
        ):
            recovery_triggered = True
            before_count = len({point.product_id for point in [*text_points, *image_points]})
            recovered_text = retrieve_text(constraints.recovery_filters)
            recovered_image = retrieve_image(constraints.recovery_filters)
            text_points = _dedupe_by_product([*text_points, *recovered_text])
            image_points = _dedupe_by_product([*image_points, *recovered_image])
            retained_recovery_fields = (
                set(constraints.recovery_filters.model_dump(exclude_none=True))
                if constraints.recovery_filters
                else set()
            )
            relaxed_filter_names = [
                item.field
                for item in constraints.constraints
                if item.mode == "hard"
                and item.source != "explicit"
                and item.field not in retained_recovery_fields
            ]
            logger.info(
                "hybrid_search_recovery_triggered reason=weak_candidates before=%d after=%d relaxed=%s",
                before_count,
                len({point.product_id for point in [*text_points, *image_points]}),
                relaxed_filter_names,
            )

        for point in text_points:
            candidate = candidates.setdefault(point.product_id, _Candidate(product_id=point.product_id))
            lexical_boost = (
                sum(
                    _lexical_score_components(
                        point.payload,
                        original_query or rewritten_query or "",
                        self.settings,
                    ).values()
                )
                if self.settings.hybrid_lexical_fusion_enabled
                else 0.0
            )
            candidate.text_similarity = max(candidate.text_similarity, point.score + lexical_boost)
            candidate.present_in_text = True
            candidate.embedding_text = _embedding_text_from_payload(point.payload)
            candidate.payload = point.payload

        for point in image_points:
            candidate = candidates.setdefault(point.product_id, _Candidate(product_id=point.product_id))
            candidate.image_similarity = max(candidate.image_similarity, point.score)
            candidate.present_in_image = True
            if not candidate.payload:
                candidate.payload = point.payload

        scored_started_at = monotonic()
        scored_results: list[SearchResultItem] = []
        for candidate in candidates.values():
            explicit_satisfaction = _filter_satisfaction(
                candidate.payload,
                constraints.explicit_hard_filters if constraints is not None else None,
            )
            if explicit_satisfaction and not all(explicit_satisfaction.values()):
                continue
            score = self._hybrid_score(candidate, ranking_filters)
            scored_results.append(
                SearchResultItem(
                    product_id=candidate.product_id,
                    score=score,
                    source="hybrid",
                    explicit_constraint_satisfied=(
                        all(explicit_satisfaction.values())
                        if explicit_satisfaction
                        else None
                    ),
                    explicit_constraint_satisfaction=explicit_satisfaction or None,
                )
            )
            logger.debug(
                "hybrid_search_score product_id=%s present_in_text=%s present_in_image=%s "
                "text_similarity=%.6f image_similarity=%.6f score=%.6f",
                candidate.product_id,
                candidate.present_in_text,
                candidate.present_in_image,
                candidate.text_similarity,
                candidate.image_similarity,
                score,
            )
        scored_results.sort(key=lambda result: result.score, reverse=True)
        scored_at = monotonic()
        content_by_product = {
            candidate.product_id: candidate.embedding_text
            for candidate in candidates.values()
            if candidate.embedding_text
        }
        scored_results = self._rerank(rewritten_query, scored_results, content_by_product)
        reranked_at = monotonic()
        logger.info(
            "hybrid_search_stage_latency branches=%.1fms score=%.1fms rerank=%.1fms total=%.1fms "
            "text_candidates=%d image_candidates=%d union_candidates=%d recovery_triggered=%s",
            (branch_finished_at - branch_started_at) * 1000,
            (scored_at - scored_started_at) * 1000,
            (reranked_at - scored_at) * 1000,
            (reranked_at - started_at) * 1000,
            len(text_points),
            len(image_points),
            len(candidates),
            recovery_triggered,
        )
        response_filters = constraints.response_filters if constraints is not None else filters
        final_results = scored_results[:output_top_k]
        logger.info(
            "hybrid_search_result_summary candidate_limit=%d returned_count=%d underfilled=%s",
            candidate_limit,
            len(final_results),
            len(final_results) < output_top_k,
        )
        explicit_filters = (
            constraints.explicit_hard_filters if constraints is not None else None
        )
        return _response(
            rewritten_query,
            response_filters,
            final_results,
            explicit_filters=explicit_filters,
            inferred_filters=(
                constraints.inferred_filters if constraints is not None else None
            ),
            relaxed_filters=relaxed_filter_names,
            constraint_failure_reason=(
                "no_candidates_satisfy_explicit_filters"
                if explicit_filters is not None and not final_results
                else None
            ),
        )

    def _analyze_query_cached(self, query: str) -> QueryAnalysis:
        catalog = self._catalog_metadata()
        cache_size = self.settings.hybrid_query_parse_cache_size
        key = (
            f"{CANONICALIZER_VERSION}:"
            f"{int(self.settings.text_typo_correction_enabled)}:"
            f"{normalize_query_text(query)}"
        )
        if cache_size:
            with self._cache_lock:
                cached = self._query_analysis_cache.get(key)
                if cached is not None:
                    self._query_analysis_cache.move_to_end(key)
                    return cached
        analysis = analyze_query(
            query,
            catalog,
            typo_correction_enabled=self.settings.text_typo_correction_enabled,
        )
        if cache_size:
            with self._cache_lock:
                self._query_analysis_cache[key] = analysis
                self._query_analysis_cache.move_to_end(key)
                while len(self._query_analysis_cache) > cache_size:
                    self._query_analysis_cache.popitem(last=False)
        return analysis

    def _understand_query_cached(self, query: str, *, locale: str):
        cache_size = self.settings.text_llm_analysis_cache_size
        cache_ttl = self.settings.text_llm_analysis_cache_ttl_seconds
        key = f"{locale}:{normalize_query_text(query)}"
        now = monotonic()
        if cache_size and cache_ttl:
            with self._cache_lock:
                cached = self._llm_analysis_cache.get(key)
                if cached is not None and cached[0] > now:
                    self._llm_analysis_cache.move_to_end(key)
                    return deepcopy(cached[1])
                if cached is not None:
                    self._llm_analysis_cache.pop(key, None)

        understood = self.llm_service.analyze_user_query(query, locale=locale)
        if cache_size and cache_ttl:
            with self._cache_lock:
                self._llm_analysis_cache[key] = (
                    monotonic() + cache_ttl,
                    deepcopy(understood),
                )
                self._llm_analysis_cache.move_to_end(key)
                while len(self._llm_analysis_cache) > cache_size:
                    self._llm_analysis_cache.popitem(last=False)
        return understood

    def _catalog_metadata(self) -> CatalogMetadata:
        now = monotonic()
        if (
            self._catalog_metadata_cache is not None
            and now - self._catalog_metadata_loaded_at
            < self.settings.text_catalog_metadata_cache_ttl_seconds
        ):
            return self._catalog_metadata_cache
        try:
            metadata = _load_catalog_metadata_from_qdrant(
                client=self.qdrant_client,
                collection_name=self.settings.qdrant_text_collection,
            )
        except Exception:
            logger.debug("catalog_metadata_load_failed", exc_info=True)
            metadata = CatalogMetadata()
        self._catalog_metadata_cache = metadata
        self._catalog_metadata_loaded_at = now
        with self._cache_lock:
            self._query_analysis_cache.clear()
        return metadata

    def _search_image_points(
        self,
        *,
        crops: list[CropResult],
        filters: SearchFilter | None,
        limit: int,
        soft_attributes: bool = False,
    ) -> list["_ScoredPoint"]:
        embedded_started_at = monotonic()
        vectors = self._embed_images_cached([crop.image for crop in crops])
        embedded_at = monotonic()
        per_crop_limit = _image_per_crop_limit(limit, len(crops), self.settings)
        initial_per_crop_limit = per_crop_limit
        refill_rounds = 0
        all_points: list[_ScoredPoint] = []
        while True:
            all_points = []
            result_counts: list[int] = []
            for vector in vectors:
                points = self._query_collection(
                    collection_name=self.settings.qdrant_image_collection,
                    vector=vector,
                    filters=filters,
                    limit=per_crop_limit,
                    soft_attributes=soft_attributes,
                )
                all_points.extend(points)
                result_counts.append(len(points))
            unique_product_count = len({point.product_id for point in all_points})
            collection_exhausted = bool(result_counts) and all(
                count < per_crop_limit for count in result_counts
            )
            if (
                unique_product_count >= limit
                or collection_exhausted
                or per_crop_limit >= self.settings.image_query_per_crop_limit_cap
            ):
                break
            next_limit = min(
                per_crop_limit * 2,
                self.settings.image_query_per_crop_limit_cap,
            )
            if next_limit == per_crop_limit:
                break
            per_crop_limit = next_limit
            refill_rounds += 1
        queried_at = monotonic()
        logger.info(
            "image_search_vector_latency image_embedding=%.1fms qdrant=%.1fms crop_count=%d "
            "initial_per_crop_limit=%d final_per_crop_limit=%d refill_rounds=%d raw_point_count=%d "
            "unique_product_count=%d",
            (embedded_at - embedded_started_at) * 1000,
            (queried_at - embedded_at) * 1000,
            len(crops),
            initial_per_crop_limit,
            per_crop_limit,
            refill_rounds,
            len(all_points),
            len({point.product_id for point in all_points}),
        )
        return all_points

    def _embed_images_cached(self, images: list[Image.Image]) -> list[list[float]]:
        cache_size = self.settings.hybrid_image_embedding_cache_size
        if not cache_size:
            return self.image_embedding_service.embed_queries(images)

        now = monotonic()
        ttl = self.settings.hybrid_image_embedding_cache_ttl_seconds
        digests = [_image_digest(image) for image in images]
        resolved: dict[str, list[float]] = {}
        missing_digests: list[str] = []
        missing_images: list[Image.Image] = []
        with self._cache_lock:
            for digest, image in zip(digests, images, strict=True):
                cached = self._image_embedding_cache.get(digest)
                if cached is not None and now - cached[0] <= ttl:
                    resolved[digest] = list(cached[1])
                    self._image_embedding_cache.move_to_end(digest)
                else:
                    if cached is not None:
                        self._image_embedding_cache.pop(digest, None)
                    if digest not in missing_digests:
                        missing_digests.append(digest)
                        missing_images.append(image)

        if missing_images:
            embedded = self.image_embedding_service.embed_queries(missing_images)
            with self._cache_lock:
                for digest, vector in zip(missing_digests, embedded, strict=True):
                    resolved[digest] = list(vector)
                    self._image_embedding_cache[digest] = (now, list(vector))
                    self._image_embedding_cache.move_to_end(digest)
                while len(self._image_embedding_cache) > cache_size:
                    self._image_embedding_cache.popitem(last=False)
        return [list(resolved[digest]) for digest in digests]

    def _crops_for_search(self, *, image: Image.Image, crop_box: ImageBoundingBox | None) -> list[CropResult]:
        if crop_box is None:
            return self.yolo_crop_service.detect_and_crop(image)
        source_image = image.convert("RGB")
        width, height = source_image.size
        bbox = _clamp_user_bbox(crop_box, width, height)
        return [
            CropResult(
                image=source_image.crop(bbox),
                bbox=bbox,
                confidence=1.0,
                class_id=None,
                is_fallback=False,
            )
        ]

    def _query_collection(
        self,
        *,
        collection_name: str,
        vector: list[float],
        filters: SearchFilter | None,
        limit: int,
        soft_attributes: bool = False,
        exact_title: str | None = None,
    ) -> list["_ScoredPoint"]:
        query_filter = _build_qdrant_filter(filters, soft_attributes=soft_attributes)
        if exact_title:
            query_filter.should = [
                models.FieldCondition(
                    key="normalized_title_vi",
                    match=models.MatchValue(value=exact_title),
                ),
                models.FieldCondition(
                    key="normalized_title",
                    match=models.MatchValue(value=exact_title),
                ),
            ]
        response = self.qdrant_client.query_points(
            collection_name=collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=[
                "product_id",
                "category_keys",
                "brand_key",
                "color_keys",
                "material_keys",
                "use_case_keys",
                "size_keys",
                "gender_key",
                "audience_keys",
                "category_names",
                "category_names_vi",
                "normalized_title",
                "normalized_title_vi",
                "title_tokens",
                "embedding_text",
                "base_colour",
                "base_colour_vi",
                "gender",
                "gender_vi",
                "product_usage",
                "product_usage_vi",
                "season",
                "season_vi",
                "available",
                "inventory_count",
                "selling_price",
            ],
            with_vectors=False,
        )
        return _extract_scored_points(response)

    def _hybrid_score(self, candidate: _Candidate, filters: SearchFilter | None) -> float:
        filter_match = 0.0
        if self.settings.hybrid_soft_attribute_boost_enabled:
            filter_match = _inferred_filter_match_ratio(candidate.payload, filters)
        business_boost = _business_signal(candidate.payload)
        use_case_match_ratio = _use_case_match_ratio(candidate.payload, filters)
        if self.settings.hybrid_use_case_overlap_boost_enabled:
            use_case_boost = self.settings.hybrid_use_case_boost_weight * use_case_match_ratio
        else:
            use_case_boost = (
                self.settings.hybrid_use_case_boost_weight
                if use_case_match_ratio > 0
                else 0.0
            )
        return (
            self.settings.hybrid_image_weight * candidate.image_similarity
            + self.settings.hybrid_text_weight * candidate.text_similarity
            + self.settings.hybrid_filter_weight * filter_match
            + self.settings.hybrid_business_weight * business_boost
            + use_case_boost
        )

    def _rerank(
        self,
        query: str | None,
        results: list[SearchResultItem],
        content_by_product: dict[str, str],
    ) -> list[SearchResultItem]:
        if not self.settings.rerank_enabled or not query or len(results) < 2:
            return results

        window = results[: self.settings.rerank_top_k]
        tail = results[self.settings.rerank_top_k :]
        rerankable = [item for item in window if content_by_product.get(item.product_id)]
        if len(rerankable) < 2:
            return results

        documents = [content_by_product[item.product_id] for item in rerankable]
        try:
            scores = self.rerank_service.rerank(query, documents)
        except Exception:
            logger.exception("rerank_failed")
            return results

        for item, score in zip(rerankable, scores, strict=True):
            item.rerank_score = float(score)
        reranked = sorted(rerankable, key=lambda item: item.rerank_score or 0.0, reverse=True)
        skipped = [item for item in window if not content_by_product.get(item.product_id)]
        return reranked + skipped + tail


@dataclass(frozen=True)
class _ScoredPoint:
    product_id: str
    score: float
    payload: dict[str, object] = field(default_factory=dict)


_CLASS_CATEGORY_KEYWORDS: dict[int, tuple[str, ...]] = {
    0: ("shirt", "tshirt", "tee", "top", "blouse", "ao", "ao thun", "ao so mi"),
    1: ("bag", "bags", "backpack", "handbag", "wallet", "balo", "tui", "vi"),
    2: ("pants", "jeans", "trousers", "shorts", "skirt", "quan", "vay"),
    3: ("shoe", "shoes", "sneaker", "sneakers", "footwear", "boot", "boots", "sandals", "heels", "giay"),
    4: ("dress", "dresses", "dam", "vay"),
    5: ("jacket", "coat", "hoodie", "sweater", "ao khoac", "ao hoodie"),
    6: ("watch", "belt", "hat", "cap", "glasses", "accessory", "accessories", "dong ho", "that lung", "mu", "kinh"),
}


def _image_payload_to_pil(payload: ImagePayload, settings: Settings | None = None) -> Image.Image:
    settings = settings or get_settings()
    try:
        image = Image.open(BytesIO(b64decode(payload.data_base64, validate=True)))
        image = ImageOps.exif_transpose(image)
        image.load()
    except (BinasciiError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("image payload must contain a decodable image") from exc

    image = image.convert("RGB")
    width, height = image.size
    if width < settings.image_min_width or height < settings.image_min_height:
        raise ValueError(
            f"image dimensions must be at least {settings.image_min_width}x{settings.image_min_height}"
        )

    if max(width, height) > settings.image_max_side:
        image.thumbnail((settings.image_max_side, settings.image_max_side), Image.Resampling.LANCZOS)
    return image


def _image_digest(image: Image.Image) -> str:
    normalized = image.convert("RGB")
    digest = sha256()
    digest.update(f"{normalized.width}x{normalized.height}:RGB".encode("ascii"))
    digest.update(normalized.tobytes())
    return digest.hexdigest()


def _clamp_user_bbox(bbox: ImageBoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    left = max(0, min(width - 1, bbox.left))
    top = max(0, min(height - 1, bbox.top))
    right = max(left + 1, min(width, bbox.right))
    bottom = max(top + 1, min(height, bbox.bottom))
    return (left, top, right, bottom)


def _detections_from_crops(crops: list[CropResult]) -> list[ImageDetectionBox]:
    return [
        ImageDetectionBox(
            bbox=ImageBoundingBox(
                left=crop.bbox[0],
                top=crop.bbox[1],
                right=crop.bbox[2],
                bottom=crop.bbox[3],
            ),
            confidence=crop.confidence,
            class_id=crop.class_id,
            is_fallback=crop.is_fallback,
        )
        for crop in crops
    ]


def _build_qdrant_filter(filters: SearchFilter | None, *, soft_attributes: bool = False) -> models.Filter:
    must: list[models.Condition] = [
        models.FieldCondition(key="active", match=models.MatchValue(value=True)),
    ]
    if filters is None:
        return models.Filter(must=must)

    if filters.category:
        category_keys = category_filter_keys([filters.category])
        if category_keys:
            must.append(
                models.FieldCondition(key="category_keys", match=models.MatchAny(any=category_keys))
            )
    # When soft_attributes is on, gender/colors are excluded from the hard filter
    # and applied as ranking boosts instead (see _text_score_boost), so a wrong
    # gender/color extraction no longer drops the correct product entirely.
    if filters.gender and not soft_attributes:
        gender_key = canonicalize_gender_key(filters.gender)
        if gender_key:
            must.append(
                models.FieldCondition(key="audience_keys", match=models.MatchValue(value=gender_key))
            )
    if filters.brand:
        brand_key = canonicalize_brand_key(filters.brand)
        if brand_key:
            must.append(models.FieldCondition(key="brand_key", match=models.MatchValue(value=brand_key)))
    if filters.colors and not soft_attributes:
        color_keys = color_filter_keys(filters.colors)
        if color_keys:
            if filters.color_match_mode == "all" and len(color_keys) > 1:
                must.extend(
                    models.FieldCondition(
                        key="color_keys",
                        match=models.MatchValue(value=color_key),
                    )
                    for color_key in color_keys
                )
            else:
                must.append(
                    models.FieldCondition(
                        key="color_keys",
                        match=models.MatchAny(any=color_keys),
                    )
                )
    if filters.use_cases and not soft_attributes:
        use_case_keys = canonicalize_use_case_keys(filters.use_cases)
        if use_case_keys:
            must.append(
                models.FieldCondition(
                    key="use_case_keys",
                    match=models.MatchAny(any=use_case_keys),
                )
            )
    if filters.sizes:
        size_keys = canonicalize_size_keys(filters.sizes)
        if size_keys:
            must.append(models.FieldCondition(key="size_keys", match=models.MatchAny(any=size_keys)))
    if filters.material:
        material_keys = canonicalize_material_keys([filters.material])
        if material_keys:
            must.append(models.FieldCondition(key="material_keys", match=models.MatchAny(any=material_keys)))
    if filters.min_price is not None or filters.max_price is not None:
        must.append(
            models.FieldCondition(
                key="selling_price",
                range=models.Range(gte=filters.min_price, lte=filters.max_price),
            )
        )
    return models.Filter(must=must)


def _payload_str_values(payload: dict[str, object], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = payload.get(key)
        if isinstance(raw, str):
            if raw:
                values.add(_normalize_text(raw))
        elif isinstance(raw, (list, tuple)):
            for item in raw:
                if isinstance(item, str) and item:
                    values.add(_normalize_text(item))
    return values


def _gender_payload_values(value: str) -> list[str]:
    canonical = normalize_gender(value) or _normalize_text(value)
    aliases = {
        "women": ["women", "Women", "female", "Female", "nữ", "Nữ", "nu"],
        "men": ["men", "Men", "male", "Male", "nam", "Nam"],
        "unisex": ["unisex", "Unisex", "unisex adult", "Unisex Adult"],
    }
    return aliases.get(canonical, [value])


def _text_score_boost(
    payload: dict[str, object],
    filters: SearchFilter | None,
    settings: Settings,
) -> float:
    """Legacy boost entry point retained for image/hybrid callers and unit compatibility."""
    boost = 0.0
    if filters is not None and settings.text_soft_attribute_boost_enabled:
        boost += _soft_attribute_boost(
            payload,
            filters,
            color_weight=settings.text_color_boost_weight,
            gender_weight=settings.text_gender_boost_weight,
        )
    if settings.text_business_boost_enabled:
        boost += _business_boost(payload, settings.text_business_boost_weight)
    return boost


def _text_score_components(
    payload: dict[str, object],
    filters: SearchFilter | None,
    settings: Settings,
    *,
    query: str,
) -> dict[str, float]:
    components: dict[str, float] = {}
    if settings.text_lexical_fusion_enabled:
        components.update(_lexical_score_components(payload, query, settings))
    inferred_boost = _inferred_filter_boost(payload, filters, settings)
    if inferred_boost:
        components["inferred_filter"] = inferred_boost
    exact_shade_boost = _exact_shade_boost(
        payload,
        filters,
        settings,
        query=query,
    )
    use_case_boost = (
        settings.text_use_case_boost_weight
        * _explicit_usage_phrase_match_ratio(payload, query)
    )
    if use_case_boost:
        components['use_case'] = use_case_boost
    if exact_shade_boost:
        components["exact_shade"] = exact_shade_boost
    if filters is not None and settings.text_soft_attribute_boost_enabled:
        attribute_boost = _soft_attribute_boost(
            payload,
            filters,
            color_weight=settings.text_color_boost_weight,
            gender_weight=settings.text_gender_boost_weight,
        )
        if attribute_boost:
            components["soft_attribute"] = attribute_boost
    if settings.text_business_boost_enabled:
        business_boost = _business_boost(payload, settings.text_business_boost_weight)
        if business_boost:
            components["business"] = business_boost
    return components


def _lexical_score_components(
    payload: dict[str, object],
    query: str,
    settings: Settings,
) -> dict[str, float]:
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        return {}
    titles = _payload_str_values(payload, "normalized_title_vi", "normalized_title")
    titles = {normalize_query_text(title) for title in titles if title}
    if not titles:
        return {}

    query_tokens = set(normalized_query.split())
    best_coverage = max(
        (len(query_tokens & set(title.split())) / len(query_tokens) for title in titles),
        default=0.0,
    )
    components: dict[str, float] = {}
    if normalized_query in titles:
        components["exact_title"] = settings.text_exact_title_boost_weight
    if any(normalized_query in title or title in normalized_query for title in titles):
        components["phrase"] = settings.text_phrase_boost_weight
    if best_coverage:
        components["token_coverage"] = settings.text_token_coverage_boost_weight * best_coverage
    if any(title.startswith(normalized_query) or normalized_query.startswith(title) for title in titles):
        components["prefix"] = settings.text_prefix_boost_weight
    specific_tokens = {
        token
        for token in query_tokens
        if len(token) >= 3 and token not in _GENERIC_RANKING_TOKENS
    }
    if specific_tokens:
        best_specific_coverage = 0.0
        best_fuzzy_coverage = 0.0
        for title in titles:
            title_tokens = set(title.split())
            exact_specific = specific_tokens & title_tokens
            best_specific_coverage = max(
                best_specific_coverage,
                len(exact_specific) / len(specific_tokens),
            )
            unmatched = specific_tokens - exact_specific
            fuzzy_matches = sum(
                any(
                    SequenceMatcher(None, query_token, title_token).ratio()
                    >= settings.text_fuzzy_token_min_similarity
                    for title_token in title_tokens
                    if abs(len(query_token) - len(title_token)) <= 2
                )
                for query_token in unmatched
            )
            best_fuzzy_coverage = max(
                best_fuzzy_coverage,
                fuzzy_matches / len(specific_tokens),
            )
        if best_specific_coverage:
            components["specific_tokens"] = (
                settings.text_specific_token_boost_weight * best_specific_coverage
            )
        if best_fuzzy_coverage:
            components["fuzzy_tokens"] = (
                settings.text_fuzzy_token_boost_weight * best_fuzzy_coverage
            )
    return components


_EXPLICIT_COLOR_SHADE_PHRASES = (
    'trang nga',
    'trang kem',
    'nau chocolate',
    'xanh navy',
    'xanh da troi',
    'xanh olive',
    'cham dam',
    'hong phan',
)

_STRICT_COLOR_SHADE_RULES: tuple[
    tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...
] = (
    (("wine red", "red wine", "do ruou vang"), ("wine",), ()),
    (("dark brown", "nau dam"), ("dark brown", "brown dark"), ()),
    (("gold metallic", "metallic gold", "vang anh kim"), ("golden", "metallic gold", "gold"), ()),
    (("striped brown", "brown striped", "nau soc"), ("brown stripe", "brown stripes", "striped brown"), ()),
    (("pastel pink", "hong pastel", "pastel style"), ("pastel",), ()),
    (("tobacco brown", "nau thuoc la", "thuoc la"), ("tobacco",), ()),
    (("charcoal gray", "charcoal grey", "xam than", "charcoal"), ("charcoal",), ()),
    (("sand and black", "sand black", "mau cat den"), (), ("sand", "black")),
)


def _filter_requested_color_shade(
    results: list[SearchResultItem],
    payload_by_product: dict[str, dict[str, object]],
    *,
    query: str,
) -> list[SearchResultItem]:
    """Keep exact compound shades instead of padding with the broad color family."""

    normalized_query = normalize_query_text(query)
    rule = next(
        (
            (accepted_any, accepted_all)
            for triggers, accepted_any, accepted_all in _STRICT_COLOR_SHADE_RULES
            if any(contains_token(normalized_query, trigger) for trigger in triggers)
        ),
        None,
    )
    if rule is None:
        return results
    accepted_any, accepted_all = rule
    filtered: list[SearchResultItem] = []
    for result in results:
        payload = payload_by_product.get(result.product_id, {})
        raw_color = " ".join(
            normalize_query_text(value)
            for value in (payload.get("base_colour"), payload.get("base_colour_vi"))
            if isinstance(value, str)
        )
        matches_any = bool(accepted_any) and any(
            contains_token(raw_color, phrase) for phrase in accepted_any
        )
        matches_all = bool(accepted_all) and all(
            contains_token(raw_color, token) for token in accepted_all
        )
        if matches_any or matches_all:
            filtered.append(result)
    return filtered


def _exact_shade_boost(
    payload: dict[str, object],
    filters: SearchFilter | None,
    settings: Settings,
    *,
    query: str,
) -> float:
    """Rank an exact color match above its shade variants within the same family.

    After reindexing, `color_keys` only carries family keys (pink, blue, ...), so a
    "màu hồng" query matches "Pink", "Hồng pastel" and "dusty pink" equally. When the
    raw `base_colour` IS the plain requested family, add a small boost so the exact
    shade outranks its variants without hard-filtering them out."""
    if not filters or not filters.colors or settings.text_exact_shade_boost_weight <= 0:
        return 0.0
    wanted = set(canonicalize_color_keys(filters.colors))
    if not wanted:
        return 0.0
    normalized_query = normalize_query_text(query)
    requested_compound_shades = {
        phrase
        for phrase in _EXPLICIT_COLOR_SHADE_PHRASES
        if contains_token(normalized_query, phrase)
    }
    if requested_compound_shades:
        raw_colors = {
            normalize_query_text(raw_color)
            for raw_color in (
                payload.get('base_colour'),
                payload.get('base_colour_vi'),
            )
            if isinstance(raw_color, str)
        }
        if any(
            contains_token(raw_color, phrase)
            for phrase in requested_compound_shades
            for raw_color in raw_colors
        ):
            return settings.text_exact_shade_boost_weight
        return 0.0
    for raw_color in (payload.get("base_colour"), payload.get("base_colour_vi")):
        if isinstance(raw_color, str) and any(
            is_exact_color_shade(raw_color, family) for family in wanted
        ):
            return settings.text_exact_shade_boost_weight
    return 0.0


def _inferred_filter_boost(
    payload: dict[str, object],
    filters: SearchFilter | None,
    settings: Settings,
) -> float:
    if filters is None or not settings.text_inferred_filters_soft_enabled:
        return 0.0
    return settings.text_inferred_filter_boost_weight * _inferred_filter_match_ratio(payload, filters)


def _inferred_filter_match_ratio(
    payload: dict[str, object],
    filters: SearchFilter | None,
) -> float:
    """Return the canonical match ratio for inferred ranking-only constraints."""

    if filters is None:
        return 0.0
    matches = 0
    requested = 0

    checks: list[tuple[bool, bool]] = []
    if filters.category:
        wanted = set(category_filter_keys([filters.category]))
        actual = _payload_str_values(payload, "category_keys")
        checks.append((True, bool(wanted & actual)))
    if filters.brand:
        wanted_brand = canonicalize_brand_key(filters.brand)
        checks.append((True, wanted_brand in _payload_str_values(payload, "brand_key")))
    if filters.colors:
        wanted_colors = set(color_filter_keys(filters.colors))
        checks.append((True, bool(wanted_colors & _payload_str_values(payload, "color_keys"))))
    if filters.material:
        wanted_materials = set(canonicalize_material_keys([filters.material]))
        checks.append((True, bool(wanted_materials & _payload_str_values(payload, "material_keys"))))
    if filters.use_cases:
        wanted_use_cases = set(canonicalize_use_case_keys(filters.use_cases))
        checks.append(
            (
                True,
                bool(
                    wanted_use_cases
                    & _payload_str_values(payload, "use_case_keys")
                ),
            )
        )
    if filters.sizes:
        wanted_sizes = set(canonicalize_size_keys(filters.sizes))
        checks.append((True, bool(wanted_sizes & _payload_str_values(payload, "size_keys"))))
    if filters.gender:
        wanted_gender = canonicalize_gender_key(filters.gender)
        checks.append((True, bool(wanted_gender and wanted_gender in _payload_str_values(payload, "audience_keys"))))
    if filters.min_price is not None or filters.max_price is not None:
        price = payload.get("selling_price")
        matched_price = isinstance(price, (int, float)) and not isinstance(price, bool)
        if matched_price and filters.min_price is not None:
            matched_price = float(price) >= filters.min_price
        if matched_price and filters.max_price is not None:
            matched_price = float(price) <= filters.max_price
        checks.append((True, matched_price))

    for is_requested, is_match in checks:
        requested += int(is_requested)
        matches += int(is_match)
    return matches / requested if requested else 0.0


_EXPLICIT_USAGE_PHRASES = (
    'di choi',
    'di lam',
    'dao pho',
    'hen ho',
    'du tiec',
    'hang ngay',
)


def _explicit_usage_phrase_match_ratio(
    payload: dict[str, object],
    query: str,
) -> float:
    normalized_query = normalize_query_text(query)
    normalized_usage = normalize_query_text(
        str(payload.get('product_usage_vi') or '')
    )
    requested = {
        phrase
        for phrase in _EXPLICIT_USAGE_PHRASES
        if contains_token(normalized_query, phrase)
    }
    if not requested:
        return 0.0
    matched = {
        phrase
        for phrase in requested
        if contains_token(normalized_usage, phrase)
    }
    return len(matched) / len(requested)


def _use_case_match_ratio(
    payload: dict[str, object],
    filters: SearchFilter | None,
) -> float:
    if filters is None or not filters.use_cases:
        return 0.0
    wanted = set(canonicalize_use_case_keys(filters.use_cases))
    if not wanted:
        return 0.0
    actual = _payload_str_values(payload, "use_case_keys")
    return len(wanted & actual) / len(wanted)


def _use_case_matches(
    payload: dict[str, object],
    filters: SearchFilter | None,
) -> bool:
    return _use_case_match_ratio(payload, filters) > 0


def _filter_satisfaction(
    payload: dict[str, object],
    filters: SearchFilter | None,
) -> dict[str, bool]:
    if filters is None:
        return {}
    satisfaction: dict[str, bool] = {}
    if filters.category:
        satisfaction["category"] = bool(
            set(category_filter_keys([filters.category]))
            & _payload_str_values(payload, "category_keys")
        )
    if filters.brand:
        brand = canonicalize_brand_key(filters.brand)
        satisfaction["brand"] = bool(
            brand and brand in _payload_str_values(payload, "brand_key")
        )
    if filters.colors:
        satisfaction["colors"] = bool(
            set(color_filter_keys(filters.colors))
            & _payload_str_values(payload, "color_keys")
        )
    if filters.use_cases:
        satisfaction["use_cases"] = _use_case_matches(payload, filters)
    if filters.material:
        satisfaction["material"] = bool(
            set(canonicalize_material_keys([filters.material]))
            & _payload_str_values(payload, "material_keys")
        )
    if filters.sizes:
        satisfaction["sizes"] = bool(
            set(canonicalize_size_keys(filters.sizes))
            & _payload_str_values(payload, "size_keys")
        )
    if filters.gender:
        gender = canonicalize_gender_key(filters.gender)
        satisfaction["gender"] = bool(
            gender and gender in _payload_str_values(payload, "audience_keys")
        )
    price = _float_payload_value(payload.get("selling_price"))
    if filters.min_price is not None:
        satisfaction["min_price"] = bool(
            price is not None and price >= filters.min_price
        )
    if filters.max_price is not None:
        satisfaction["max_price"] = bool(
            price is not None and price <= filters.max_price
        )
    return satisfaction


def _soft_attribute_boost(
    payload: dict[str, object],
    filters: SearchFilter | None,
    *,
    color_weight: float,
    gender_weight: float,
) -> float:
    if filters is None:
        return 0.0

    boost = 0.0
    if filters.colors:
        product_colors = _payload_str_values(payload, "color_keys", "base_colour", "base_colour_vi")
        wanted_colors = set(color_filter_keys(filters.colors))
        if product_colors & wanted_colors:
            boost += color_weight
    if filters.gender:
        product_gender = _payload_str_values(payload, "audience_keys", "gender", "gender_vi")
        gender_key = canonicalize_gender_key(filters.gender)
        normalized_gender_values = {gender_key} if gender_key else set()
        if product_gender & normalized_gender_values:
            boost += gender_weight
    return boost


def _soft_attribute_match_ratio(
    payload: dict[str, object],
    filters: SearchFilter | None,
    *,
    color_weight: float,
    gender_weight: float,
) -> float:
    if filters is None:
        return 0.0

    matched_weight = 0.0
    requested_weight = 0.0
    if filters.colors:
        requested_weight += color_weight
        product_colors = _payload_str_values(payload, "color_keys", "base_colour", "base_colour_vi")
        wanted_colors = set(color_filter_keys(filters.colors))
        if product_colors & wanted_colors:
            matched_weight += color_weight
    if filters.gender:
        requested_weight += gender_weight
        product_gender = _payload_str_values(payload, "audience_keys", "gender", "gender_vi")
        gender_key = canonicalize_gender_key(filters.gender)
        if gender_key and gender_key in product_gender:
            matched_weight += gender_weight
    return matched_weight / requested_weight if requested_weight > 0 else 0.0


def _boost_image_results(
    results: list[SearchResultItem],
    points: Iterable[_ScoredPoint],
    filters: SearchFilter | None,
    settings: Settings,
) -> list[SearchResultItem]:
    payload_by_product = _best_payload_by_product(points)
    boosted: list[SearchResultItem] = []
    for result in results:
        payload = payload_by_product.get(result.product_id, {})
        boost = _image_score_boost(payload, filters, settings)
        boosted.append(result.model_copy(update={"score": result.score + boost}))
    boosted.sort(key=lambda item: item.score, reverse=True)
    return boosted


def _image_score_boost(payload: dict[str, object], filters: SearchFilter | None, settings: Settings) -> float:
    boost = 0.0
    if filters is not None:
        if filters.colors:
            product_colors = _payload_str_values(payload, "color_keys", "base_colour", "base_colour_vi")
            wanted_colors = set(color_filter_keys(filters.colors))
            if product_colors & wanted_colors:
                boost += 0.01
        if filters.category and _payload_has_category_keyword(payload, (_normalize_text(filters.category),)):
            boost += 0.01
    if settings.image_business_boost_enabled:
        boost += _business_boost(payload, settings.image_business_boost_weight)
    return boost


def _business_boost(payload: dict[str, object], weight: float) -> float:
    if weight <= 0:
        return 0.0
    return weight * _business_signal(payload)


def _business_signal(payload: dict[str, object]) -> float:
    inventory_count = payload.get("inventory_count")
    if payload.get("available") is not True:
        return 0.0
    if not isinstance(inventory_count, (int, float)) or isinstance(inventory_count, bool):
        return 0.0
    return 1.0 if inventory_count > 0 else 0.0


def _best_payload_by_product(points: Iterable[_ScoredPoint]) -> dict[str, dict[str, object]]:
    best: dict[str, _ScoredPoint] = {}
    for point in points:
        current = best.get(point.product_id)
        if current is None or point.score > current.score:
            best[point.product_id] = point
    return {product_id: point.payload for product_id, point in best.items()}


def _image_per_crop_limit(limit: int, crop_count: int, settings: Settings) -> int:
    candidate_pool_size = max(
        limit * settings.image_product_overfetch_factor,
        settings.image_candidate_pool_size,
    )
    if crop_count <= 1:
        return min(candidate_pool_size, settings.image_query_per_crop_limit_cap)
    scaled_limit = math.ceil(candidate_pool_size / crop_count) * 2
    return min(scaled_limit, settings.image_query_per_crop_limit_cap)


def _resolve_top_k(requested: int | None, default: int, settings: Settings) -> int:
    resolved = requested if requested is not None else default
    if resolved > settings.max_search_top_k:
        raise SearchTopKExceededError(resolved, settings.max_search_top_k)
    return resolved


def _hybrid_candidate_limit(output_top_k: int, settings: Settings) -> int:
    requested_limit = max(
        output_top_k * settings.hybrid_product_overfetch_factor,
        settings.hybrid_candidate_pool_size,
        settings.rerank_top_k if settings.rerank_enabled else 0,
    )
    # MAX_SEARCH_TOP_K limits the public request. Candidate overfetch is internal,
    # but can never return fewer points than the requested response size.
    return max(
        output_top_k,
        min(requested_limit, settings.hybrid_candidate_pool_cap),
    )


def _extract_scored_points(response: object) -> list[_ScoredPoint]:
    raw_points = getattr(response, "points", response)
    points: list[_ScoredPoint] = []
    for point in raw_points:
        payload = getattr(point, "payload", None) or {}
        product_id = payload.get("productId") or payload.get("product_id")
        if product_id:
            points.append(_ScoredPoint(product_id=str(product_id), score=float(point.score), payload=payload))
    return points


def _rank_points_by_detected_category(
    points: list[_ScoredPoint],
    crops: list[CropResult],
    settings: Settings,
) -> list[_ScoredPoint]:
    signal = _category_signal_for_crops(crops)
    if signal is None:
        return points

    class_id, confidence, keywords = signal
    if confidence < settings.image_yolo_category_soft_min_confidence:
        return points

    matched = [point for point in points if _payload_has_category_keyword(point.payload, keywords)]
    hard_filter_allowed = (
        class_id in settings.image_yolo_category_hard_filter_class_ids
        and confidence >= settings.image_yolo_category_hard_filter_confidence
    )
    candidates = matched if hard_filter_allowed and matched else points

    boost = settings.image_yolo_category_soft_boost_weight * confidence
    if boost <= 0:
        return candidates
    return [
        _ScoredPoint(
            product_id=point.product_id,
            score=(
                point.score + boost
                if _payload_has_category_keyword(point.payload, keywords)
                else point.score
            ),
            payload=point.payload,
        )
        for point in candidates
    ]


def _category_signal_for_crops(crops: list[CropResult]) -> tuple[int, float, tuple[str, ...]] | None:
    detected = [
        crop
        for crop in crops
        if crop.class_id is not None and not crop.is_fallback
    ]
    if not detected:
        return None

    best_crop = max(detected, key=lambda crop: crop.confidence)
    keywords = _CLASS_CATEGORY_KEYWORDS.get(best_crop.class_id, ())
    if not keywords or best_crop.class_id is None:
        return None
    return best_crop.class_id, best_crop.confidence, keywords


def _payload_has_category_keyword(payload: dict[str, object], keywords: tuple[str, ...]) -> bool:
    values = (
        _payload_values(payload.get("category_keys"))
        + _payload_values(payload.get("category_names"))
        + _payload_values(payload.get("category_names_vi"))
    )
    normalized_values = [_normalize_text(value) for value in values]
    return any(
        keyword in value
        for value in normalized_values
        for keyword in keywords
    )


def _load_catalog_metadata_from_qdrant(
    *,
    client: QdrantClient,
    collection_name: str,
    page_size: int = 256,
    max_pages: int = 40,
) -> CatalogMetadata:
    categories: set[str] = set()
    brands: set[str] = set()
    colors: set[str] = set()
    genders: set[str] = set()
    materials: set[str] = set()
    sizes: set[str] = set()
    normalized_titles: set[str] = set()
    title_product_ids: dict[str, set[str]] = defaultdict(set)
    product_filter_payloads: dict[str, dict[str, object]] = {}
    prices: list[float] = []
    offset: object | None = None

    for _ in range(max_pages):
        points, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="active", match=models.MatchValue(value=True))]
            ),
            limit=page_size,
            offset=offset,
            with_payload=[
                "category_keys",
                "brand_key",
                "color_keys",
                "material_keys",
                "size_keys",
                "gender_key",
                "category_names",
                "category_names_vi",
                "brand_name",
                "gender",
                "gender_vi",
                "base_colour",
                "base_colour_vi",
                "material",
                "material_vi",
                "option_value",
                "unified_size",
                "selling_price",
                "normalized_title",
                "normalized_title_vi",
                "productId",
                "product_id",
            ],
            with_vectors=False,
        )
        for point in points:
            payload = getattr(point, "payload", None) or {}
            categories.update(_normalized_payload_values(payload.get("category_keys")))
            categories.update(_normalized_payload_values(payload.get("category_names")))
            categories.update(_normalized_payload_values(payload.get("category_names_vi")))
            brands.update(_normalized_payload_values(payload.get("brand_key")))
            brands.update(_normalized_payload_values(payload.get("brand_name")))
            genders.update(_normalized_payload_values(payload.get("gender_key")))
            genders.update(_normalized_payload_values(payload.get("gender")))
            genders.update(_normalized_payload_values(payload.get("gender_vi")))
            colors.update(_normalized_payload_values(payload.get("color_keys")))
            colors.update(_normalized_payload_values(payload.get("base_colour")))
            colors.update(_normalized_payload_values(payload.get("base_colour_vi")))
            materials.update(_normalized_payload_values(payload.get("material_keys")))
            materials.update(_normalized_payload_values(payload.get("material")))
            materials.update(_normalized_payload_values(payload.get("material_vi")))
            sizes.update(_normalized_payload_values(payload.get("size_keys")))
            sizes.update(_normalized_payload_values(payload.get("option_value")))
            sizes.update(_normalized_payload_values(payload.get("unified_size")))
            normalized_titles.update(_normalized_payload_values(payload.get("normalized_title")))
            normalized_titles.update(_normalized_payload_values(payload.get("normalized_title_vi")))
            product_id = payload.get("productId") or payload.get("product_id")
            if product_id is not None:
                product_filter_payloads.setdefault(str(product_id), dict(payload))
                for title in _normalized_payload_values(
                    payload.get("normalized_title")
                ).union(
                    _normalized_payload_values(payload.get("normalized_title_vi"))
                ):
                    title_product_ids[title].add(str(product_id))
            price = _float_payload_value(payload.get("selling_price"))
            if price is not None:
                prices.append(price)
        if next_offset is None:
            break
        offset = next_offset

    return CatalogMetadata(
        categories=frozenset(categories),
        brands=frozenset(brands),
        colors=frozenset(colors),
        genders=frozenset(genders),
        materials=frozenset(materials),
        sizes=frozenset(sizes),
        normalized_titles=frozenset(normalized_titles),
        title_product_ids={
            title: tuple(sorted(product_ids))
            for title, product_ids in title_product_ids.items()
        },
        product_filter_payloads=product_filter_payloads,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
    )


def _normalized_payload_values(value: object) -> set[str]:
    return {_normalize_text(item).strip() for item in _payload_values(value) if str(item).strip()}


def _float_payload_value(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _payload_values(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _normalize_text(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _dedupe_by_product(points: Iterable[_ScoredPoint]) -> list[_ScoredPoint]:
    best: dict[str, _ScoredPoint] = {}
    for point in points:
        current = best.get(point.product_id)
        if current is None or point.score > current.score:
            best[point.product_id] = point
    return sorted(best.values(), key=lambda point: point.score, reverse=True)


def _text_recovery_reasons(
    points: Iterable[_ScoredPoint],
    query: str,
    constraints: ResolvedSearchConstraints | None,
    settings: Settings,
) -> tuple[str, ...]:
    if constraints is None or not constraints.has_inferred_hard_filters:
        return ()
    deduped = _dedupe_by_product(points)
    reasons: list[str] = []
    if any(
        constraint.field == "category"
        and constraint.mode == "hard"
        and constraint.source != "explicit"
        and constraint.match_type == "typo"
        for constraint in constraints.constraints
    ):
        reasons.append("category_typo")
    if len(deduped) < settings.text_filter_recovery_min_candidates:
        reasons.append("few_candidates")
    if (
        not deduped
        or deduped[0].score < settings.text_filter_recovery_min_top_score
    ):
        reasons.append("low_top_score")
    lexical_coverage = (
        _title_lexical_coverage(query, deduped[0].payload)
        if deduped
        else 0.0
    )
    if lexical_coverage < settings.text_filter_recovery_min_lexical_coverage:
        reasons.append("low_lexical_coverage")
    return tuple(dict.fromkeys(reasons))


def _title_lexical_coverage(query: str, payload: dict[str, object]) -> float:
    query_tokens = {
        token
        for token in normalize_query_text(query).split()
        if len(token) > 1 and token not in _GENERIC_RANKING_TOKENS
    }
    if not query_tokens:
        return 0.0
    title_tokens = _payload_str_values(
        payload,
        "normalized_title_tokens",
        "title_tokens",
    )
    if not title_tokens:
        for title in _payload_str_values(
            payload,
            "normalized_title_vi",
            "normalized_title",
        ):
            title_tokens.update(title.split())
    return len(query_tokens.intersection(title_tokens)) / len(query_tokens)


def _best_score_by_product(points: Iterable[_ScoredPoint]) -> dict[str, float]:
    best: defaultdict[str, float] = defaultdict(lambda: float("-inf"))
    for point in points:
        best[point.product_id] = max(best[point.product_id], point.score)
    return dict(best)


def _embedding_text_from_payload(payload: dict[str, object]) -> str | None:
    value = payload.get("embedding_text")
    return str(value) if value else None


def _content_by_product(points: Iterable[_ScoredPoint]) -> dict[str, str]:
    content: dict[str, str] = {}
    for point in points:
        text = _embedding_text_from_payload(point.payload)
        if text:
            content[point.product_id] = text
    return content


def _has_user_filters(filters: SearchFilter | None) -> bool:
    return bool(filters and filters.model_dump(exclude_none=True))


def _response(
    rewritten_query: str | None,
    filters: SearchFilter | None,
    results: list[SearchResultItem],
    detections: list[ImageDetectionBox] | None = None,
    route: SearchRoute | None = None,
    *,
    explicit_filters: SearchFilter | None = None,
    inferred_filters: SearchFilter | None = None,
    relaxed_filters: list[str] | None = None,
    constraint_failure_reason: str | None = None,
) -> SearchResponse:
    return SearchResponse(
        rewritten_query=rewritten_query,
        filters=filters if _has_user_filters(filters) else None,
        explicit_filters=(
            explicit_filters if _has_user_filters(explicit_filters) else None
        ),
        inferred_filters=(
            inferred_filters if _has_user_filters(inferred_filters) else None
        ),
        relaxed_filters=relaxed_filters or [],
        constraint_failure_reason=constraint_failure_reason,
        route=route,
        product_ids=[result.product_id for result in results],
        results=results,
        detections=detections or [],
    )


def _response_with_route(
    response: SearchResponse,
    route: SearchRoute,
    *,
    rewritten_query: str | None = None,
) -> SearchResponse:
    updates: dict[str, object] = {"route": route}
    if rewritten_query is not None and response.rewritten_query is None:
        updates["rewritten_query"] = rewritten_query
    return response.model_copy(update=updates)
