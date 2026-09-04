from qdrant_client import models

from ecommerce_search_assistant.infrastructure.qdrant import _PAYLOAD_INDEXES


def test_qdrant_payload_indexes_match_compact_filter_payload() -> None:
    assert _PAYLOAD_INDEXES == (
        ("product_id", models.PayloadSchemaType.KEYWORD),
        ("category_codes", models.PayloadSchemaType.KEYWORD),
        ("category_keys", models.PayloadSchemaType.KEYWORD),
        ("category_aliases", models.PayloadSchemaType.KEYWORD),
        ("brand_key", models.PayloadSchemaType.KEYWORD),
        ("color_keys", models.PayloadSchemaType.KEYWORD),
        ("material_keys", models.PayloadSchemaType.KEYWORD),
        ("use_case_keys", models.PayloadSchemaType.KEYWORD),
        ("size_keys", models.PayloadSchemaType.KEYWORD),
        ("gender_key", models.PayloadSchemaType.KEYWORD),
        ("audience_keys", models.PayloadSchemaType.KEYWORD),
        ("normalized_title", models.PayloadSchemaType.KEYWORD),
        ("normalized_title_vi", models.PayloadSchemaType.KEYWORD),
        ("normalized_title_tokens", models.PayloadSchemaType.KEYWORD),
        ("metadata_schema_version", models.PayloadSchemaType.INTEGER),
        ("active", models.PayloadSchemaType.BOOL),
        ("selling_price", models.PayloadSchemaType.FLOAT),
    )
