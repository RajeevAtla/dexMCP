"""Pydantic models for DexMCP tool inputs and outputs."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# --- Core Pokemon summary models ---


class BaseStats(BaseModel):
    """Base stat block for a Pokemon."""

    hp: int
    attack: int
    defense: int
    sp_atk: int
    sp_def: int
    speed: int


class PokemonSummary(BaseModel):
    """High-level Pokemon summary used by tool responses."""

    dex: int = Field(description="National Pokedex number")
    name: str
    types: List[str]
    # Keep both raw and derived units so clients can pick a display.
    height_dm: int = Field(description="Height in decimeters (as provided by API)")
    height_m: float = Field(description="Height in meters (derived)")
    weight_hg: int = Field(description="Weight in hectograms (as provided by API)")
    weight_kg: float = Field(description="Weight in kilograms (derived)")
    base_experience: int
    base_stats: BaseStats


# --- Move + sprite outputs ---


class Move(BaseModel):
    """Move learnset entry for a Pokemon."""

    name: str
    learn_method: str
    level: Optional[int] = None


class SpriteURL(BaseModel):
    """Sprite URL metadata for a Pokemon."""

    url: Optional[str] = Field(
        description="Direct URL to a sprite image (may be None if unavailable)"
    )
    side: str = Field(description="front or back")
    variant: str = Field(
        description="one of: default, shiny, female, female_shiny (depends on availability)"
    )


# --- Coverage analysis outputs ---


class TypeMatchupSummary(BaseModel):
    """Defensive matchup counts for a single attacking type."""

    attack_type: str
    weak: int = Field(description="Team members that take >1x damage from this type")
    resistant: int = Field(description="Team members that take <1x damage")
    immune: int = Field(description="Team members that take 0 damage")
    neutral: int = Field(description="Team members that take exactly 1x damage")


class TypeCoverageReport(BaseModel):
    """Summary of defensive coverage for a roster."""

    team: List[str]
    matchup_summary: List[TypeMatchupSummary]
    notable_weaknesses: List[str] = Field(
        description="Attack types that threaten at least half the roster"
    )
    notable_resistances: List[str] = Field(
        description="Attack types largely covered by the roster"
    )


# --- Ability outputs ---


class AbilityDetail(BaseModel):
    """Detailed ability info with effect text."""

    name: str
    is_hidden: bool
    short_effect: Optional[str]
    effect: Optional[str]


class AbilityExplorerResult(BaseModel):
    """Ability listing for a Pokemon."""

    pokemon: str
    abilities: List[AbilityDetail]


# --- Evolution outputs ---


class EvolutionStep(BaseModel):
    """Single evolution transition with trigger metadata."""

    from_species: str
    to_species: str
    trigger: Optional[str]
    minimum_level: Optional[int]
    item: Optional[str]
    conditions: Dict[str, Optional[str]] = Field(default_factory=dict)


class EvolutionPath(BaseModel):
    """Ordered evolution steps forming one path in the chain."""

    steps: List[EvolutionStep]


class EvolutionReport(BaseModel):
    """Collection of evolution paths for a Pokemon."""

    pokemon: str
    paths: List[EvolutionPath]


# --- Encounter outputs ---


class EncounterDetail(BaseModel):
    """Encounter method details for a specific version entry."""

    method: str
    min_level: int
    max_level: int
    chance: int
    condition_values: List[str]


class EncounterVersion(BaseModel):
    """Encounter details for a single game version."""

    version: str
    max_chance: int
    details: List[EncounterDetail]


class EncounterLocation(BaseModel):
    """Encounter information for a specific location area."""

    location_area: str
    versions: List[EncounterVersion]


class EncounterReport(BaseModel):
    """Encounter locations grouped by area and version."""

    pokemon: str
    locations: List[EncounterLocation]


# --- Breeding outputs ---


class GenderRatio(BaseModel):
    """Gender ratio percentages for a Pokemon."""

    female_percent: float
    male_percent: float


class BreedingInfo(BaseModel):
    """Breeding metadata including egg groups and egg moves."""

    pokemon: str
    egg_groups: List[str]
    gender: GenderRatio
    hatch_steps: Optional[int]
    egg_moves: List[str]


# --- Moveset recommendation outputs ---


class MoveRecommendation(BaseModel):
    """Move recommendation metadata and scoring."""

    name: str
    move_type: Optional[str]
    power: Optional[int]
    accuracy: Optional[int]
    damage_class: Optional[str]
    learn_method: str
    level: Optional[int]
    stab: bool
    # Score is a heuristic, not a competitive tiering metric.
    score: float
    short_effect: Optional[str]
    effect: Optional[str]


class MovesetRecommendation(BaseModel):
    """Ranked moveset recommendations for a Pokemon."""

    pokemon: str
    game: str
    recommendations: List[MoveRecommendation]
