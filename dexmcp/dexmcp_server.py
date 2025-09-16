from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# requests is used for direct PokeAPI lookups that supplement the pypokedex client.

import pypokedex

# FastMCP tool definitions that surface Pokedex data for agentic clients.
# Each decorated function becomes a structured tool discoverable by MCP hosts.

# ---------- Pydantic schemas (structured tool output) ----------


class BaseStats(BaseModel):
    hp: int
    attack: int
    defense: int
    sp_atk: int
    sp_def: int
    speed: int


class PokemonSummary(BaseModel):
    dex: int = Field(description="National Pokedex number")
    name: str
    types: List[str]
    height_dm: int = Field(description="Height in decimeters (as provided by API)")
    height_m: float = Field(description="Height in meters (derived)")
    weight_hg: int = Field(description="Weight in hectograms (as provided by API)")
    weight_kg: float = Field(description="Weight in kilograms (derived)")
    base_experience: int
    base_stats: BaseStats


class Move(BaseModel):
    name: str
    learn_method: str
    level: Optional[int] = None


class SpriteURL(BaseModel):
    url: Optional[str] = Field(
        description="Direct URL to a sprite image (may be None if unavailable)"
    )
    side: str = Field(description="front or back")
    variant: str = Field(
        description="one of: default, shiny, female, female_shiny (depends on availability)"
    )


class TypeMatchupSummary(BaseModel):
    attack_type: str
    weak: int = Field(description="Team members that take >1x damage from this type")
    resistant: int = Field(description="Team members that take <1x damage")
    immune: int = Field(description="Team members that take 0 damage")
    neutral: int = Field(description="Team members that take exactly 1x damage")


class TypeCoverageReport(BaseModel):
    team: List[str]
    matchup_summary: List[TypeMatchupSummary]
    notable_weaknesses: List[str] = Field(
        description="Attack types that threaten at least half the roster"
    )
    notable_resistances: List[str] = Field(
        description="Attack types largely covered by the roster"
    )


class AbilityDetail(BaseModel):
    name: str
    is_hidden: bool
    short_effect: Optional[str]
    effect: Optional[str]


class AbilityExplorerResult(BaseModel):
    pokemon: str
    abilities: List[AbilityDetail]


class EvolutionStep(BaseModel):
    from_species: str
    to_species: str
    trigger: Optional[str]
    minimum_level: Optional[int]
    item: Optional[str]
    conditions: Dict[str, Optional[str]] = Field(default_factory=dict)


class EvolutionPath(BaseModel):
    steps: List[EvolutionStep]


class EvolutionReport(BaseModel):
    pokemon: str
    paths: List[EvolutionPath]


class EncounterDetail(BaseModel):
    method: str
    min_level: int
    max_level: int
    chance: int
    condition_values: List[str]


class EncounterVersion(BaseModel):
    version: str
    max_chance: int
    details: List[EncounterDetail]


class EncounterLocation(BaseModel):
    location_area: str
    versions: List[EncounterVersion]


class EncounterReport(BaseModel):
    pokemon: str
    locations: List[EncounterLocation]


class GenderRatio(BaseModel):
    female_percent: float
    male_percent: float


class BreedingInfo(BaseModel):
    pokemon: str
    egg_groups: List[str]
    gender: GenderRatio
    hatch_steps: Optional[int]
    egg_moves: List[str]


class MoveRecommendation(BaseModel):
    name: str
    move_type: Optional[str]
    power: Optional[int]
    accuracy: Optional[int]
    damage_class: Optional[str]
    learn_method: str
    level: Optional[int]
    stab: bool
    score: float
    short_effect: Optional[str]
    effect: Optional[str]


class MovesetRecommendation(BaseModel):
    pokemon: str
    game: str
    recommendations: List[MoveRecommendation]


# ---------- Constants ----------

IGNORED_TYPES = {"unknown", "shadow"}

# ---------- Server ----------

mcp = FastMCP("DexMCP Server")


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
    except Exception as e:
        # Let the client see a clean error string
        raise ValueError(f"Could not find Pokemon '{name_or_dex}': {e}") from e


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


def _calc_multiplier(attack_type: str, defend_types: Sequence[str]) -> float:
    """Return how much damage an attack type deals to the provided defensive typing."""
    try:
        relations = _get_type_relations(attack_type)
    except ValueError:
        return 1.0

    multiplier = 1.0
    for defend_type in defend_types:
        if defend_type in relations.get("no_damage_to", []):
            return 0.0
        if defend_type in relations.get("double_damage_to", []):
            multiplier *= 2.0
        elif defend_type in relations.get("half_damage_to", []):
            multiplier *= 0.5
    return multiplier


