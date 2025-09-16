<p align='center'>
    <img src='https://raw.githubusercontent.com/RajeevAtla/dexMCP/main/logo.png'/>
</p>

# DexMCP

DexMCP is a Model Context Protocol (MCP) server that wraps the community-maintained
[pypokedex](https://pypi.org/project/pypokedex/) client for the
[PokéAPI](https://pokeapi.co/) into a collection of structured tools.
It lets MCP-compatible applications fetch Pokédex data - from base stats to move
lists and sprite URLs – without writing any custom API plumbing.

## Key capabilities

- Query any Pokemon by name or national Pokedex number and receive a structured summary with metric conversions and base stats.
- Pull localized Pokedex flavor text to deliver in-universe descriptions in the language your UX needs.
- Inspect full move learnsets for a chosen game so agents can chain the right tooling steps automatically.
- Map evolution chains, encounter locations, and breeding requirements without writing custom glue code.
- Run roster analysis with type coverage reports and heuristic moveset suggestions for battle preparation.

## Available tools

| Tool | Description | Required arguments | Optional arguments | Returns |
| --- | --- | --- | --- | --- |
| `get_pokemon` | Core Pokedex summary including stats, types, height/weight, and base experience. | `name_or_dex` | N/A | [`PokemonSummary`](dexmcp/dexmcp_server.py) model with nested base stats. |
| `get_moves` | List the moves a Pokemon can learn in a specific PokeAPI game entry. | `name_or_dex`, `game` | N/A | List of [`Move`](dexmcp/dexmcp_server.py) records (move name, learn method, optional level). |
| `get_sprites` | Produce a direct URL to a sprite image. | `name_or_dex` | `side` (`front`/`back`), `variant` (`default`, `shiny`, `female`, `female_shiny`) | [`SpriteURL`](dexmcp/dexmcp_server.py) record containing the resolved URL. |
| `get_descriptions` | Retrieve flavor-text entries keyed by game version. | `name_or_dex` | `language` (default `en`) | Dict of version identifier -> description string. |
| `analyze_type_coverage` | Summarize defensive coverage for a roster of Pokemon. | `names_or_dexes` (list) | N/A | [`TypeCoverageReport`](dexmcp/dexmcp_server.py) with matchup breakdowns. |
| `explore_abilities` | Fetch effect text and hidden-ability metadata. | `name_or_dex` | N/A | [`AbilityExplorerResult`](dexmcp/dexmcp_server.py) listing each ability. |
| `plan_evolutions` | Enumerate evolution steps, triggers, and branching paths. | `name_or_dex` | N/A | [`EvolutionReport`](dexmcp/dexmcp_server.py) containing relevant chains. |
| `find_encounters` | Surface wild encounter locations, methods, and levels. | `name_or_dex` | N/A | [`EncounterReport`](dexmcp/dexmcp_server.py) grouped by location and game version. |
| `get_breeding_info` | Summarize egg groups, hatch steps, gender split, and egg moves. | `name_or_dex` | `game` to scope egg moves | [`BreedingInfo`](dexmcp/dexmcp_server.py) record. |
| `suggest_moveset` | Recommend high-impact moves for a game using simple heuristics. | `name_or_dex`, `game` | `limit` (default 4), `include_tm` (default `false`) | [`MovesetRecommendation`](dexmcp/dexmcp_server.py) sorted by score. |


## Getting started

### Prerequisites

- Python 3.10 or newer.
- An MCP-aware client (or the Python `mcp` package) that can launch stdio servers.
- Internet access so `pypokedex` can query PokéAPI the first time a Pokémon is requested.

### Clone and install dependencies

```bash
git clone https://github.com/RajeevAtla/dexMCP.git
cd dexMCP
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install "mcp[cli]" pypokedex dspy-ai
```

The only runtime requirements for the server are `mcp` (for `FastMCP`), `pypokedex`,
and `pydantic` (installed transitively). Installing `dspy-ai` is optional but
useful if you want to run the example agent below.

### Run the MCP server

```bash
python dexmcp/dexmcp_server.py
```

The server speaks the Model Context Protocol over stdio. 
Configure your MCP client to launch the command above and it will automatically discover the tools listed earlier.

### Example: ask an agent for stats and moves

The repository includes `dspy_client.py`, 
a minimal DSPy client that connects
to the server and chooses the right tools to satisfy a natural-language request.
Activate your virtual environment and run:

```bash
python dspy_client.py
```

You should see the agent summarize the retrieved stats and move list for the prompt defined at the bottom of the script. 
Edit the prompt or wire it into your own DSPy workflows to integrate DexMCP into larger automations.

## Project structure

```
.
├── dexmcp/
│   └── dexmcp_server.py     # FastMCP server exposing Pokédex tooling
├── dspy_client.py           # Optional DSPy example agent that consumes the MCP server
├── logo.png                 # Branding used in the README banner
├── LICENSE.md               # MIT License
└── README.md
```

## Data source & caching

`pypokedex` wraps PokéAPI and caches responses on disk (typically under the
user's cache directory). The first lookup for a Pokémon may take a second or two
while data is fetched; subsequent calls are served from the local cache.

## License

DexMCP is distributed under the terms of the MIT License. See
[LICENSE.md](LICENSE.md) for details.
