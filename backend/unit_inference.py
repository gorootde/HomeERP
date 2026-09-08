"""Heuristics for guessing a product's unit / physical dimension.

Pure functions only — no DB, no network — so they stay trivially testable and
can be reused from an Alembic migration (see the ``dimension`` backfill).

The generic pivot is the *dimension* (``mass`` / ``volume`` / ``count`` /
``length``): infer that from whatever signal is available (a parsed package
size, an OpenFoodFacts category tag, or a keyword in the product name), then let
the caller pick the user's preferred unit of that dimension.
"""
from __future__ import annotations

import re

DIMENSIONS = ("mass", "volume", "count", "length", "other")

# Normalised size / abbreviation token -> (dimension, canonical abbreviation).
KNOWN_UNIT_TOKENS: dict[str, tuple[str, str]] = {
    # ── mass ──
    "g": ("mass", "g"), "gr": ("mass", "g"), "gm": ("mass", "g"),
    "gramm": ("mass", "g"), "gramme": ("mass", "g"), "gram": ("mass", "g"),
    "gramms": ("mass", "g"), "grams": ("mass", "g"), "grammes": ("mass", "g"),
    "kg": ("mass", "kg"), "kgs": ("mass", "kg"), "kilo": ("mass", "kg"),
    "kilos": ("mass", "kg"), "kilogramm": ("mass", "kg"), "kilogram": ("mass", "kg"),
    "kilograms": ("mass", "kg"), "kilogramme": ("mass", "kg"),
    "mg": ("mass", "mg"), "milligramm": ("mass", "mg"), "milligram": ("mass", "mg"),
    # ── volume ──
    "l": ("volume", "l"), "ltr": ("volume", "l"), "lt": ("volume", "l"),
    "liter": ("volume", "l"), "litre": ("volume", "l"), "liters": ("volume", "l"),
    "litres": ("volume", "l"),
    "ml": ("volume", "ml"), "milliliter": ("volume", "ml"), "millilitre": ("volume", "ml"),
    "cl": ("volume", "cl"), "centiliter": ("volume", "cl"), "centilitre": ("volume", "cl"),
    "dl": ("volume", "dl"), "deciliter": ("volume", "dl"), "decilitre": ("volume", "dl"),
    # ── length ──
    "mm": ("length", "mm"), "cm": ("length", "cm"),
    "meter": ("length", "m"), "metre": ("length", "m"),
    # ── count ──
    "stk": ("count", "stück"), "stück": ("count", "stück"), "stueck": ("count", "stück"),
    "stck": ("count", "stück"), "st": ("count", "stück"), "pc": ("count", "stück"),
    "pcs": ("count", "stück"), "piece": ("count", "stück"), "pieces": ("count", "stück"),
    "x": ("count", "stück"), "unit": ("count", "stück"), "units": ("count", "stück"),
}

# OpenFoodFacts ``categories_tags`` leaf (language prefix stripped) -> dimension.
OFF_CATEGORY_DIMENSION: dict[str, str] = {
    # volume
    "beverages": "volume", "drinks": "volume", "sodas": "volume", "waters": "volume",
    "spring-waters": "volume", "mineral-waters": "volume", "juices": "volume",
    "fruit-juices": "volume", "nectars": "volume", "milks": "volume",
    "plant-based-beverages": "volume", "plant-milks": "volume", "syrups": "volume",
    "iced-teas": "volume", "energy-drinks": "volume", "beers": "volume",
    "wines": "volume", "alcoholic-beverages": "volume", "olive-oils": "volume",
    "vegetable-oils": "volume", "sunflower-oils": "volume", "oils": "volume",
    "vinegars": "volume", "sauces": "volume", "creams": "volume",
    # mass
    "flours": "mass", "wheat-flours": "mass", "flour": "mass", "sugars": "mass",
    "rices": "mass", "pastas": "mass", "dried-pastas": "mass", "cereals": "mass",
    "breakfast-cereals": "mass", "flakes": "mass", "coffees": "mass",
    "ground-coffees": "mass", "coffee-beans": "mass", "teas": "mass",
    "salts": "mass", "sea-salts": "mass", "spices": "mass", "legumes": "mass",
    "lentils": "mass", "nuts": "mass",
    # count
    "eggs": "count", "chicken-eggs": "count",
}

