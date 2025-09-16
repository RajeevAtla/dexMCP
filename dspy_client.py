from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import dspy

# DSPy example client that brokers MCP tools into a ReAct workflow.
# The script is intentionally small so readers can reuse the pattern elsewhere.

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["dexmcp/dexmcp_server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

# Run the MCP server as a subprocess over stdio so any MCP-aware host can reuse this config.


class DSPyPokedex(dspy.Signature):
    """You are an agentic pokedex. You are given a list of tools to handle user requests.
    You should decide the right tool to use in order to fulfill users' requests."""

    user_request: str = dspy.InputField()
    process_result: str = dspy.OutputField(
        desc=(
            "Message that summarizes the process result, and the information users need, "
            "e.g., the Pokedex entry if it's a Pokémon lookup request."
        )
    )


dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash"))
# Use the hosted Gemini model so the example works without local weights.


async def run(user_request):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Establish the MCP session and discover available tools.
            await session.initialize()
            tools = await session.list_tools()

            # Convert the wire-level MCP descriptions into DSPy Tool objects the agent can call.
            dspy_tools = []
            for tool in tools.tools:
                dspy_tools.append(dspy.Tool.from_mcp_tool(session, tool))

            # Instantiate a lightweight ReAct agent that can plan/tool-call using the signature above.
            react = dspy.ReAct(DSPyPokedex, tools=dspy_tools)

            result = await react.acall(user_request=user_request)
            print(result)


if __name__ == "__main__":
    import asyncio

    # Sample prompt demonstrates a multi-step workflow that exercises multiple tools.
    asyncio.run(run("Show Garchomp's base stats then list all level-up moves in ORAS."))