@lru_cache(maxsize=64)
def _get_move_data(move_name: str) -> Dict:
    return _fetch_json(
        f"https://pokeapi.co/api/v2/move/{move_name.lower()}",
        context=f"move data for {move_name}",
    )


def _extract_short_effect(entries: List[Dict]) -> Optional[str]:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("short_effect")
    return None


def _extract_effect(entries: List[Dict]) -> Optional[str]:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get("effect")
    return None


@mcp.tool()
def get_pokemon(name_or_dex: str) -> PokemonSummary:
    """
    Look up a Pokemon by name (e.g., 'garchomp') or dex number (e.g., '445').
    Returns core stats, types, height/weight (with metric conversions), and base experience.
    """
    pk = _lookup(name_or_dex)

    # pk.base_stats is a namedtuple; convert to our model
    stats = BaseStats(
        hp=pk.base_stats.hp,
        attack=pk.base_stats.attack,
        defense=pk.base_stats.defense,
        sp_atk=pk.base_stats.sp_atk,
        sp_def=pk.base_stats.sp_def,
        speed=pk.base_stats.speed,
    )

    # Height and weight keep both raw and derived units so clients can choose the display they prefer.
    return PokemonSummary(
        dex=pk.dex,
        name=pk.name,
        types=list(pk.types),
        height_dm=pk.height,          # decimeters per pypokedex/PokeAPI
        height_m=pk.height / 10.0,    # convert dm -> m
        weight_hg=pk.weight,          # hectograms per pypokedex/PokeAPI
        weight_kg=pk.weight / 10.0,   # convert hg -> kg
        base_experience=pk.base_experience,
        base_stats=stats,
    )


@mcp.tool()
def get_moves(name_or_dex: str, game: str) -> List[Move]:
    """
    List the moves a Pokemon can learn in a specific PokeAPI game identifier (e.g., 'scarlet-violet', 'sword-shield').
    """
    pk = _lookup(name_or_dex)
    # pypokedex exposes move data keyed by game identifier (e.g., 'scarlet-violet'). Missing keys return [].
    moves_for_game = pk.moves.get(game, [])
    return [Move(name=m.name, learn_method=m.learn_method, level=m.level) for m in moves_for_game]


@mcp.tool()
def get_sprites(name_or_dex: str, side: str = "front", variant: str = "default") -> SpriteURL:
    """
    Return a direct URL to a sprite. side: 'front' or 'back'.
    variant: typically one of 'default', 'shiny', 'female', 'female_shiny'.
    (Availability varies by Pokemon.)
    """
    if side not in {"front", "back"}:
        # Validate inputs early so downstream tooling gets actionable errors.
        raise ValueError("side must be 'front' or 'back'")
    pk = _lookup(name_or_dex)

    # pk.sprites.{front,back} are dicts with keys like 'default','shiny','female','female_shiny'
    sprite_dict: Dict[str, Optional[str]] = getattr(pk.sprites, side)
    url = sprite_dict.get(variant)
    return SpriteURL(url=url, side=side, variant=variant)


@mcp.tool()
def get_descriptions(name_or_dex: str, language: str = "en") -> Dict[str, str]:
    """
    Return flavor-text descriptions (version -> text) in the requested language.
    """
    pk = _lookup(name_or_dex)
    # Flavor text comes from multiple game entries; keep the raw mapping so clients can pick the ones they need.
    return pk.get_descriptions(language=language)


