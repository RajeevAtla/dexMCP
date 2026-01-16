from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
