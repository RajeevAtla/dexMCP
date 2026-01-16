"""Shared API helpers for PokeAPI and pypokedex access."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import requests

import pypokedex

# requests is used for direct PokeAPI lookups that supplement the pypokedex client.

# Types that exist in the API but are not used for standard battles.
IGNORED_TYPES = {"unknown", "shadow"}


@lru_cache(maxsize=256)
def _cached_fetch(url: str) -> Dict:
    """Fetch JSON data from a URL with caching.

    Args:
        url: PokeAPI URL to request.

    Returns:
        Parsed JSON response data.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the response cannot be decoded as JSON.
    """
    # Cache raw HTTP responses so repeated tooling calls do not spam the public API.
    # This keeps the server responsive and avoids rate-limiting.
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def _fetch_json(url: str, context: str) -> Dict:
    """Fetch JSON data and wrap errors with context.

    Args:
        url: PokeAPI URL to request.
        context: Description used for error messages.

    Returns:
        Parsed JSON response data.

    Raises:
        ValueError: If the request fails or JSON decoding fails.
    """
    # Wrap lower-level exceptions in a consistent, user-facing error.
    try:
        return _cached_fetch(url)
    except (requests.RequestException, ValueError) as exc:
        raise ValueError(f"Failed to fetch {context}: {exc}") from exc


def _lookup(name_or_dex: str):
    """Fetch a pypokedex.Pokemon by name or dex number.

    Args:
        name_or_dex: Pokemon name (case-insensitive) or dex number.

    Returns:
        The pypokedex Pokemon object.

    Raises:
        ValueError: If the Pokemon cannot be found.
    """
    # pypokedex caches responses locally, so repeat lookups avoid hitting the public API.
    # Use numeric dex IDs when the input is digits only.
    try:
        if name_or_dex.isdigit():
            return pypokedex.get(dex=int(name_or_dex))
        return pypokedex.get(name=name_or_dex.lower())
    except Exception as exc:
        # Let the client see a clean error string
        raise ValueError(f"Could not find Pokemon '{name_or_dex}': {exc}") from exc


@lru_cache(maxsize=1)
def _list_all_types() -> List[str]:
    """Return the canonical list of Pokemon types.

    Returns:
        Sorted list of type names excluding ignored types.
    """
    # Grab the canonical list of types once per process; the result drives coverage math.
    # Sort to keep deterministic ordering for reports/tests.
    data = _fetch_json("https://pokeapi.co/api/v2/type", context="type listing")
    types = [entry["name"] for entry in data.get("results", [])]
    return sorted([type_name for type_name in types if type_name not in IGNORED_TYPES])


@lru_cache(maxsize=64)
def _get_type_relations(type_name: str) -> Dict[str, List[str]]:
    """Fetch type matchup relations from PokeAPI.

    Args:
        type_name: Type name to look up.

    Returns:
        Mapping of damage relation keys to lists of type names.
    """
    # Damage relations are used to compute defensive multipliers.
    data = _fetch_json(
        f"https://pokeapi.co/api/v2/type/{type_name.lower()}",
        context=f"type data for {type_name}",
    )
    relations = data.get("damage_relations", {})
    return {
        key: [entry["name"] for entry in relations.get(key, [])]
        for key in (
            "double_damage_to",
            "half_damage_to",
            "no_damage_to",
        )
    }


@lru_cache(maxsize=64)
def _get_move_data(move_name: str) -> Dict:
    """Fetch move metadata from PokeAPI.

    Args:
        move_name: Move name to look up.

    Returns:
        Move metadata payload from PokeAPI.
    """
    # Move data provides power/accuracy/type and effect text for scoring.
    return _fetch_json(
        f"https://pokeapi.co/api/v2/move/{move_name.lower()}",
        context=f"move data for {move_name}",
    )


def _extract_short_effect(entries: List[Dict]) -> str | None:
    """Extract the English short effect entry.

    Args:
        entries: List of effect entries from PokeAPI.

    Returns:
        English short effect text, if available.
    """
    # PokeAPI includes multiple languages; pull only English for summaries.
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("short_effect")
    return None


def _extract_effect(entries: List[Dict]) -> str | None:
    """Extract the English effect entry.

    Args:
        entries: List of effect entries from PokeAPI.

    Returns:
        English effect text, if available.
    """
    # PokeAPI includes multiple languages; pull only English for summaries.
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("effect")
    return None
