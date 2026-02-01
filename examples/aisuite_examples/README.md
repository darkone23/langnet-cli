# AISuite Examples

Minimal approach - raw dicts, simple function, direct API calls.

```python
import aisuite as ai

def print_text(text: str) -> dict:
    return {"success": True, "output": text}

client = ai.Client({"api_key": api_key})
response = client.chat.completions.create(
    model="openai:gpt-4o-mini",
    messages=[{"role": "user", "content": "Print hello"}],
    tools=[print_text],
    max_turns=2,
)
```

