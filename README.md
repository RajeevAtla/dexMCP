# Title

<p align='center'>
    <img src='https://raw.githubusercontent.com/RajeevAtla/dexMCP/main/logo.png'/>
</P>

## DexMCP

DexMCP is a Model Context Protocol (MCP) server that wraps the community
maintained [pypokedex](https://pypi.org/project/pypokedex/) client for the
[PokeAPI](https://pokeapi.co/). It exposes curated tools so MCP compatible
applications can fetch Pokedex data without custom API plumbing.

## Key capabilities

- Query any Pokemon by name or national number and receive metric aware base
  stats.
- Pull localized flavor text so agents can present in universe descriptions for
  each game version.
- Inspect move learnsets for a chosen game so automation chains pick the right
  actions.
- Map evolution chains, encounter locations, and breeding requirements without
  bespoke glue code.
- Run roster analysis with coverage reports and simple moveset tips for
  battle planning.

## Available tools

- `get_pokemon`
  - Required: `name_or_dex`
  - Optional: none
  - Returns: `PokemonSummary` with stats, types, height, weight, and base
    experience.
- `get_moves`
  - Required: `name_or_dex`, `game`
  - Optional: none
  - Returns: list of `Move` entries with learn method and optional level.
- `get_sprites`
  - Required: `name_or_dex`
  - Optional: `side` (`front` or `back`), `variant` (`default`, `shiny`,
    `female`, `female_shiny`)
  - Returns: `SpriteURL` containing the resolved image link.
- `get_descriptions`
  - Required: `name_or_dex`
  - Optional: `language` (defaults to `en`)
  - Returns: mapping of game version to flavor text strings.
- `analyze_type_coverage`
  - Required: `names_or_dexes` list
  - Optional: none
  - Returns: `TypeCoverageReport` summarizing defensive matchups.
- `explore_abilities`
  - Required: `name_or_dex`
  - Optional: none
  - Returns: `AbilityExplorerResult` with effect text and hidden ability flag.
- `plan_evolutions`
  - Required: `name_or_dex`
  - Optional: none
  - Returns: `EvolutionReport` that enumerates triggers and branching paths.
- `find_encounters`
  - Required: `name_or_dex`
  - Optional: none
  - Returns: `EncounterReport` grouped by location and game version.
- `get_breeding_info`
  - Required: `name_or_dex`
  - Optional: `game` to scope egg moves
  - Returns: `BreedingInfo` with egg groups, hatch steps, gender split, and
    egg moves.
- `suggest_moveset`
  - Required: `name_or_dex`, `game`
  - Optional: `limit` (default 4), `include_tm` (default `false`)
  - Returns: `MovesetRecommendation` ordered by heuristic score.

## Getting started

### Prerequisites

- Python 3.10 or newer.
- An MCP aware client (or the Python `mcp` package) that can launch stdio
  servers.
- Internet access so `pypokedex` can query PokeAPI the first time a Pokemon is

  requested.

### Clone and install dependencies

```bash
git clone https://github.com/RajeevAtla/dexMCP.git
cd dexMCP
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install "mcp[cli]" pypokedex dspy-ai
```

The runtime requirements are `mcp` (for `FastMCP`), `pypokedex`, and the
transitive `pydantic` dependency. Installing `dspy-ai` is optional but useful
for trying the example agent below.

### Run the MCP server

```bash
python dexmcp/dexmcp_server.py
```

The server speaks MCP over stdio. Configure an MCP client to launch the command
above and it will auto discover the tools listed earlier.

### Example: run the DSPy demo agent

The repository ships `dspy_client.py`, a minimal DSPy client that connects to
this server and calls the appropriate tools to satisfy natural language
requests. Activate your virtual environment and run the curated demo suite:

```bash
python dspy_client.py --demo
```

The agent chains several tools to:

- Retrieve Garchomp stats and ORAS level up moves.
- Audit defensive coverage for Pikachu, Garchomp, and Gyarados.
- Surface Gengar abilities and Eevee evolution branches.
- List Dratini encounter methods in FireRed and LeafGreen.
- Summarize Sylveon breeding info and egg moves in Sword and Shield.

- Recommend a Greninja moveset for Sun and Moon.

Provide your own prompt with:

```bash
python dspy_client.py \
  "Compare Charizard and Tyranitar defensive coverage in scarlet-violet."
```

Add `--demo` alongside the prompt to run the canned sequence afterward.

### Example: run the LangChain demo agent

If you prefer LangChain, install the optional packages:

```bash
pip install langchain langchain-openai
```

Ensure `OPENAI_API_KEY` (or another provider key supported by your LangChain
LLM) is present in the environment. Then launch the demo:

```bash
python langchain_client.py --demo
```

The LangChain agent mirrors the DSPy scenarios, exercising the coverage,
ability, evolution, encounter, breeding, and moveset tools.

Supply a custom prompt with:

```bash
python langchain_client.py \
  "Plan a battle ready moveset for gardevoir in scarlet-violet."
```

Use `--demo` with a prompt to run it first before the guided walkthrough.

## Project structure

```text
.
|-- dexmcp/
|   `-- dexmcp_server.py   # FastMCP server that exposes the tool set
|-- dspy_client.py         # DSPy demo agent that consumes the server
|-- langchain_client.py    # LangChain demo agent for the same tools
|-- logo.png               # Branding used in the README banner
|-- LICENSE.md             # MIT License
|-- README.md
```

## Data source and caching

`pypokedex` wraps PokeAPI and caches responses on disk under the user cache
folder. The first lookup for a Pokemon may take a second while data is fetched;
subsequent calls are served from the local cache.

## License

DexMCP is distributed under the MIT License. See [LICENSE.md](LICENSE.md) for
full terms.
