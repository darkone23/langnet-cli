"""
AISuite Tool Calling Example

Simple tool calling with aisuite, then mapping results to typed dataclasses.
"""

import json
import os
import random
from dataclasses import dataclass

import aisuite as ai
import cattrs
import dotenv
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

dotenv.load_dotenv()
console = Console()
_converter = cattrs.Converter(omit_if_default=True)


# ===== Typed response classes (mapped from raw API output) =====


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall]
    model: str


# ===== Tool (plain function, string args) =====


def choose_topic(category: str, options: str) -> str:
    """Choose one AI topic from a list."""

    # print(f"called with: {category} - {options}")
    opts = (
        [o.strip() for o in options.split(",")] if options else ["magic the gathering", "pokemon"]
    )
    selected = random.choice(opts)
    print(f"[TOOL] Chose: {selected}")
    return f"Selected: {selected}"


# ===== Output mapper =====


def to_typed_response(raw_response, model: str = "unknown") -> ChatResponse:
    """Map raw aisuite response to typed dataclass."""
    content = ""
    tool_calls = []

    for msg in raw_response.choices[0].intermediate_messages:
        if hasattr(msg, "role") and msg.role == "assistant" and msg.content:
            content = msg.content
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = (
                        json.loads(tc.function.arguments)
                        if isinstance(tc.function.arguments, str)
                        else {}
                    )
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

    return ChatResponse(content=content, tool_calls=tool_calls, model=model)


# ===== Client helper =====


def get_client() -> ai.Client | None:
    api_key = os.getenv("OPENAI_API_KEY", "NOTSET")
    base = os.getenv("OPENAI_API_BASE", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    if not api_key or api_key == "NOTSET":
        return None
    os.environ["OPENAI_BASE_URL"] = base
    return ai.Client({"api_key": api_key})


def format_tool(tc: ToolCall) -> Panel:
    return Panel(
        JSON(json.dumps(tc.arguments, indent=2)),
        title=f"[bold cyan]Tool: {tc.name}[/bold cyan]",
        border_style="cyan",
        expand=False,
    )


# ===== Demo =====


def main():
    print("\n=== AISuite Demo: Topic Chooser ===\n")

    client = get_client()
    if not client:
        console.print(
            Panel(
                "[yellow]Set OPENAI_API_KEY to run[/yellow]",
                title="Configuration Required",
                border_style="yellow",
            )
        )
        return

    msg = (
        "Choose one computer science topic from: "
        "transformers, reinforcement learning, "
        "computer vision, natural language processing"
    )
    console.print(
        Panel(
            f"[bold]User:[/bold] {msg}",
            title="Conversation",
            border_style="blue",
        )
    )

    messages = [
        {"role": "system", "content": "You are a helpful tutor."},
        {
            "role": "system",
            "content": (
                "When given a topic you describe the fundamentals "
                "in one short and concise paragraph."
            ),
        },
        {"role": "user", "content": msg},
    ]

    raw = client.chat.completions.create(
        model="openai:gpt-4o-mini",
        messages=messages,
        tools=[choose_topic],
        max_turns=2,
    )

    # Map to typed dataclass
    response = to_typed_response(raw, model="gpt-4o-mini")

    console.print(
        Panel(
            f"[bold]Assistant:[/bold] {response.content}",
            title="Response",
            border_style="green",
        )
    )

    if response.tool_calls:
        console.print(
            Panel(
                f"[bold]Tool Calls:[/bold] {len(response.tool_calls)}",
                title="Activity",
                border_style="cyan",
            )
        )
        for tc in response.tool_calls:
            console.print(format_tool(tc))


if __name__ == "__main__":
    main()
