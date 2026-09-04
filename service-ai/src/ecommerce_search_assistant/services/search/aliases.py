from __future__ import annotations

from ecommerce_search_assistant.services.search.normalization import normalize_alias_key, normalize_query_text


def _registry(values: dict[str, str]) -> dict[str, str]:
    registry: dict[str, str] = {}
    for alias, canonical in values.items():
        registry[normalize_alias_key(alias)] = canonical
        registry[normalize_query_text(alias)] = canonical
    return registry


COLOR_ALIASES = _registry(
    {
        "black": "black",
        "den": "black",
        "mau den": "black",
        "white": "white",
        "trang": "white",
        "mau trang": "white",
        "cream": "cream",
        "kem": "cream",
        "mau kem": "cream",
        "ecru": "cream",
        "ivory": "cream",
        "off white": "cream",
        "off-white": "cream",
        "trang nga": "cream",
        "mau trang nga": "cream",
        # Vanilla is a distinct catalog shade. Keep the Vietnamese label on
        # the same key instead of allowing the LLM to approximate it as
        # lavender/purple.
        "vanilla": "vanilla",
        "vani": "vanilla",
        "mau vani": "vanilla",
        "beige": "beige",
        "be": "beige",
        "mau be": "beige",
        # Long blue phrases must stay ahead of the bare "xanh"/"blue" family token
        # so "xanh da troi" resolves to light blue, not blue.
        "xanh da troi": "light blue",
        "xanh da trời": "light blue",
        "light blue": "light blue",
        "sky blue": "light blue",
        "xanh nhat": "light blue",
        "xanh sang": "light blue",
        "xanh navy": "navy",
        "xanh dam": "navy",
        "navy blue": "navy",
        "navy": "navy",
        "cham dam": "dark indigo",
        "chàm đậm": "dark indigo",
        "dark indigo": "dark indigo",
        "xanh olive": "olive",
        "xanh reu": "olive",
        "olive": "olive",
        "xanh la": "green",
        "xanh luc": "green",
        "green": "green",
        "blue": "blue",
        "xanh": "blue",
        "xanh duong": "blue",
        "brown": "brown",
        "nau": "brown",
        "gray": "gray",
        "grey": "gray",
        "xam": "gray",
        "ghi": "gray",
        "silver": "silver",
        "bac": "silver",
        "tan": "tan",
        "pink": "pink",
        "hong": "pink",
        "mau hong": "pink",
        "fuchsia": "pink",
        # Single-syllable Vietnamese color words are only registered with the
        # explicit "mau" prefix. Their accent-stripped forms collide with very
        # common words ("tim"->tìm/search, "do"->do/đó, "vang"->vâng, "cam"->cảm),
        # so the bare token would misfire on ordinary queries.
        "red": "red",
        "mau do": "red",
        "do do": "red",
        "yellow": "yellow",
        "mau vang": "yellow",
        "vang tuoi": "yellow",
        "orange": "orange",
        "mau cam": "orange",
        "purple": "purple",
        "mau tim": "purple",
        "multicolor": "multicolor",
        "multicolour": "multicolor",
        "nhieu mau": "multicolor",
        "da mau": "multicolor",
        "mau da mau": "multicolor",
        "rose gold": "rose gold",
        "vang hong": "rose gold",
    }
)

MATERIAL_ALIASES = _registry(
    {
        "cotton": "cotton",
        "vai cotton": "cotton",
        "denim": "denim",
        "jean": "denim",
        "da": "leather",
        "leather": "leather",
        "len": "wool",
        "wool": "wool",
        "polyester": "polyester",
        "elastane": "elastane",
        "spandex": "elastane",
        "viscose": "viscose",
        "rayon": "viscose",
        "lyocell": "lyocell",
        "tencel": "lyocell",
        "hemp": "hemp",
        "gai dau": "hemp",
        "ramie": "ramie",
        "poplin": "poplin",
        "vai poplin": "poplin",
        "ni": "fleece",
        "fleece": "fleece",
    }
)

USE_CASE_ALIASES = _registry(
    {
        "school": "school",
        "di hoc": "school",
        "work": "office",
        "office": "office",
        "cong so": "office",
        "van phong": "office",
        "di lam": "office",
        "event": "event",
        "su kien": "event",
        "du tiec": "event",
        "party": "event",
        "streetwear": "streetwear",
        "street wear": "streetwear",
        "dao pho": "streetwear",
        "travel": "travel",
        "du lich": "travel",
        "winter": "winter",
        "mua dong": "winter",
        "thu dong": "winter",
        "autumn winter": "winter",
        "cold weather": "winter",
        "casual": "casual",
        "di choi": "casual",
        "hang ngay": "casual",
        "sports": "sports",
        "the thao": "sports",
        "running": "running",
        "chay bo": "running",
        "gym": "gym",
        "tap gym": "gym",
        "outdoor": "outdoor",
        "leo nui": "outdoor",
    }
)

GENDER_ALIASES = _registry(
    {
        "women": "women",
        "woman": "women",
        "female": "women",
        "ladies": "women",
        "nu": "women",
        "phai nu": "women",
        "danh cho nu": "women",
        "cho nu": "women",
        "men": "men",
        "man": "men",
        "male": "men",
        "nam": "men",
        "phai nam": "men",
        "danh cho nam": "men",
        "cho nam": "men",
        "unisex": "unisex",
        "unisex adult": "unisex",
    }
)

BRAND_ALIASES = _registry(
    {
        "adidas": "adidas",
        "nike": "nike",
        "puma": "puma",
        "reebok": "reebok",
        "zara": "zara",
        "hm": "h&m",
        "h m": "h&m",
        "h&m": "h&m",
        "h & m": "h&m",
        "uniqlo": "uniqlo",
        "mlb": "mlb",
        "converse": "converse",
        "vans": "vans",
        "canada goose": "canada goose",
    }
)

SIZE_ALIASES = _registry(
    {
        "extra small": "xs",
        "small": "s",
        "medium": "m",
        "large": "l",
        "extra large": "xl",
        "one size": "one-size",
        "onesize": "one-size",
        "free size": "one-size",
    }
)

# Natural Vietnamese material and usage expressions that commonly appear in
# conversational search. Keep these in the shared registry so rule extraction,
# indexing canonicalization, and filter normalization agree on one value.
MATERIAL_ALIASES.update(
    _registry(
        {
            'vai bong': 'cotton',
            'polyamide': 'polyamide',
            'nylon': 'polyamide',
            'ni long': 'polyamide',
        }
    )
)
USE_CASE_ALIASES.update(
    _registry(
        {
            'xuong pho': 'streetwear',
            'mac xuong pho': 'streetwear',
            'mac cong so': 'office',
        }
    )
)
