from __future__ import annotations

# Backward-compatible entrypoint that re-exports the MCP tools.

from . import api
from .server import (
    analyze_type_coverage,
    explore_abilities,
    find_encounters,
    get_breeding_info,
    get_descriptions,
    get_moves,
    get_pokemon,
    get_sprites,
    mcp,
    plan_evolutions,
    suggest_moveset,
)

# Re-export helpers used by tests and legacy integrations.
_cached_fetch = api._cached_fetch
_fetch_json = api._fetch_json
_get_move_data = api._get_move_data
_get_type_relations = api._get_type_relations
_list_all_types = api._list_all_types
_lookup = api._lookup
_extract_effect = api._extract_effect
_extract_short_effect = api._extract_short_effect

import pypokedex  # noqa: E402 - re-exported for test monkeypatching


if __name__ == "__main__":
    mcp.run()
