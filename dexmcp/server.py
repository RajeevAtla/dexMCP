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

mcp = FastMCP("DexMCP Server")


@mcp.tool()
def get_pokemon(name_or_dex: str) -> PokemonSummary:
    return _get_pokemon(name_or_dex)


@mcp.tool()
def get_moves(name_or_dex: str, game: str) -> list[Move]:
    return _get_moves(name_or_dex, game)


@mcp.tool()
def get_sprites(name_or_dex: str, side: str = "front", variant: str = "default") -> SpriteURL:
    return _get_sprites(name_or_dex, side=side, variant=variant)


@mcp.tool()
def get_descriptions(name_or_dex: str, language: str = "en") -> dict[str, str]:
    return _get_descriptions(name_or_dex, language=language)


@mcp.tool()
def analyze_type_coverage(names_or_dexes: list[str]) -> TypeCoverageReport:
    return _analyze_type_coverage(names_or_dexes)


@mcp.tool()
def explore_abilities(name_or_dex: str) -> AbilityExplorerResult:
    return _explore_abilities(name_or_dex)


@mcp.tool()
def plan_evolutions(name_or_dex: str) -> EvolutionReport:
    return _plan_evolutions(name_or_dex)


@mcp.tool()
def find_encounters(name_or_dex: str) -> EncounterReport:
    return _find_encounters(name_or_dex)


@mcp.tool()
def get_breeding_info(name_or_dex: str, game: str | None = None) -> BreedingInfo:
    return _get_breeding_info(name_or_dex, game=game)


@mcp.tool()
def suggest_moveset(
    name_or_dex: str,
    game: str,
    limit: int = 4,
    include_tm: bool = False,
) -> MovesetRecommendation:
    return _suggest_moveset(name_or_dex, game=game, limit=limit, include_tm=include_tm)
