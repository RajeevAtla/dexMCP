from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

from pydantic import BaseModel, Field, create_model

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - fallback for older LangChain installs
    from langchain.chat_models import ChatOpenAI  # type: ignore


DEMO_REQUESTS: Tuple[str, ...] = (
    "Show Garchomp's base stats then list all level-up moves in ORAS.",
    "Analyze the defensive type coverage for pikachu, garchomp, and gyarados and call out weaknesses.",
    "List Gengar's abilities with hidden ability notes and short effect summaries.",
    "Explain Eevee's full evolution paths including branching requirements.",
    "Where can I encounter dratini in firered-leafgreen and what are the encounter methods?",
    "Summarize Sylveon's breeding groups, hatch steps, and any egg moves in sword-shield.",
    "Recommend a competitive moveset for greninja in sun-moon using level-up or tutor moves only.",
)

SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["dexmcp/dexmcp_server.py"],
    env=None,
)

TYPE_MAP: Dict[str, Type[Any]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


@dataclass
class ToolSpec:
    """Hold the parsed schema and LangChain tool for an MCP endpoint."""

    mcp_tool: Tool
    args_model: Type[BaseModel]
    structured_tool: StructuredTool


def _json_schema_to_annotation(schema: Dict[str, Any]) -> Type[Any]:
    schema_type = schema.get("type", "string")
    if schema_type == "array":
        items_schema = schema.get("items", {})
        inner = _json_schema_to_annotation(items_schema) if items_schema else Any
        return List[inner]
    if schema_type == "object":
        return Dict[str, Any]
    return TYPE_MAP.get(schema_type, str)


def _build_args_model(tool: Tool) -> Type[BaseModel]:
    properties = tool.input_schema.get("properties", {}) if tool.input_schema else {}
    required = set(tool.input_schema.get("required", [])) if tool.input_schema else set()

    if not properties:
        return create_model(
            f"{tool.name.title().replace('-', '').replace('_', '')}Args",
            payload=(Dict[str, Any], Field(default_factory=dict)),
        )

    fields: Dict[str, Tuple[Type[Any], Field]] = {}
    for prop_name, prop_schema in properties.items():
        annotation = _json_schema_to_annotation(prop_schema)
        description = prop_schema.get("description")
        default = prop_schema.get("default")
        is_required = prop_name in required and default is None

        if not is_required:
            annotation = Optional[annotation]  # type: ignore[assignment]
            default = default if default is not None else None
            field_info = Field(default=default, description=description)
        else:
            field_info = Field(..., description=description)

        fields[prop_name] = (annotation, field_info)

    model_name = f"{tool.name.title().replace('-', '').replace('_', '')}Args"
    return create_model(model_name, **fields)  # type: ignore[arg-type]


def _format_content(content: Iterable[Any]) -> str:
    parts: List[str] = []
    for item in content:
        if hasattr(item, "text") and getattr(item, "text"):
            parts.append(getattr(item, "text"))
        elif hasattr(item, "data") and getattr(item, "data"):
            parts.append(json.dumps(getattr(item, "data"), indent=2))
        elif hasattr(item, "model_dump"):
            parts.append(json.dumps(item.model_dump(), indent=2))
        else:
            parts.append(str(item))
    return "\n".join(parts)


async def _build_tool_specs(session: ClientSession) -> List[ToolSpec]:
    tool_listing = await session.list_tools()
    specs: List[ToolSpec] = []

    for mcp_tool in tool_listing.tools:
        args_model = _build_args_model(mcp_tool)

        async def call_tool(_args_model=args_model, _tool_name=mcp_tool.name, **kwargs: Any) -> str:
            validated = _args_model(**kwargs)
            result = await session.call_tool(
                _tool_name,
                arguments=validated.model_dump(exclude_none=True),
            )
            return _format_content(result.content)

        tool = StructuredTool(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
            args_schema=args_model,
            coroutine=call_tool,
        )
        specs.append(ToolSpec(mcp_tool=mcp_tool, args_model=args_model, structured_tool=tool))
    return specs


async def run_agent(prompt: str, model: str) -> None:
    llm = ChatOpenAI(model=model, temperature=0)

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_specs = await _build_tool_specs(session)
            tools = [spec.structured_tool for spec in tool_specs]

            system_message = (
                "You are DexMCP, a knowledgeable Pokedex assistant. Use the provided tools to satisfy requests. "
                "Always cite tool results in concise natural language."
            )
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )

            agent = create_tool_calling_agent(llm, tools, prompt_template)
            executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            result = await executor.ainvoke({"input": prompt})
            print(result.get("output", "<no output>"))


def run_demo(prompts: Iterable[str], model: str) -> None:
    for prompt in prompts:
        print("\n=== {} ===".format(prompt))
        asyncio.run(run_agent(prompt, model=model))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DexMCP LangChain demo client.")
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
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Chat model identifier passed to LangChain's ChatOpenAI wrapper (default: gpt-4o-mini).",
    )
    args = parser.parse_args()

    if args.prompt and not args.demo:
        asyncio.run(run_agent(args.prompt, model=args.model))
    else:
        prompts = DEMO_REQUESTS if not args.prompt else (args.prompt, *DEMO_REQUESTS)
        run_demo(prompts, model=args.model)


if __name__ == "__main__":
    main()
