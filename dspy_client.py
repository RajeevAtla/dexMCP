from __future__ import annotations

import argparse
from typing import Iterable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import dspy

# DSPy example client that brokers MCP tools into a ReAct workflow.
# The script is intentionally small so readers can reuse the pattern elsewhere.

# Demonstration prompts that exercise the richer tool surface.
DEMO_REQUESTS = (
    "Show Garchomp's base stats then list all level-up moves in ORAS.",
    "Analyze the defensive type coverage for pikachu, garchomp, and gyarados and call out weaknesses.",
    "List Gengar's abilities with hidden ability notes and short effect summaries.",
    "Explain Eevee's full evolution paths including branching requirements.",
    "Where can I encounter dratini in firered-leafgreen and what are the encounter methods?",
    "Summarize Sylveon's breeding groups, hatch steps, and any egg moves in sword-shield.",
    "Recommend a competitive moveset for greninja in sun-moon using level-up or tutor moves only.",
)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["dexmcp/server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

# Run the MCP server as a subprocess over stdio so any MCP-aware host can reuse this config.


class DSPyPokedex(dspy.Signature):
    """You are an agentic pokedex. Choose and chain the right tools to satisfy user requests."""

    user_request: str = dspy.InputField()
    process_result: str = dspy.OutputField(
        desc=(
            "Message that summarizes the process result, and the information users need, "
            "e.g., the Pokedex entry if it's a Pokemon lookup request."
        )
    )


# Use the hosted Gemini model so the example works without local weights.
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash"))


async def run_request(user_request: str) -> None:
    """Connect to the MCP server, expose its tools to DSPy, and run a ReAct plan."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Establish the MCP session and discover available tools.
            await session.initialize()
            tools = await session.list_tools()

            # Convert the wire-level MCP descriptions into DSPy Tool objects the agent can call.
            dspy_tools = [dspy.Tool.from_mcp_tool(session, tool) for tool in tools.tools]

            # Instantiate a lightweight ReAct agent that can plan/tool-call using the signature above.
            react = dspy.ReAct(DSPyPokedex, tools=dspy_tools)

            result = await react.acall(user_request=user_request)
            print(result)


def run_demo(prompts: Iterable[str]) -> None:
    """Sequentially execute several demo prompts so each new endpoint is exercised."""
    import asyncio

    for prompt in prompts:
        print("\n=== {} ===".format(prompt))
        asyncio.run(run_request(prompt))


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description="Run the DexMCP DSPy demo client.")
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Custom natural-language request for the agent. If omitted, demo prompts run.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Force running the built-in demo prompts even if a custom prompt is supplied.",
    )
    args = parser.parse_args()

    if args.prompt and not args.demo:
        asyncio.run(run_request(args.prompt))
    else:
        run_demo(DEMO_REQUESTS if not args.prompt else (args.prompt, *DEMO_REQUESTS))
