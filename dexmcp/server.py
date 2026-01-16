"""Expose FastMCP tools for Pokedex lookups and analysis."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .abilities import explore_abilities as _explore_abilities
from .breeding import get_breeding_info as _get_breeding_info
from .coverage import analyze_type_coverage as _analyze_type_coverage
from .encounters import find_encounters as _find_encounters
from .evolution import plan_evolutions as _plan_evolutions
from .moveset import suggest_moveset as _suggest_moveset
from .pokemon import (
    get_descriptions as _get_descriptions,
    get_moves as _get_moves,
    get_pokemon as _get_pokemon,
    get_sprites as _get_sprites,
)
from .models import (
    AbilityExplorerResult,
    BreedingInfo,
    EncounterReport,
    EvolutionReport,
    Move,
    MovesetRecommendation,
    PokemonSummary,
    SpriteURL,
    TypeCoverageReport,
)

# FastMCP tool definitions that surface Pokedex data for agentic clients.
# Each decorated function becomes a structured tool discoverable by MCP hosts.

# Create the FastMCP server instance that registers the tool functions.
mcp = FastMCP("DexMCP Server")


@mcp.tool()
def get_pokemon(name_or_dex: str) -> PokemonSummary:
    """Fetch a Pokemon summary for the given identifier.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Summary stats, typing, and measurements for the Pokemon.
    """
    # Delegate to the core helper for consistent behavior.
    return _get_pokemon(name_or_dex)


@mcp.tool()
def get_moves(name_or_dex: str, game: str) -> list[Move]:
    """List the learnset for a Pokemon in a specific game.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: PokeAPI game identifier (e.g., "scarlet-violet").

    Returns:
        Moves the Pokemon can learn in the requested game.
    """
    # Delegate to the core helper for consistent behavior.
    return _get_moves(name_or_dex, game)


@mcp.tool()
def get_sprites(name_or_dex: str, side: str = "front", variant: str = "default") -> SpriteURL:
    """Resolve a sprite URL for a Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.
        side: Sprite side ("front" or "back").
        variant: Sprite variant (e.g., "default", "shiny").

    Returns:
        Sprite URL with the requested side and variant.
    """
    # Delegate to the core helper for consistent behavior.
    return _get_sprites(name_or_dex, side=side, variant=variant)


@mcp.tool()
def get_descriptions(name_or_dex: str, language: str = "en") -> dict[str, str]:
    """Fetch localized Pokedex flavor text.

    Args:
        name_or_dex: Pokemon name or national dex number.
        language: Language code for flavor text.

    Returns:
        Mapping of game version to flavor text.
    """
    # Delegate to the core helper for consistent behavior.
    return _get_descriptions(name_or_dex, language=language)


@mcp.tool()
def analyze_type_coverage(names_or_dexes: list[str]) -> TypeCoverageReport:
    """Summarize defensive type coverage for a roster.

    Args:
        names_or_dexes: Pokemon names or dex numbers to analyze.

    Returns:
        Coverage report with matchup counts and notable weaknesses.
    """
    # Delegate to the core helper for consistent behavior.
    return _analyze_type_coverage(names_or_dexes)


@mcp.tool()
def explore_abilities(name_or_dex: str) -> AbilityExplorerResult:
    """Retrieve ability details for a Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Ability names and effect text details.
    """
    # Delegate to the core helper for consistent behavior.
    return _explore_abilities(name_or_dex)


@mcp.tool()
def plan_evolutions(name_or_dex: str) -> EvolutionReport:
    """Enumerate evolution paths that include the Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Evolution paths and triggers.
    """
    # Delegate to the core helper for consistent behavior.
    return _plan_evolutions(name_or_dex)


@mcp.tool()
def find_encounters(name_or_dex: str) -> EncounterReport:
    """Find wild encounter locations for a Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Encounter locations grouped by version and method.
    """
    # Delegate to the core helper for consistent behavior.
    return _find_encounters(name_or_dex)


@mcp.tool()
def get_breeding_info(name_or_dex: str, game: str | None = None) -> BreedingInfo:
    """Summarize breeding details for a Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: Optional game identifier for egg move filtering.

    Returns:
        Breeding info including egg groups, hatch steps, and egg moves.
    """
    # Delegate to the core helper for consistent behavior.
    return _get_breeding_info(name_or_dex, game=game)


@mcp.tool()
def suggest_moveset(
    name_or_dex: str,
    game: str,
    limit: int = 4,
    include_tm: bool = False,
) -> MovesetRecommendation:
    """Recommend a moveset for a Pokemon in a game.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: PokeAPI game identifier to scope learnsets.
        limit: Maximum number of recommendations to return.
        include_tm: Whether to include TM moves.

    Returns:
        Ranked move recommendations based on simple heuristics.
    """
    # Delegate to the core helper for consistent behavior.
    return _suggest_moveset(name_or_dex, game=game, limit=limit, include_tm=include_tm)
