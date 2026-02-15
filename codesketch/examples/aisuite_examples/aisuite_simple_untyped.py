"""
AISuite Simple Tool Calling Example (Untyped)

Demonstrates basic tool calling with aisuite using raw dicts.
This is the simplest approach - no dataclasses or cattrs needed.
"""

import os

import aisuite as ai
import dotenv

dotenv.load_dotenv()


def get_openapi_client() -> ai.Client | None:
    api_key = os.getenv("OPENAI_API_KEY", "NOTSET")
    api_base = os.getenv(
        "OPENAI_API_BASE", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )

    if not api_key or api_key == "NOTSET":
        return None

    os.environ["OPENAI_BASE_URL"] = api_base
    return ai.Client({"api_key": api_key})


def main():
    print("\n=== Example: Simple Chat ===\n")

    client = get_openapi_client()
    if not client:
        print("Error: OPENAI_API_KEY not configured")
        return

    system_msg = (
        "You are a helpful assistant who responds with a single concise sentence."
    )

    user_msg = (
        "Why should someone study classical language?"
    )

    print(f"Q: {user_msg}")

    messages = [
        {
            "role": "system",
            "content": system_msg,
        },
        {"role": "user", "content": user_msg},
    ]

    response = client.chat.completions.create(
        model="openai:gpt-4o-mini",
        messages=messages,
        tools=[],
        # max_turns=2,
    )

    print(f"A: {response.choices[0].message.content}")

    # print("Model: openai:gpt-4o-mini")
    # print("\nIntermediate messages:")
    # for msg in response.choices[0].intermediate_messages:
    #     if hasattr(msg, "role"):
    #         print(f"  {msg.role}: {msg.content[:100]}...")
    #     if hasattr(msg, "tool_calls") and msg.tool_calls:
    #         for call in msg.tool_calls:
    #             print(f"  Tool: {call.function.name}")
    #             print(f"  Args: {call.function.arguments}")
    #     if hasattr(msg, "tool_call_id"):
    #         print(f"  Result: {msg.content}")

    print("\n=== Example completed! ===\n")


if __name__ == "__main__":
    main()
