# dexmcp_dspy_client.py
# A DSPy client that connects to the DexMCP (Pokédex) MCP server over stdio
# and uses **Gemini** as the model provider.
#
# Requirements:
#   pip install -U dspy-ai "mcp[cli]" pypokedex httpx
#   # for Gemini via DSPy
#   export GEMINI_API_KEY=...            # required
#
# Run:
#   python dexmcp_dspy_client.py --server ./pokedex_mcp_server.py \
#       --ask "Show Garchomp base stats and abilities, then list all level-up moves in ORAS."
#
# Notes:
# - The MCP server should be the one you implemented earlier (pokedex_mcp_server.py).
# - This client discovers MCP tools, converts them to DSPy tools, and lets a ReAct agent
#   choose and call them. All LLM responses must be grounded in tool outputs.

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Iterable, List

import dspy
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

# -----------------------------
# Gemini configuration (DSPy)
# -----------------------------

def configure_gemini_from_env() -> None:
    """Configure DSPy to use Google Gemini via the built-in provider string.

    Uses the environment variables:
      - GEMINI_API_KEY (required)
      - GEMINI_MODEL (optional; defaults to Gemini 2.5 Flash)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Please export your Google AI Studio key."
        )
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    # Provider string follows the DSPy docs: 'gemini/<model-name>'
    lm = dspy.LM(f"gemini/{model}", api_key=api_key)
    dspy.configure(lm=lm)


# -----------------------------------
# MCP session + tool discovery helpers
# -----------------------------------

@asynccontextmanager
async def open_mcp_session(server_path: str, args: list[str] | None = None, env: dict | None = None):
    """Open an MCP stdio session and yield a live ClientSession.

    Example:
        async with open_mcp_session("./pokedex_mcp_server.py") as session:
            tools = await session.list_tools()
    """
    abs_path = os.path.abspath(server_path)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[abs_path] + (args or []),
        env=env,
    )
    async with stdio_client(server_params) as (read, write):
        session = ClientSession(read, write)
        # Older mcp SDKs do not accept a 'client_name' kwarg.
        # Initialize the session (older mcp SDKs may not support ClientInfo)
        await session.initialize()
        try:
            yield session
        finally:
            try:
                await session.close()
            except Exception:
                pass


async def gather_dspy_tools(session: ClientSession) -> List[dspy.Tool]:
    """Fetch MCP tools and convert them to DSPy tools."""
    tools_list = await session.list_tools()
    dspy_tools: List[dspy.Tool] = []
    for tool_info in tools_list.tools:
        dspy_tools.append(dspy.Tool.from_mcp_tool(session, tool_info))
    return dspy_tools


# ------------------------------
# DSPy Signature + ReAct Agent
# ------------------------------

class DexMCPAgentSig(dspy.Signature):
    """You are DexMCP, a tool-using Pokédex assistant.

    Use ONLY the provided tools for facts (types, stats, learnsets, move data, encounters).
    Do not invent values. Preserve numeric values exactly as returned by tools.
    When a game or generation is implied (e.g., ORAS/XY/USUM/SWSH/SV), pass the right
    version_group to tools. When uncertain, ask the user to specify the game/gen.
    Respond clearly and concisely.
    """

    user_request: str = dspy.InputField()
    answer: str = dspy.OutputField(desc="Factual response grounded in tool outputs.")


# ------------------------------
# Main routine (async)
# ------------------------------

async def run_agent(server: str, question: str, list_tools: bool = False, show_trajectory: bool = False) -> str:
    configure_gemini_from_env()

    async with open_mcp_session(server) as session:
        dspy_tools = await gather_dspy_tools(session)
        if list_tools:
            print("Available tools:")
            for t in dspy_tools:
                print(f"- {t.name}({', '.join(t.args.keys())})")

        react = dspy.ReAct(DexMCPAgentSig, tools=dspy_tools)

        # IMPORTANT: MCP tools are async; use .acall()
        pred = await react.acall(user_request=question)
        if show_trajectory and hasattr(pred, "trajectory"):
            print("\n--- Trajectory ---")
            try:
                # Pretty-print if possible
                print(json.dumps(pred.trajectory, indent=2, ensure_ascii=False))
            except Exception:
                print(pred.trajectory)
        return pred.answer


# ------------------------------
# CLI
# ------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DexMCP DSPy Client (Gemini)")
    p.add_argument("--server", default="./pokedex_mcp_server.py", help="Path to the MCP server script (stdio)")
    p.add_argument("--ask", default="Show Garchomp base stats and abilities, then list all level-up moves in ORAS.", help="User request to answer")
    p.add_argument("--list-tools", action="store_true", help="List discovered tools and exit")
    p.add_argument("--trajectory", action="store_true", help="Print the agent's thought/action trajectory")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        answer = asyncio.run(
            run_agent(
                server=args.server,
                question=args.ask,
                list_tools=args.list_tools,
                show_trajectory=args.trajectory,
            )
        )
        print("\n=== Answer ===\n" + str(answer))
    except KeyboardInterrupt:
        print("Interrupted.")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
