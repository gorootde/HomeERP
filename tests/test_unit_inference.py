"""Coverage for backend/unit_inference.py (pure heuristics, no DB)."""
import pytest

from backend.unit_inference import (
    canonical_token,
    category_dimension,
    guess_dimension_from_abbr,
    keyword_dimension,
    parse_size,
)


@pytest.mark.parametrize(
    "raw, value, token, dimension",
    [
        ("0.33 l", 0.33, "l", "volume"),
        ("1,5 l", 1.5, "l", "volume"),
        ("500 g", 500.0, "g", "mass"),
        ("500g", 500.0, "g", "mass"),
        ("1 kg", 1.0, "kg", "mass"),
        ("33cl", 33.0, "cl", "volume"),
        ("250 ml", 250.0, "ml", "volume"),
        ("6x50g", 50.0, "g", "mass"),
        ("6 x 50 g", 50.0, "g", "mass"),
        ("1 Stück", 1.0, "stück", "count"),
        ("6er Pack 0,33 l", 0.33, "l", "volume"),
        ("ca. 300 g", 300.0, "g", "mass"),
        ("1 pièce", 1.0, "pièce", None),
        ("", None, None, None),
        (None, None, None, None),
        ("no numbers here", None, None, None),
    ],
)
def test_parse_size(raw, value, token, dimension):
    assert parse_size(raw) == {"value": value, "token": token, "dimension": dimension}


@pytest.mark.parametrize(
    "abbr, dimension",
    [
        ("g", "mass"), ("kg", "mass"), ("mg", "mass"), ("Gramm", "mass"),
        ("l", "volume"), ("ml", "volume"), ("cl", "volume"), ("Liter", "volume"),
        ("Stk", "count"), ("Stück", "count"), ("pcs", "count"),
        ("cm", "length"),
        ("Bund", None), ("", None), (None, None),
    ],
)
def test_guess_dimension_from_abbr(abbr, dimension):
    assert guess_dimension_from_abbr(abbr) == dimension


def test_canonical_token():
    assert canonical_token("Gramm") == "g"
    assert canonical_token("LITER") == "l"
    assert canonical_token("stk.") == "stück"
    assert canonical_token("bund") is None


@pytest.mark.parametrize(
    "name, dimension",
    [
        ("Weizenmehl Type 405", "mass"),
        ("Basmati Reis", "mass"),
        ("Kristallzucker", "mass"),
        ("Coca-Cola Zero", "volume"),
        ("Frische Vollmilch", "volume"),
        ("Sonnenblumenöl", "volume"),
        ("Bio Orangensaft", "volume"),
        ("6 Frische Eier", "count"),
        ("Schrauben verzinkt", None),
        ("", None),
        (None, None),
    ],
)
def test_keyword_dimension(name, dimension):
    assert keyword_dimension(name) == dimension


@pytest.mark.parametrize(
    "tags, dimension",
    [
        (["en:sodas", "en:beverages"], "volume"),
        (["en:flours", "en:cereals"], "mass"),
        (["de:eier", "en:eggs"], "count"),
        (["en:snacks"], None),
        (["en:sunflower-oils"], "volume"),
        ([], None),
        (None, None),
    ],
)
def test_category_dimension(tags, dimension):
    assert category_dimension(tags) == dimension
