"""Evolution chain traversal helpers."""

from __future__ import annotations

from typing import Dict, List, Optional

from . import api
from .models import EvolutionPath, EvolutionReport, EvolutionStep


def _expand_chain(
    node: Dict,
    current_path: List[EvolutionStep],
    all_paths: List[EvolutionPath],
) -> None:
    """Traverse evolution chain nodes and collect full paths.

    Args:
        node: Current chain node from the PokeAPI evolution tree.
        current_path: Accumulated steps for the current path.
        all_paths: Collector for all discovered evolution paths.
    """
    # Depth-first traversal that collects every evolution path through the chain graph.
    # Each node includes the species name and its possible next evolutions.
    species_name = node["species"]["name"]
    evolves_to = node.get("evolves_to", [])
    if not evolves_to:
        # Leaf node: record the accumulated path.
        all_paths.append(EvolutionPath(steps=current_path.copy()))
        return

    for child in evolves_to:
        # Some nodes can have multiple evolution conditions; iterate each detail.
        evolution_details = child.get("evolution_details") or [{}]
        for detail in evolution_details:
            # Collect extra conditions to keep the output expressive.
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
            # Build a step from the current species to the child species.
            step = EvolutionStep(
                from_species=species_name,
                to_species=child["species"]["name"],
                trigger=(detail.get("trigger") or {}).get("name"),
                minimum_level=detail.get("min_level"),
                item=(detail.get("item") or {}).get("name"),
                conditions=conditions,
            )
            # Recurse deeper with the new step appended.
            current_path.append(step)
            _expand_chain(child, current_path, all_paths)
            current_path.pop()


def plan_evolutions(name_or_dex: str) -> EvolutionReport:
    """Enumerate evolution paths for the given Pokemon.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Evolution paths with trigger and condition metadata.
    """
    # Resolve the Pokemon and then fetch its species data (for the evolution chain URL).
    pk = api._lookup(name_or_dex)
    species_data = api._fetch_json(
        f"https://pokeapi.co/api/v2/pokemon-species/{pk.dex}",
        context=f"species data for {pk.name}",
    )
    chain_url = species_data.get("evolution_chain", {}).get("url")
    if not chain_url:
        # Some species legitimately lack an evolution chain.
        return EvolutionReport(pokemon=pk.name, paths=[])

    # Load the chain once and walk the tree to expand all paths.
    chain_data = api._fetch_json(chain_url, context="evolution chain")
    all_paths: List[EvolutionPath] = []
    _expand_chain(chain_data["chain"], [], all_paths)

    # Prefer paths that explicitly include the requested Pokemon.
    relevant_paths = [
        path
        for path in all_paths
        if any(step.from_species == pk.name or step.to_species == pk.name for step in path.steps)
    ]
    if not relevant_paths:
        # Fallback: return full chain if the Pokemon isn't found in the path list.
        relevant_paths = all_paths

    return EvolutionReport(pokemon=pk.name, paths=relevant_paths)
