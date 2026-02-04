# Multi-Model AI Development: Complete How-To Guide

## Quick Start

### 1. **Setup OpenRouter**
```bash
# Add to your shell config (.bashrc/.zshrc)
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your_openrouter_key_here
```

### 2. **Basic Usage**
```bash
# Switch personas using @mention syntax
@architect "Design a new Sanskrit morphology system"

@coder "Implement the morphology system"

# Get help choosing personas
just autobot model list          # List all available personas
just autobot model suggest "debugging"  # Get recommended persona
just autobot model skill testing  # Get persona for testing skill
```

## Persona Reference Cheatsheet

| Persona | Model | Best For | Example Command |
|---------|-------|----------|-----------------|
| **The Architect** | `deepseek/deepseek-v3.2` | System design, planning, complex logic | `@architect "Design new caching layer"` |
| **The Sleuth** | `z-ai/glm-4.7` | Debugging, root cause analysis | `@sleuth "Fix deadlock in parser"` |
| **The Artisan** | `minimax/minimax-m2.1` | Code optimization, style improvements | `@artisan "Refactor cache for performance"` |
| **The coder** | `z-ai/glm-4.5-air` | Feature development, testing | `@coder "Implement new API endpoint"` |
| **The Scribe** | `xiaomi/mimo-v2-flash` | Documentation, comments, prose | `@scribe "Document the new module"` |
| **The Auditor** | `openai/gpt-oss-120b` | Code review, security analysis | `@auditor "Check for vulnerabilities"` |

## Complete Workflow Examples

### Example 1: Adding a New Backend

```bash
# 1. Research and Design (Architect)
@architect "Design Old Norse dictionary integration with morphology parsing"

# 2. Implementation (coder)
@coder "Create Old Norse backend module following the design"

# 3. Data Models (Architect)
@architect "Design dataclass models for Old Norse morphology results"

# 4. Testing (coder)
@coder "Write comprehensive tests for Old Norse backend"

# 5. Documentation (Scribe)
@scribe "Document the Old Norse integration API and usage"

# 6. Review (Auditor)
@auditor "Check Old Norse implementation for security issues"
```

### Example 2: Debugging a Performance Issue

```bash
# 1. Investigation (Sleuth)
@sleuth "Debug memory leak in DuckDB cache"

# 2. Fix Implementation (coder)
@coder "Implement memory leak fix based on findings"

# 3. Optimization (Artisan)
@artisan "Optimize cache memory usage after fix"

# 4. Testing (coder)
@coder "Add tests to prevent regression"

# 5. Review (Auditor)
@auditor "Check if optimization introduces edge cases"
```

### Example 3: Refactoring Legacy Code

```bash
# 1. Analysis (Sleuth)
@sleuth "Analyze spaghetti code in diogenes module"

# 2. Design (Architect)
@architect "Design modular refactoring for diogenes"

# 3. Implementation (coder)
@coder "Implement modular refactoring step by step"

# 4. Refactoring (Artisan)
@artisan "Clean up code style and improve readability"

# 5. Documentation (Scribe)
@scribe "Update module documentation with new architecture"
```

## Skill-Persona Mapping Reference

All 10 skills are mapped to personas:

| Skill | Persona | When to Use |
|-------|---------|-------------|
| **backend-integration.md** | Architect | Designing new backends, system architecture |
| **data-models.md** | Architect | Schema design, complex type systems |
| **api-development.md** | coder | API implementation, endpoint development |
| **testing.md** | coder | Test writing, debugging failures |
| **debugging.md** | sleuth | Troubleshooting, root cause analysis |
| **code-style.md** | Artisan | Code optimization, linting improvements |
| **cache-management.md** | Artisan | Performance optimization, cache design |
| **cli-development.md** | coder | CLI command implementation |
| **multi-model-ai.md** | coder | AI workflow setup and configuration |
| **persona-routing.md** | coder | Persona selection guidance |
| **project-tools.md** | coder | Autobot command development |

## Advanced Techniques