@mcp.tool()
def analyze_type_coverage(names_or_dexes: List[str]) -> TypeCoverageReport:
    """Summarize defensive coverage for a roster of Pokemon."""
    # Helps team builders quickly spot shared weaknesses before heading into a battle.
    if not names_or_dexes:
        raise ValueError("names_or_dexes must contain at least one Pokemon")

    team_pokemon = [_lookup(identifier) for identifier in names_or_dexes]
    matchup_rows: List[TypeMatchupSummary] = []

    for attack_type in _list_all_types():
        weak = resistant = immune = neutral = 0
        for pk in team_pokemon:
            multiplier = _calc_multiplier(attack_type, pk.types)
            if multiplier == 0:
                immune += 1
            elif multiplier > 1:
                weak += 1
            elif multiplier < 1:
                resistant += 1
            else:
                neutral += 1
        matchup_rows.append(
            TypeMatchupSummary(
                attack_type=attack_type,
                weak=weak,
                resistant=resistant,
                immune=immune,
                neutral=neutral,
            )
        )

    roster_size = len(team_pokemon)
    notable_weak = [
        row.attack_type
        for row in matchup_rows
        if row.weak >= max(1, (roster_size + 1) // 2)
    ]
    notable_resist = [
        row.attack_type
        for row in matchup_rows
        if row.resistant + row.immune == roster_size
    ]
    return TypeCoverageReport(
        team=[pk.name for pk in team_pokemon],
        matchup_summary=matchup_rows,
        notable_weaknesses=notable_weak,
        notable_resistances=notable_resist,
    )


@mcp.tool()
def explore_abilities(name_or_dex: str) -> AbilityExplorerResult:
    # Fetch each ability's effect text directly from PokeAPI so clients do not need a second integration.
    """Return detailed ability information with effect text pulled from PokeAPI."""
    pk = _lookup(name_or_dex)
    abilities: List[AbilityDetail] = []
    for ability in pk.abilities:
        data = _fetch_json(
            f"https://pokeapi.co/api/v2/ability/{ability.name}",
            context=f"ability data for {ability.name}",
        )
        effect_entries = data.get("effect_entries", [])
        abilities.append(
            AbilityDetail(
                name=ability.name,
                is_hidden=ability.is_hidden,
                short_effect=_extract_short_effect(effect_entries),
                effect=_extract_effect(effect_entries),
            )
        )
    return AbilityExplorerResult(pokemon=pk.name, abilities=abilities)


def _expand_chain(
    node: Dict,
    current_path: List[EvolutionStep],
    all_paths: List[EvolutionPath],
) -> None:
    # Depth-first traversal that collects every evolution path through the chain graph.
    species_name = node["species"]["name"]
    evolves_to = node.get("evolves_to", [])
    if not evolves_to:
        all_paths.append(EvolutionPath(steps=current_path.copy()))
        return

    for child in evolves_to:
        evolution_details = child.get("evolution_details") or [{}]
        for detail in evolution_details:
            conditions: Dict[str, Optional[str]] = {}
            for key, value in detail.items():
                if key in {"trigger", "min_level", "item"}:
                    continue
                if key == "time_of_day" and value:
                    conditions[key] = value
                elif isinstance(value, dict):
                    conditions[key] = value.get("name")
                elif value not in (None, False):
                    conditions[key] = str(value)
            step = EvolutionStep(
                from_species=species_name,
                to_species=child["species"]["name"],
                trigger=(detail.get("trigger") or {}).get("name"),
                minimum_level=detail.get("min_level"),
                item=(detail.get("item") or {}).get("name"),
                conditions=conditions,
            )
            current_path.append(step)
            _expand_chain(child, current_path, all_paths)
            current_path.pop()


@mcp.tool()
def plan_evolutions(name_or_dex: str) -> EvolutionReport:
    """Enumerate evolution paths for the given Pokemon."""
    pk = _lookup(name_or_dex)
    species_data = _fetch_json(
        f"https://pokeapi.co/api/v2/pokemon-species/{pk.dex}",
        context=f"species data for {pk.name}",
    )
    chain_url = species_data.get("evolution_chain", {}).get("url")
    if not chain_url:
        return EvolutionReport(pokemon=pk.name, paths=[])

    chain_data = _fetch_json(chain_url, context="evolution chain")
    all_paths: List[EvolutionPath] = []
    _expand_chain(chain_data["chain"], [], all_paths)

    relevant_paths = [
        path
        for path in all_paths
        if any(step.from_species == pk.name or step.to_species == pk.name for step in path.steps)
    ]
    if not relevant_paths:
        relevant_paths = all_paths

    return EvolutionReport(pokemon=pk.name, paths=relevant_paths)


@mcp.tool()
def find_encounters(name_or_dex: str) -> EncounterReport:
    """Retrieve wild encounter locations from PokeAPI."""
    # Useful for players planning hunts or resource runs in a specific game version.
    pk = _lookup(name_or_dex)
    data = _fetch_json(
        f"https://pokeapi.co/api/v2/pokemon/{pk.dex}/encounters",
        context=f"encounter data for {pk.name}",
    )
    locations: List[EncounterLocation] = []
    for entry in data:
        location_area = entry.get("location_area", {}).get("name")
        versions: List[EncounterVersion] = []
        for version_detail in entry.get("version_details", []):
            version_name = version_detail.get("version", {}).get("name")
            max_chance = version_detail.get("max_chance", 0)
            details: List[EncounterDetail] = []
            for detail in version_detail.get("encounter_details", []):
                details.append(
                    EncounterDetail(
                        method=(detail.get("method") or {}).get("name", "unknown"),
                        min_level=detail.get("min_level", 0),
                        max_level=detail.get("max_level", 0),
                        chance=detail.get("chance", 0),
                        condition_values=[
                            value.get("name")
                            for value in detail.get("condition_values", [])
                            if value
                        ],
                    )
                )
            versions.append(
                EncounterVersion(
                    version=version_name,
                    max_chance=max_chance,
                    details=details,
                )
            )
        locations.append(
            EncounterLocation(
                location_area=location_area,
                versions=versions,
            )
        )
    return EncounterReport(pokemon=pk.name, locations=locations)


def _gender_from_rate(gender_rate: int) -> GenderRatio:
    if gender_rate == -1:
        return GenderRatio(female_percent=0.0, male_percent=0.0)
    female = (gender_rate / 8.0) * 100.0
    male = 100.0 - female
    return GenderRatio(female_percent=round(female, 2), male_percent=round(male, 2))


@mcp.tool()
def get_breeding_info(name_or_dex: str, game: Optional[str] = None) -> BreedingInfo:
    """Summarize egg groups, hatch steps, gender ratio, and egg moves."""
    # Combines species metadata with move learnsets so breeders see everything in one response.
    pk = _lookup(name_or_dex)
    species_data = _fetch_json(
        f"https://pokeapi.co/api/v2/pokemon-species/{pk.dex}",
        context=f"species data for {pk.name}",
    )
    egg_groups = [group["name"] for group in species_data.get("egg_groups", [])]
    hatch_counter = species_data.get("hatch_counter")
    hatch_steps = (hatch_counter + 1) * 255 if hatch_counter is not None else None
    gender = _gender_from_rate(species_data.get("gender_rate", -1))

    egg_moves: List[str] = []
    if game:
        moves = pk.moves.get(game, [])
        egg_moves = sorted({move.name for move in moves if move.learn_method == "egg"})
    else:
        for moves in pk.moves.values():
            for move in moves:
                if move.learn_method == "egg":
                    egg_moves.append(move.name)
        egg_moves = sorted(set(egg_moves))

    return BreedingInfo(
        pokemon=pk.name,
        egg_groups=egg_groups,
        gender=gender,
        hatch_steps=hatch_steps,
        egg_moves=egg_moves,
    )


@mcp.tool()
# Lightweight heuristic that ranks damaging moves by power, accuracy, STAB, and stat alignment.
def suggest_moveset(
    name_or_dex: str,
    game: str,
    limit: int = 4,
    include_tm: bool = False,
) -> MovesetRecommendation:
    """Recommend high-impact moves for a Pokemon in a given game using simple heuristics."""
    pk = _lookup(name_or_dex)
    moves = pk.moves.get(game)
    if moves is None:
        raise ValueError(f"No move data for game '{game}'")

    preferred_class = "physical" if pk.base_stats.attack >= pk.base_stats.sp_atk else "special"
    candidates: List[MoveRecommendation] = []
    for move in moves:
        if move.learn_method == "egg":
            continue  # egg moves are covered by the breeding helper
        if not include_tm and move.learn_method not in {"level-up", "tutor"}:
            continue
        try:
            move_data = _get_move_data(move.name)
        except ValueError:
            continue

        damage_class = (move_data.get("damage_class") or {}).get("name")
        if damage_class not in {"physical", "special"}:
            continue

        power = move_data.get("power")
        accuracy = move_data.get("accuracy")
        move_type = (move_data.get("type") or {}).get("name")
        stab = move_type in pk.types if move_type else False
        accuracy_factor = (accuracy / 100.0) if accuracy else 0.85
        power_factor = power or 0
        class_factor = 1.1 if damage_class == preferred_class else 0.9
        stab_factor = 1.3 if stab else 1.0
        score = power_factor * accuracy_factor * class_factor * stab_factor
        effect_entries = move_data.get("effect_entries", [])
        recommendation = MoveRecommendation(
            name=move.name,
            move_type=move_type,
            power=power,
            accuracy=accuracy,
            damage_class=damage_class,
            learn_method=move.learn_method,
            level=move.level,
            stab=stab,
            score=round(score, 2),
            short_effect=_extract_short_effect(effect_entries),
            effect=_extract_effect(effect_entries),
        )
        candidates.append(recommendation)

    candidates.sort(key=lambda rec: rec.score, reverse=True)
    return MovesetRecommendation(
        pokemon=pk.name,
        game=game,
        recommendations=candidates[:limit],
    )


if __name__ == "__main__":
    mcp.run()
