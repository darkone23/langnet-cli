# 📜 GenAI Model Selection

## 1. Overview: The Multi-Model MoE Approach

In the current development landscape, the most efficient way to build complex software is not through a "one chatbot to rule them all" model but through focused and dynamic model routing. This strategy treats various Large Language Models (LLMs) as specialized team members, routing tasks based on their specific strengths in reasoning, execution speed, or context handling.

By utilizing **OpenRouter** to access high-performance open-weight models, development teams can match (and sometimes exceed) the performance of proprietary models like Claude Opus or GPT-5 at **1/10th of the cost**.

---

## 2. The Expert Persona Matrix

This matrix defines which model "Persona" should be used for specific development tasks.

> nb: the model frontier is an evolving space and so these examples may become quite outdated

| Persona | Task Category | Primary Model | Market Alternative | Rationale |
| --- | --- | --- | --- | --- |
| **The Architect** | System Design, Planning | `deepseek/deepseek-v3.2-speciale` | `kimi/kimi-k2-thinking` | High "Chain-of-Thought" reasoning; best for complex logic. |
| **The Detective** | Debugging, Root Cause | `zhipuai/glm-4.7` | `mistral/mistral-large-3` | "Sober" and conservative; less likely to hallucinate fixes. |
| **The Refactorer** | Optimization, Style | `minimax/minimax-m2.1` | `qwen/qwen3-235b` | High throughput and 200K+ context for rewriting large modules. |
| **The Implementer** | Feature Build, Tests | `zhipuai/glm-4.5-air` | `meta/llama-4-scout` | Fast execution with reliable tool-use for agentic "build" loops. |
| **The Scribe** | Docs, Comments | `xiaomi/mimo-v2-flash` | `google/gemini-2.5-flash` | Ultra-low cost for high-volume English prose generation. |
| **The Auditor** | Code Review, Security | `openai/gpt-oss-120b` | `zhipuai/glm-4.7` | Peak instruction following; identifies edge cases and security leaks. |

---

## 3. Tooling & Integration

This project has chosen to standardize on **OpenCode** (CLI) and **OpenRouter** (Unified API) to manage this multi-model workflow.

### Initial Setup

1. **Install OpenCode:**

Visit the upstream project documentation for accurate instructions.

2. **Configure Environment:**

Add the following to your `.zshrc` or `.bashrc`:
```bash
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your_openrouter_key

```

3. **Initialize Project:**

Your project should have an AGENTS.md file for configuring the system prompt for opencode.

If you need to create one:

Run `/init` in your project root to allow OpenCode to map the repository structure and create an `AGENTS.md` file.

### Advanced Configuration (`opencode.json`)

Define variants in your configuration to toggle between "thinking" modes and "execution" modes:

```json
{
  "models": {
    "deepseek/v3.2-speciale": {
      "variants": { "architect": { "options": { "reasoningEffort": "high" } } }
    },
    "zhipuai/glm-4.7": {
      "variants": { "detective": { "options": { "temperature": 0.1 } } }
    }
  }
}

```

> Notice the `temperature` setting: higher values mean more variation in the token generation and lower values mean the output is statistically bound to the training set. Think of an essay that always repeats the same phrases (low temp) vs excessive use of a thesaurus (high temp). 


---

## 4. Operational Workflow Examples

### Step A: The Planning Phase

**Persona:** The Architect
**Command:**

```bash
/model openrouter/deepseek/deepseek-v3.2-speciale:architect
/plan "Design a refactor for the auth layer to support header based authentication."

```

* **Goal:** Generate a high-level `implementation_plan.md` that accounts for security and scalability.

### Step B: The Building Phase

**Persona:** The Implementer
**Command:**

```bash
/model openrouter/zhipuai/glm-4.5-air
/build "Follow the implementation_plan.md. Create the new routers and update the User model."

```

* **Goal:** High-speed code generation based on a pre-validated plan.

### Step C: The Hard Debugging Phase

**Persona:** The Detective
**Command:**

```bash
/model openrouter/zhipuai/glm-4.7:detective
/improve "The new auth layer is throwing a RecursionError in the dependency injection. Find and fix it."

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
