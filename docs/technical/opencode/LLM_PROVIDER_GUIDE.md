# GenAI Model Selection

## 1. Overview: The Multi-Model MoE Approach

In the current development landscape, the most efficient way to build complex software is not through a "one chatbot to rule them all" model but through focused and dynamic model routing. This strategy treats various Large Language Models (LLMs) as specialized team members, routing tasks based on their specific strengths in reasoning, execution speed, or context handling.

By using **OpenRouter** behind OpenCode personas, the project can route
planning, building, debugging, documentation, and review work to different
models without changing repository workflow.

---

## 2. The Expert Persona Matrix

This matrix defines which model "Persona" should be used for specific development tasks.

> nb: the model frontier is an evolving space and so these examples may become quite outdated

| Persona | Task Category | Primary Model | Rationale |
| --- | --- | --- | --- |
| **The Architect** | System Design, Planning | `deepseek/deepseek-v3.2` | High reasoning for complex logic. |
| **The Sleuth** | Debugging, Root Cause | `z-ai/glm-4.7` | Conservative debugging and root-cause work. |
| **The Artisan** | Optimization, Style | `minimax/minimax-m2.1` | High throughput for larger rewrites and style passes. |
| **The Coder** | Feature Build, Tests | `z-ai/glm-4.5-air` | Fast execution with reliable tool-use for build loops. |
| **The Scribe** | Docs, Comments | `xiaomi/mimo-v2-flash` | Low-cost prose generation. |
| **The Auditor** | Code Review, Security | `openai/gpt-oss-120b` | Strong instruction following for reviews and edge cases. |

---

## 3. Tooling & Integration

This project has chosen to standardize on **OpenCode** (CLI) and **OpenRouter** (Unified API) to manage this multi-model workflow.

### Initial Setup

1. **Install OpenCode:**

Use the project’s pinned OpenCode/OpenRouter setup where available. Do not
install new tools while working in this repository unless explicitly instructed.

2. **Configure Environment:**

Add the following to your `.zshrc` or `.bashrc`:
```bash
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your_openrouter_key

```

3. **Initialize Project:**

This project has an `AGENTS.md` file and `.opencode/opencode.json` persona
configuration.

Do not regenerate `AGENTS.md` as part of routine work; keep it aligned with the
current repository instructions.

### Advanced Configuration (`opencode.json`)

Define variants in your configuration to toggle between "thinking" modes and "execution" modes:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "architect": {
      "description": "System Design, Planning - High reasoning for complex logic",
      "model": "openrouter/deepseek/deepseek-v3.2",
      "options": {
        "reasoningEffort": "high"
      }
    },
    "sleuth": {
      "description": "Debugging, Root Cause - Conservative, less hallucination",
      "model": "openrouter/z-ai/glm-4.7",
      "options": {
        "temperature": 0.1
      }
    }
  },
  "provider": {
    "openrouter": {
      "baseURL": "https://openrouter.ai/api/v1"
    }
  }
}
```

Use `sleuth`, not the older `detective` name, when routing debugging work.


---

## 4. Operational Workflow Examples

### Step A: The Planning Phase

**Persona:** The Architect
**Command:**

```bash
@architect "Design a refactor for the auth layer to support header based authentication."
```

* **Goal:** Generate a high-level `implementation_plan.md` that accounts for security and scalability.

### Step B: The Building Phase

**Persona:** The Coder
**Command:**

```bash
@coder "Follow the implementation_plan.md. Create the new routers and update the User model."
```

* **Goal:** High-speed code generation based on a pre-validated plan.

### Step C: The Hard Debugging Phase

**Persona:** The Sleuth
**Command:**

```bash
@sleuth "The new auth layer is throwing a RecursionError in the dependency injection. Find and fix it."
```

* **Goal:** Leverage the "sober" logic of GLM to trace complex stack traces.

---

## 5. Cost & Quality Best Practices

* **The 90/10 Rule:** Use "Flash" or "Air" models (like `GLM-4.5-Air`) for 90% of boilerplate and documentation. Reserve "Speciale" or "Thinking" models for the 10% of tasks involving logic-heavy architecture.
* **Context Management:** Use `/compact` (MiniMax M2.1 is excellent for this) to summarize long chat histories into a single "State Memo" to save on input tokens.
* **Standardized Reviews:** Always use a different model for `/review` than the one used for `/build`. For example, if **GLM** built it, let **gpt-oss-120b** judge it.

For example, consider a **GitHub Action** that automatically triggers the "Auditor" persona on every new Pull Request.

### The Guardrail File (AGENTS.md)

The goal of your system prompts is to nudge the models to leverage your configured workflows, consider this extremely minimal example:


```

# Important Rules
  
Rule 1: Always use Python 3.12+ syntax and strict type hints.
Rule 2: Use the "Auditor" model for any file over 300 lines.
Rule 3: Never commit code without "The Scribe" generating unit tests first.

```
