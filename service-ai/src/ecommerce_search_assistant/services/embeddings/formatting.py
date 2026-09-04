from collections.abc import Iterable

from ecommerce_search_assistant.schemas.product import ProductIndexItem

_SEARCH_ATTRIBUTE_KEYS = (
    "search_category",
    "search_category_vi",
    "search_attributes",
    "search_attributes_vi",
    "search_keywords_vi",
)


def build_product_embedding_text(item: ProductIndexItem) -> str:
    category_names = _join(category.category_name for category in item.categories)
    category_names_vi = _join(category.category_name_vi for category in item.categories)
    category_levels = _join(category.category_level for category in item.categories)

    lines = (
        f"Product display name: {item.product_display_name or ''}",
        f"Vietnamese product display name: {item.product_display_name_vi or ''}",
        f"Brand name: {item.brand_name or ''}",
        f"Base colour: {item.base_colour or ''}",
        f"Vietnamese base colour: {item.base_colour_vi or ''}",
        f"Material: {item.material or ''}",
        f"Vietnamese material: {item.material_vi or ''}",
        f"Fit: {item.fit or ''}",
        f"Vietnamese fit: {item.fit_vi or ''}",
        f"Season: {item.season or ''}",
        f"Vietnamese season: {item.season_vi or ''}",
        f"Product usage: {item.product_usage or ''}",
        f"Vietnamese product usage: {item.product_usage_vi or ''}",
        f"Gender: {item.gender or ''}",
        f"Vietnamese gender: {item.gender_vi or ''}",
        f"Description: {item.description or ''}",
        f"Vietnamese description: {item.description_vi or ''}",
        f"Category names: {category_names}",
        f"Vietnamese category names: {category_names_vi}",
        f"Category levels: {category_levels}",
        f"Option values: {_join(item.option_value)}",
        f"Unified sizes: {_join(item.unified_size)}",
        f"Search attributes: {_search_attribute_values(item)}",
    )
    return "\n".join(lines)


def _search_attribute_values(item: ProductIndexItem) -> str:
    values: list[str] = []
    for key in _SEARCH_ATTRIBUTE_KEYS:
        preferred = item.attributes_vi if key.endswith("_vi") else item.attributes
        fallback = item.attributes if key.endswith("_vi") else item.attributes_vi
        value = preferred.get(key) or fallback.get(key)
        if value:
            values.append(value)
    return _join(values)


def _join(values: Iterable[object]) -> str:
    return ", ".join(str(value) for value in values if value)
