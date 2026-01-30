# AI Persona Routing Guide

This guide shows how to effectively use the multi-model AI personas for different development tasks in langnet-cli.

## Quick Reference

| Task Type | Recommended Persona | Command | Example |
|-----------|-------------------|---------|---------|
| **Architecture & Planning** | The Architect<br>`openrouter/deepseek/deepseek-v3.2:architect` | `/plan` or `/model` | `/model openrouter/deepseek/deepseek-v3.2:architect`<br>`/plan "Design caching layer for Sanskrit morphology"` |
| **Implementation & Coding** | The Implementer<br>`openrouter/zhipuai/glm-4.5-air:implementer` | `/build` or `/model` | `/model openrouter/zhipuai/glm-4.5-air:implementer`<br>`/build "Implement CDSL dictionary backend"` |
| **Debugging & Troubleshooting** | The Detective<br>`openrouter/zhipuai/glm-4.7:detective` | `/improve` or `/model` | `/model openrouter/zhipuai/glm-4.7:detective`<br>`/improve "Fix deadlock in Diogenes scraper"` |
| **Refactoring & Optimization** | The Refactorer<br>`openrouter/minimax/minimax-m2.1:refactorer` | `/compact` or `/model` | `/model openrouter/minimax/minimax-m2.1:refactorer`<br>`"Refactor cache module for better performance"` |
| **Documentation & Comments** | The Scribe<br>`openrouter/xiaomi/mimo-v2-flash:scribe` | Plain prompt | `/model openrouter/xiaomi/mimo-v2-flash:scribe`<br>`"Document the new API endpoints"` |
| **Code Review & Security** | The Auditor<br>`openrouter/openai/gpt-oss-120b:auditor` | `/review` | `/model openrouter/openai/gpt-oss-120b:auditor`<br>`/review "Check for security vulnerabilities"` |

## Complete Development Workflows

### New Feature Development

```bash
# Phase 1: Design (Architect)
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Design a new Old Norse dictionary integration with morphology parsing"

# Phase 2: Implementation (Implementer)
/model openrouter/zhipuai/glm-4.5-air:implementer
/build "Implement the Old Norse backend using the design plan"

# Phase 3: Documentation (Scribe)
/model openrouter/xiaomi/mimo-v2-flash:scribe
"Add comprehensive docstrings and API documentation for the Old Norse backend"

# Phase 4: Review (Auditor)
/model openrouter/openai/gpt-oss-120b:auditor
/review "Review the Old Norse implementation for security and edge cases"

# Phase 5: Testing (Implementer)
/model openrouter/zhipuai/glm-4.5-air:implementer
"Write unit and integration tests for the Old Norse backend"
```

### Bug Fix Workflow

```bash
# Phase 1: Investigation (Detective)
/model openrouter/zhipuai/glm-4.7:detective
/improve "Investigate the RecursionError in the Diogenes parser with long Greek texts"

# Phase 2: Fix (Implementer)
/model openrouter/zhipuai/glm-4.5-air:implementer
"Implement the fix based on the investigation findings"

# Phase 3: Refactoring (Refactorer)
/model openrouter/minimax/minimax-m2.1:refactorer
"Refactor the parser to prevent similar issues in the future"

# Phase 4: Review (Auditor)
/model openrouter/openai/gpt-oss-120b:auditor
/review "Check if the fix introduces any new issues"
```

### Performance Optimization

```bash
# Phase 1: Analysis (Detective)
/model openrouter/zhipuai/glm-4.7:detective
/improve "Identify performance bottlenecks in the CDSL lookup system"

# Phase 2: Design (Architect)
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Design a new caching strategy for Sanskrit dictionary lookups"

# Phase 3: Implementation (Implementer)
/model openrouter/zhipuai/glm-4.5-air:implementer
"Implement the caching strategy"

# Phase 4: Refactoring (Refactorer)
/model openrouter/minimax/minimax-m2.1:refactorer
"Optimize the existing code for better memory usage"
```

## Skill-Specific Persona Mapping

Each skill has a recommended persona already integrated:

| Skill | Primary Persona | Secondary Persona |
|-------|----------------|-------------------|
| **Backend Integration** | Architect | Implementer |
| **API Development** | Implementer | Architect |
| **Data Models** | Architect | Refactorer |
| **Testing** | Implementer | Detective |
| **Debugging** | Detective | Refactorer |
| **Code Style** | Refactorer | Architect |
| **Cache Management** | Refactorer | Implementer |
| **CLI Development** | Implementer | Scribe |

## Cost Optimization Tips

1. **Use Air/Flash models for routine work**: GLM-4.5-Air and MIMO-v2-Flash are excellent for implementation and documentation
2. **Reserve DeepSeek-v3.2 for planning**: Use Architect persona only for complex architecture decisions
3. **Use `/compact` for long conversations**: MiniMax M2.1 is great for summarizing context
4. **Review with a different model**: Always use Auditor persona after Implementer work
5. **Batch similar tasks**: Group documentation work for Scribe, debugging for Detective

## Environment Setup

Make sure your environment is configured:
```bash
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your_openrouter_key_here
```

## Example: Adding New Language Support

```bash
# Research and planning
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Research available resources for Old Norse and design integration"

# Implementation
/model openrouter/zhipuai/glm-4.5-air:implementer
/build "Create Old Norse backend module with dictionary integration"

# Data models
/model openrouter/deepseek/deepseek-v3.2:architect
"Design dataclasses for Old Norse morphology results"

# Testing
/model openrouter/zhipuai/glm-4.5-air:implementer
"Write comprehensive tests for Old Norse backend"

# Documentation
/model openrouter/xiaomi/mimo-v2-flash:scribe
"Document the Old Norse features and usage examples"

# Review
/model openrouter/openai/gpt-oss-120b:auditor
/review "Check the Old Norse implementation for completeness and security"
```

## Troubleshooting

**Model not responding?**
```bash
# Try switching to a lighter model
/model openrouter/zhipuai/glm-4.5-air:implementer
```

**Complex task failing?**
```bash
# Break it down and use Architect first
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Break down the complex task into smaller steps"
```

**Need better quality?**
```bash
# Use Auditor for review
/model openrouter/openai/gpt-oss-120b:auditor
/review "Improve the quality of this implementation"
```

## See Also

- `.opencode/opencode.json` - Model configuration
- `.opencode/skills/` - Individual skill guides with persona recommendations
- [LLM_PROVIDER_GUIDE.md](../../LLM_PROVIDER_GUIDE.md) - Multi-model strategy
- [AGENTS.md](../../AGENTS.md) - Project context