### 1. **Cost Optimization**
```bash
# Use cheaper models for routine tasks
@scribe "Documentation tasks"           # $0.50/M tokens
@coder "Feature implementation"         # $0.15/M tokens

# Reserve expensive models for critical tasks
@architect "Complex system design"      # $3.50/M tokens
@auditor "Security critical review"     # $5.00/M tokens
```

### 2. **Context Management**
```bash
# Use Artisan for context summarization
@artisan "Summarize the conversation about Sanskrit backend"
```

### 3. **Quality Assurance**
```bash
# Always review with different model than implementation
# Implementation
@coder "Feature implementation"

# Review with fresh perspective
@auditor "Check implementation for edge cases"
```

## Common Patterns

### Pattern 1: Feature Development Loop
```bash
# Design → Implement → Document → Review
@architect → "Plan feature"
@coder → "Build feature"
@scribe → "Document"
@auditor → "Review"
```

### Pattern 2: Bug Fix Loop
```bash
# Investigate → Fix → Test → Optimize
@sleuth → "Investigate"
@coder → "Fix"
@coder → "Add tests"
@artisan → "Simplify code"
```

### Pattern 3: Refactoring Loop
```bash
# Analyze → Design → Refactor → Document
@sleuth → "Analyze"
@architect → "Plan"
@artisan → "Refactor"
@scribe → "Update docs"
```

## Using Autobot for Guidance

```bash
# Get persona recommendations for tasks
just autobot model suggest "performance optimization"
# Output: artisan

just autobot model suggest "design new schema"
# Output: architect

# Check persona for specific skill
just autobot model skill debugging
# Output: sleuth with example commands

# List all available personas
just autobot model list

# Show configuration status
just autobot model config

# Export configurations
just autobot model export json > personas.json
```

## Troubleshooting

### Issue: Model Not Responding
```bash
# Check configuration
just autobot model config

# Switch to lighter model
@coder

# Check OpenRouter status
curl https://openrouter.ai/api/v1/models
```

### Issue: Wrong Persona for Task
```bash
# Get recommendation
just autobot model suggest "your specific task"

# Manual override if needed
# (Sometimes you know best what you need)
```

### Issue: Cost Concerns
```bash
# Use cheaper models first
@scribe "Documentation tasks"           # Cheapest
@coder "Feature implementation"         # Good balance

# Only use expensive models when needed
@architect "Complex system design"      # Complex design
@auditor "Security critical review"     # Critical review
```

## Best Practices

1. **Start with Sleuth** for debugging issues
2. **Use Architect for planning**, coder for coding
3. **Always Document with Scribe** after implementation
4. **Review with Auditor** for critical code
5. **Refine with Artisan** after features work
6. **Batch similar tasks** to stay in same persona
7. **Check cost** before using expensive models

## Getting Started Exercises

### Exercise 1: Add a Simple Feature
```bash
# 1. Use autobot to get persona for feature development
just autobot model suggest "feature implementation"

# 2. Switch to recommended persona
# 3. Implement feature
# 4. Document with Scribe
# 5. Review with Auditor
```

### Exercise 2: Fix a Bug
```bash
# 1. Use Sleuth to investigate
# 2. Use coder to fix
# 3. Use Scribe to update documentation
# 4. Use Artisan to optimize and refine if needed
```

### Exercise 3: Improve Performance
```bash
# 1. Use Sleuth to find bottlenecks
# 2. Use Architect to design solution
# 3. Use coder to implement
# 4. Use Artisan to cleanup
```

## Next Steps

1. **Set up environment**: Export OpenRouter API key
2. **Try basic commands**: Start with `just autobot model list`
3. **Pick a task**: Choose from skills list
4. **Select persona**: Use autobot or manual selection
5. **Follow workflow**: Design → Implement → Document → Review

## See Also

- `.opencode/opencode.json` - Model configurations
- `.opencode/skills/persona-routing.md` - Detailed workflows
- `just autobot model --help` - All available commands
- OpenRouter pricing: https://openrouter.ai/pricing