# Substrings in the product name that hint at a dimension (German base + English).
NAME_KEYWORDS: dict[str, list[str]] = {
    "mass": [
        "mehl", "flour", "zucker", "sugar", "reis", "rice", "salz", "salt",
        "nudel", "nudeln", "pasta", "spaghetti", "penne", "kaffee", "coffee",
        "grieß", "griess", "haferflocke", "oats", "oatmeal", "müsli", "muesli",
        "couscous", "linse", "linsen", "lentil", "bohnen", "erbsen", "butter",
        "käse", "cheese", "hackfleisch", "schinken", "wurst", "mandel",
        "walnuss", "haselnuss", "cashew", "erdnuss", "backpulver", "puderzucker",
        "kakao", "cocoa",
    ],
    "volume": [
        "cola", "limonade", "limo", "saft", "juice", "milch", "milk", "wasser",
        "water", "essig", "vinegar", "bier", "beer", "wein", "wine", "sekt",
        "prosecco", "sirup", "syrup", "sauce", "soße", "sosse", "brühe",
        "bruehe", "sahne", "cream", "smoothie", "eistee", "softdrink", "nektar",
        "spülmittel", "spuelmittel", "shampoo", "duschgel", "waschmittel",
        "olivenöl", "sonnenblumenöl", "rapsöl", "speiseöl", "pflanzenöl",
        "kokosöl", "öl", "oil",
    ],
    "count": [
        "eier", "eggs", "egg", "riegel", "rolle", "beutel", "teebeutel",
        "kapsel", "kapseln", "dose", "büchse", "buechse",
    ],
}

_NUM = r"\d+(?:[.,]\d+)?"
_MULTIPACK_RE = re.compile(rf"(\d+)\s*[x×*]\s*({_NUM})\s*([^\W\d_]+)", re.UNICODE)
_SINGLE_RE = re.compile(rf"({_NUM})\s*([^\W\d_]+)", re.UNICODE)


def canonical_token(text: str | None) -> str | None:
    """Map a raw unit token / abbreviation to its canonical form, if known."""
    if not text:
        return None
    key = text.strip().lower().rstrip(".")
    known = KNOWN_UNIT_TOKENS.get(key)
    return known[1] if known else None


def guess_dimension_from_abbr(text: str | None) -> str | None:
    """Best-effort dimension for a unit abbreviation or name ('kg' -> 'mass')."""
    if not text:
        return None
    key = text.strip().lower().rstrip(".")
    known = KNOWN_UNIT_TOKENS.get(key)
    return known[0] if known else None


def parse_size(size: str | None) -> dict:
    """Parse an OpenFoodFacts-style quantity string.

    ``"0,33 l"`` -> ``{"value": 0.33, "token": "l", "dimension": "volume"}``.
    Handles decimal comma, missing space (``"500ml"``) and multipacks
    (``"6x50g"`` -> per-item ``50``). Returns all-``None`` when nothing parses.
    """
    empty = {"value": None, "token": None, "dimension": None}
    if not size:
        return empty
    s = str(size).strip().lower()

    m = _MULTIPACK_RE.search(s)
    if m:
        candidates = [(m.group(2), m.group(3))]
    else:
        candidates = [(mm.group(1), mm.group(2)) for mm in _SINGLE_RE.finditer(s)]
    if not candidates:
        return empty

    # A messy string ("6er Pack 0,33 l") may hold several number+word pairs;
    # prefer the one whose word is an actual unit token.
    raw_value, raw_token = next(
        (c for c in candidates if c[1] in KNOWN_UNIT_TOKENS), candidates[0]
    )
    try:
        value = float(raw_value.replace(",", "."))
    except ValueError:
        value = None
    dim, canon = KNOWN_UNIT_TOKENS.get(raw_token, (None, raw_token))
    return {"value": value, "token": canon, "dimension": dim}


def category_dimension(tags) -> str | None:
    """Dimension implied by an OpenFoodFacts ``categories_tags`` list."""
    leaves = [str(t).split(":", 1)[-1].strip().lower() for t in (tags or [])]
    for leaf in leaves:
        if leaf in OFF_CATEGORY_DIMENSION:
            return OFF_CATEGORY_DIMENSION[leaf]
    for leaf in leaves:
        for key, dim in OFF_CATEGORY_DIMENSION.items():
            if key in leaf:
                return dim
    return None


def _matches(keyword: str, text: str) -> bool:
    if len(keyword) >= 4:
        return keyword in text
    # Short keywords ("öl", "egg") only match as a standalone word to avoid
    # false hits inside unrelated words.
    return re.search(rf"(?<![^\W\d_]){re.escape(keyword)}(?![^\W\d_])", text) is not None


def keyword_dimension(name: str | None) -> str | None:
    """Dimension implied by a keyword in the product name ('Weizenmehl' -> 'mass')."""
    if not name:
        return None
    text = str(name).strip().lower()
    for dim, keywords in NAME_KEYWORDS.items():
        if any(_matches(kw, text) for kw in keywords):
            return dim
    return None
