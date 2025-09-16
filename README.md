<p align='center'>
    <img src='https://raw.githubusercontent.com/RajeevAtla/dexMCP/main/logo.png'/>
</p>

# DexMCP

DexMCP is a Model Context Protocol (MCP) server that wraps the community-maintained
[pypokedex](https://pypi.org/project/pypokedex/) client for the
[PokéAPI](https://pokeapi.co/) into a collection of structured tools.
It lets MCP-compatible applications fetch Pokédex data – from base stats to move
lists and sprite URLs – without writing any custom API plumbing.

## Key capabilities

- 🔎 Look up any Pokémon by name or national Pokédex number and receive a
  structured summary including metric height/weight conversions and base stats.
- 🪪 Fetch localized Pokédex flavor text to provide in-universe descriptions.
- 🎮 Enumerate the exact moves a Pokémon can learn in a specific game
  (e.g., `scarlet-violet`, `sword-shield`, or `omega-ruby-alpha-sapphire`).
- 🖼️ Retrieve direct sprite URLs for front/back, shiny, and gendered variants to
  drive UI previews or shareable cards.
- ⚙️ Built with `FastMCP`, so it drops straight into any MCP client that speaks
  stdio (Claude Desktop, Cursor, VSCode MCP extensions, custom bots, etc.).

## Available tools

| Tool | Description | Required arguments | Optional arguments | Returns |
| --- | --- | --- | --- | --- |
| `get_pokemon` | Core Pokédex summary including stats, types, height/weight, and base experience. | `name_or_dex` – Pokémon name (case-insensitive) or dex number. | – | [`PokemonSummary`](dexmcp/dexmcp_server.py) model with nested base stats. |
| `get_moves` | List the moves a Pokémon can learn in a specific PokéAPI game entry. | `name_or_dex`, `game`. | – | List of [`Move`](dexmcp/dexmcp_server.py) records (move name, learn method, optional level). |
| `get_sprites` | Produce a direct URL to a sprite image. | `name_or_dex`. | `side` (`front`/`back`), `variant` (`default`, `shiny`, `female`, `female_shiny`). | [`SpriteURL`](dexmcp/dexmcp_server.py) record containing the resolved URL. |
| `get_descriptions` | Retrieve flavor-text entries keyed by game version. | `name_or_dex`. | `language` (default `en`). | Dict of version identifier → description string. |

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

The server speaks the Model Context Protocol over stdio. Configure your MCP
client to launch the command above and it will automatically discover the four
tools listed earlier.

### Example: ask an agent for stats and moves

The repository includes `dspy_client.py`, a minimal DSPy ReAct agent that connects
to the server and chooses the right tools to satisfy a natural-language request.
Activate your virtual environment and run:

```bash
python dspy_client.py
```

You should see the agent summarize the retrieved stats and move list for the
prompt defined at the bottom of the script. Edit the prompt or wire it into your
own DSPy workflows to integrate DexMCP into larger automations.

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
