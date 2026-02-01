
import os

# Import aisuite after patching
import aisuite as ai
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Simple tool function: print output
def print_formatted_output(text: str):
    """A simple tool that prints text."""
    print(f"[TOOL] Printed: {text}")
    return {"success": True, "output": text}

class AiSuiteHelpers:

    @staticmethod
    def get_openapi_client() -> ai.Client | None:
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY", "NOTSET")
        api_base = os.getenv("OPENAI_API_BASE",
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )

        if not api_key or api_key == "NOTSET":
            # print("Error: OPENAI_API_KEY not found in .env file")
            # print("Create a .env file with:")
            # print("OPENAI_API_KEY=your_api_key_here")
            # print("OPENAI_API_BASE=https://openrouter.ai/api/v1  # Optional")
            # sys.exit(1)
            return None

        # Configure client - use minimal configuration
        # nb: must setenv for openai client
        os.environ["OPENAI_BASE_URL"] = api_base
        client = ai.Client({
            "api_key": api_key,
        })
        return client

    @staticmethod
    def print_tool_calls(response):
        for msg in response.choices[0].intermediate_messages:
            if hasattr(msg, 'role'):
                print(f"{msg.role}: {msg.content[:100]}...")
            if hasattr(msg, 'tool_calls') and getattr(msg, 'tool_calls') is not None:
                for call in msg.tool_calls:
                    print(f"Tool: {call.function.name}")
                    print(f"Args: {call.function.arguments}")
            if hasattr(msg, 'tool_call_id'):
                print(f"Tool Result: {msg.content}")

def main():
    """Main example function"""

    print("\n=== Example 1: Simple Tool Call ===")

    client = AiSuiteHelpers.get_openapi_client()
    assert client is not None, "Please configure your OPENAI environment"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. ",
                "Use the print_formatted_output tool when asked to print something."
            )
        },
        {
            "role": "user",
            "content": "Please print a hello world message using the tool."
        },
    ]

    # Make request with tools
    response = client.chat.completions.create(
        model="openai:gpt-4o-mini",
        messages=messages,
        tools=[print_formatted_output],
        max_turns=2 # must be greater than 1 for tool usage
    )

    print("Model: openai:gpt-4o-mini")
    AiSuiteHelpers.print_tool_calls(response)

    # Access all intermediate messages

    print("\n=== Example completed! ===")


if __name__ == "__main__":
    main()
