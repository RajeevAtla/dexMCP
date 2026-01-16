"""Gradio demo that fronts DexMCP via a LangChain agent."""

from __future__ import annotations

import argparse
import json
import sys
import types as _types
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

# Gradio depends on rich, which imports core_types on Python 3.13.
# Provide a lightweight shim to keep the demo importable.
if "core_types" not in sys.modules:
    import types as _std_types

    core_types = _types.ModuleType("core_types")
    core_types.FrameType = _std_types.FrameType
    core_types.MappingProxyType = _std_types.MappingProxyType
    core_types.ModuleType = _std_types.ModuleType
    core_types.TracebackType = _std_types.TracebackType
    sys.modules["core_types"] = core_types

import gradio as gr
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
    args=["dexmcp/server.py"],
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


async def _run_agent(prompt: str, model: str) -> str:
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
            executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
            result = await executor.ainvoke({"input": prompt})
            return result.get("output", "<no output>")


async def _chat_handler(message: str, history: list[tuple[str, str]], model: str) -> str:
    if not message.strip():
        return "Please enter a request."
    return await _run_agent(message, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DexMCP LangChain + Gradio demo.")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Chat model identifier passed to LangChain's ChatOpenAI wrapper.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for the Gradio server.")
    parser.add_argument("--port", type=int, default=7860, help="Port for the Gradio server.")
    parser.add_argument("--share", action="store_true", help="Share the Gradio app publicly.")
    args = parser.parse_args()

    examples = [[prompt, args.model] for prompt in DEMO_REQUESTS]

    with gr.Blocks(title="DexMCP Gradio Demo") as demo:
        gr.Markdown("# DexMCP Gradio Demo\nAsk DexMCP anything about Pokemon data.")
        model_input = gr.Textbox(label="Model", value=args.model)
        chat = gr.ChatInterface(
            fn=_chat_handler,
            additional_inputs=[model_input],
            examples=examples,
            title="DexMCP Agent",
        )
        chat.chatbot.label = "DexMCP"

    demo.queue().launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
