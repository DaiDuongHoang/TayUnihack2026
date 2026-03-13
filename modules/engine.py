"""
engine.py – Outfit recommendation logic.

The engine matches clothing items stored in the wardrobe against the current
Melbourne weather conditions and returns a ranked list of outfit suggestions.

TODO (team): Replace the placeholder scoring with a smarter algorithm
(e.g. ML-based ranking, user preferences, colour coordination).
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recommend_outfit(wardrobe_items: list[dict], weather_tags: list[str]) -> list[dict]:
    """
    Return a ranked list of wardrobe items suitable for the current weather.

    Parameters
    ----------
    wardrobe_items:
        List of item dicts as returned by ``database.get_all_items()``.
    weather_tags:
        List of weather descriptors as returned by ``weather_api.weather_to_tags()``,
        e.g. ``["cold", "rainy"]``.

    Returns
    -------
    list[dict]
        Wardrobe items sorted by relevance score (highest first).
        Each item dict is augmented with a ``"score"`` key.

    TODO (team): Implement colour-matching, outfit completeness checks
    (top + bottom + shoes), and user style preferences.
    """
    scored = []
    for item in wardrobe_items:
        score = _score_item(item, weather_tags)
        scored.append({**item, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def build_complete_outfit(
    wardrobe_items: list[dict], weather_tags: list[str]
) -> dict[str, dict | None]:
    """
    Attempt to build a complete outfit (top + bottom + outerwear + shoes).

    Returns a dict mapping category → best matching item (or None if unavailable).

    TODO (team): Add colour coordination and style matching.
    """
    ranked = recommend_outfit(wardrobe_items, weather_tags)

    outfit: dict[str, dict | None] = {
        "top": None,
        "bottom": None,
        "outerwear": None,
        "shoes": None,
    }
    for item in ranked:
        category = item.get("category", "unknown")
        if category in outfit and outfit[category] is None:
            outfit[category] = item

    return outfit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _score_item(item: dict, weather_tags: list[str]) -> float:
    """
    Assign a relevance score to a wardrobe item given the weather tags.

    Scoring rules (placeholder):
    - +1 for each weather tag present in the item's tag string.
    - 0 baseline.

    TODO (team): Replace with a richer scoring model.
    """
    item_tags = {t.strip().lower() for t in item.get("tags", "").split(",") if t.strip()}
    matches = sum(1 for tag in weather_tags if tag.lower() in item_tags)
    return float(matches)
