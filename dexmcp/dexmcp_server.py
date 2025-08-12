from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
import pypokedex

# ---------- Pydantic schemas (structured tool output) ----------

class BaseStats(BaseModel):
    hp: int
    attack: int
    defense: int
    sp_atk: int
    sp_def: int
    speed: int

class PokemonSummary(BaseModel):
    dex: int = Field(description="National Pokédex number")
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

# ---------- Server ----------

mcp = FastMCP("DexMCP Server")

def _lookup(name_or_dex: str):
    """Internal helper to fetch a pypokedex.Pokemon by name (case-insensitive) or dex number."""
    try:
        if name_or_dex.isdigit():
            return pypokedex.get(dex=int(name_or_dex))
        return pypokedex.get(name=name_or_dex.lower())
    except Exception as e:
        # Let the client see a clean error string
        raise ValueError(f"Could not find Pokémon '{name_or_dex}': {e}") from e

@mcp.tool()
def get_pokemon(name_or_dex: str) -> PokemonSummary:
    """
    Look up a Pokémon by name (e.g., 'garchomp') or dex number (e.g., '445').
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
    List the moves a Pokémon can learn in a specific PokeAPI game identifier (e.g., 'scarlet-violet', 'sword-shield').
    """
    pk = _lookup(name_or_dex)
    moves_for_game = pk.moves.get(game, [])
    return [Move(name=m.name, learn_method=m.learn_method, level=m.level) for m in moves_for_game]

@mcp.tool()
def get_sprites(name_or_dex: str, side: str = "front", variant: str = "default") -> SpriteURL:
    """
    Return a direct URL to a sprite. side: 'front' or 'back'.
    variant: typically one of 'default', 'shiny', 'female', 'female_shiny'.
    (Availability varies by Pokémon.)
    """
    if side not in {"front", "back"}:
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
    return pk.get_descriptions(language=language)

if __name__ == "__main__":
    mcp.run()
