# Multi-Model AI Development

This skill describes how to use the multi-model AI development strategy implemented in langnet-cli.

## Overview

The project uses OpenRouter to access multiple specialized AI models, each optimized for different development tasks. This follows the "Expert Persona Matrix" approach where different AI personas handle specific parts of the development lifecycle.

## Persona Reference

### The Architect (`openrouter/deepseek/deepseek-v3.2:architect`)
- **Task Category**: System Design, Planning
- **When to Use**: High-level architecture decisions, complex logic design
- **Example Commands**:
  ```
  /model openrouter/deepseek/deepseek-v3.2:architect
  /plan "Design a new caching layer for Sanskrit morphology data"
  ```

### The Detective (`openrouter/zhipuai/glm-4.7:detective`)
- **Task Category**: Debugging, Root Cause Analysis
- **When to Use**: Complex bugs, hard-to-trace errors, logical issues
- **Example Commands**:
  ```
  /model openrouter/zhipuai/glm-4.7:detective
  /improve "Fix the RecursionError in the Diogenes parser when handling long Greek texts"
  ```

### The Refactorer (`openrouter/minimax/minimax-m2.1:refactorer`)
- **Task Category**: Optimization, Code Style
- **When to Use**: Large refactoring, code optimization, style improvements
- **Example Commands**:
  ```
  /model openrouter/minimax/minimax-m2.1:refactorer
  /compact "Summarize the current conversation state for context management"
  ```

### The Implementer (`openrouter/zhipuai/glm-4.5-air:implementer`)
- **Task Category**: Feature Build, Tests
- **When to Use**: Code generation, implementation, testing
- **Example Commands**:
  ```
  /model openrouter/zhipuai/glm-4.5-air:implementer
  /build "Implement the new Sanskrit lexicon integration based on the design plan"
  ```

### The Scribe (`openrouter/xiaomi/mimo-v2-flash:scribe`)
- **Task Category**: Documentation, Comments
- **When to Use**: Documentation generation, code comments, prose writing
- **Example Commands**:
  ```
  /model openrouter/xiaomi/mimo-v2-flash:scribe
  "Document the new API endpoints and add docstrings to the new functions"
  ```

### The Auditor (`openrouter/openai/gpt-oss-120b:auditor`)
- **Task Category**: Code Review, Security
- **When to Use**: Code review, security analysis, edge case identification
- **Example Commands**:
  ```
  /model openrouter/openai/gpt-oss-120b:auditor
  /review "Review the authentication changes for security vulnerabilities"
  ```

## Configuration

### Environment Setup
```bash
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your_openrouter_key
```

### Model Configuration File
The model configurations are stored in `.opencode/opencode.json`. This file defines:
- Agent configurations with persona-specific settings
- Model assignments for each persona
- Temperature settings and other options for each persona

## Operational Workflow Examples

### Complete Feature Development
1. **Planning**: Architect designs the feature architecture
2. **Implementation**: Implementer writes the code
3. **Documentation**: Scribe adds comments and documentation
4. **Review**: Auditor reviews for security and edge cases
5. **Debugging**: Detective fixes any issues that arise

### Example Workflow for New Backend
```bash
# Phase 1: Design
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Design a new Old Norse dictionary backend integration"

# Phase 2: Implementation
/model openrouter/zhipuai/glm-4.5-air:implementer
/build "Implement the Old Norse backend following the design plan"

# Phase 3: Documentation
/model openrouter/xiaomi/mimo-v2-flash:scribe
"Document the Old Norse backend API and usage examples"

# Phase 4: Review
/model openrouter/openai/gpt-oss-120b:auditor
/review "Review the Old Norse backend for security and correctness"
```

## Cost Optimization

### 90/10 Rule
- Use **Flash/Air models** (GLM-4.5-Air, MIMO-v2-Flash) for 90% of boilerplate and documentation
- Reserve **Standard/Thinking models** (DeepSeek-v3.2) for 10% of logic-heavy architecture

### Context Management
- Use `/compact` command (MiniMax M2.1 is excellent for this) to summarize long chat histories
- This saves on input tokens and maintains context for complex tasks

### Standardized Reviews
- Always use a different model for `/review` than the one used for `/build`
- This provides fresh perspective and reduces bias

## Troubleshooting

### Model Not Available
- Check OpenRouter API status at https://openrouter.ai/status
- Verify your API key is correctly set in environment variables
- Check if the model is listed in OpenRouter's available models

### Performance Issues
- Switch to lighter models (Air/Flash variants) for routine tasks
- Use `/compact` to reduce context length
- Consider splitting complex tasks into smaller subtasks

### Quality Issues
- Adjust temperature settings in `.opencode/opencode.json`
- Switch to more specialized personas for specific task types
- Use the Detective persona for troubleshooting model behavior

## Integration with Existing Skills

This multi-model approach complements the existing skills:
- Use **Testing Skill** with the Implementer persona
- Use **Backend Integration Skill** with the Architect persona
- Use **Code Style Skill** with the Refactorer persona
- Use **Debugging Skill** with the Detective persona

## See Also

- [AGENTS.md](../AGENTS.md) - Project context and multi-model strategy
- [LLM_PROVIDER_GUIDE.md](../../LLM_PROVIDER_GUIDE.md) - Detailed multi-model guidance
- `.opencode/opencode.json` - Model configuration
- OpenRouter Documentation - https://openrouter.ai/docs