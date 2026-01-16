from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import requests

import pypokedex

# requests is used for direct PokeAPI lookups that supplement the pypokedex client.

IGNORED_TYPES = {"unknown", "shadow"}


@lru_cache(maxsize=256)
def _cached_fetch(url: str) -> Dict:
    # Cache raw HTTP responses so repeated tooling calls do not spam the public API.
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def _fetch_json(url: str, context: str) -> Dict:
    try:
        return _cached_fetch(url)
    except (requests.RequestException, ValueError) as exc:
        raise ValueError(f"Failed to fetch {context}: {exc}") from exc


def _lookup(name_or_dex: str):
    """Internal helper to fetch a pypokedex.Pokemon by name (case-insensitive) or dex number."""
    # pypokedex caches responses locally, so repeat lookups avoid hitting the public API.
    try:
        if name_or_dex.isdigit():
            return pypokedex.get(dex=int(name_or_dex))
        return pypokedex.get(name=name_or_dex.lower())
    except Exception as exc:
        # Let the client see a clean error string
        raise ValueError(f"Could not find Pokemon '{name_or_dex}': {exc}") from exc


@lru_cache(maxsize=1)
def _list_all_types() -> List[str]:
    # Grab the canonical list of types once per process; the result drives coverage math.
    data = _fetch_json("https://pokeapi.co/api/v2/type", context="type listing")
    types = [entry["name"] for entry in data.get("results", [])]
    return sorted([type_name for type_name in types if type_name not in IGNORED_TYPES])


@lru_cache(maxsize=64)
def _get_type_relations(type_name: str) -> Dict[str, List[str]]:
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
    return _fetch_json(
        f"https://pokeapi.co/api/v2/move/{move_name.lower()}",
        context=f"move data for {move_name}",
    )


def _extract_short_effect(entries: List[Dict]) -> str | None:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("short_effect")
    return None


def _extract_effect(entries: List[Dict]) -> str | None:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("effect")
    return None
