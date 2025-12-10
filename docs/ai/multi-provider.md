# AI Multi-Provider and Task Integration Guide

This guide covers the enhanced AI capabilities in the Feishu Webhook Bot framework, including support for multiple AI model providers and AI-powered automated tasks.

## Table of Contents

- [Multiple AI Model Providers](#multiple-ai-model-providers)
- [AI-Powered Automated Tasks](#ai-powered-automated-tasks)
- [Configuration Reference](#configuration-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Multiple AI Model Providers

The framework now supports multiple AI model providers through pydantic-ai, giving you flexibility in choosing the best model for your use case.

### Supported Providers

| Provider | Models | API Key Env Var | Notes |
|----------|--------|----------------|-------|
| **OpenAI** | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | `OPENAI_API_KEY` | Best for general-purpose tasks |
| **Anthropic** | claude-3-5-sonnet, claude-3-opus | `ANTHROPIC_API_KEY` | Excellent for analysis and reasoning |
| **Google** | gemini-1.5-pro, gemini-1.5-flash | `GOOGLE_API_KEY` | Fast and cost-effective |
| **Groq** | llama-3.1-70b, mixtral-8x7b | `GROQ_API_KEY` | Ultra-fast inference |
| **Cohere** | command-r-plus, command-r | `COHERE_API_KEY` | Enterprise-focused |
| **Ollama** | llama3.1, mistral, etc. | N/A (local) | Run models locally |

### Basic Configuration

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"  # Format: provider:model-name
  api_key: ${OPENAI_API_KEY}
  
  # Provider-specific configuration
  provider_config:
    provider: "openai"  # Auto-detected if not specified
    timeout: 60.0
    max_retries: 2
    base_url: null  # Custom API endpoint (e.g., for Ollama)
```

### Provider-Specific Examples

#### OpenAI

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: ${OPENAI_API_KEY}
  provider_config:
    organization_id: ${OPENAI_ORG_ID}  # Optional
    timeout: 60.0
```

#### Anthropic (Claude)

```yaml
ai:
  enabled: true
  model: "anthropic:claude-3-5-sonnet-20241022"
  api_key: ${ANTHROPIC_API_KEY}
  provider_config:
    timeout: 90.0  # Claude can take longer for complex tasks
```

#### Google Gemini

```yaml
ai:
  enabled: true
  model: "google:gemini-1.5-pro"
  api_key: ${GOOGLE_API_KEY}
  provider_config:
    timeout: 60.0
```

#### Groq (Fast Inference)

```yaml
ai:
  enabled: true
  model: "groq:llama-3.1-70b-versatile"
  api_key: ${GROQ_API_KEY}
  provider_config:
    timeout: 30.0  # Groq is very fast
```

#### Cohere

```yaml
ai:
  enabled: true
  model: "cohere:command-r-plus"
  api_key: ${COHERE_API_KEY}
  provider_config:
    timeout: 60.0
```

#### Ollama (Local Models)

```yaml
ai:
  enabled: true
  model: "ollama:llama3.1"
  provider_config:
    base_url: "http://localhost:11434/v1"
    timeout: 120.0  # Local inference can be slower
```

### Fallback Models

Configure fallback models for improved reliability:

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"  # Primary model
  fallback_models:
    - "anthropic:claude-3-5-sonnet-20241022"  # First fallback
    - "groq:llama-3.1-70b-versatile"  # Second fallback
```

If the primary model fails, the system will automatically try the fallback models in order.

## AI-Powered Automated Tasks

Integrate AI capabilities directly into your automated tasks for intelligent processing.

### AI Action Types

Two new action types are available for tasks:

1. **`ai_chat`**: For conversational AI interactions with context
2. **`ai_query`**: For one-off AI queries without conversation history

### Basic AI Task Example

```yaml
tasks:
  - name: "daily_summary"
    description: "Generate daily summary using AI"
    enabled: true
    
    schedule:
      mode: "cron"
      arguments:
        hour: 18
        minute: 0
    
    actions:
      - type: "ai_query"
        ai_prompt: "Generate a brief daily summary for ${date}."
        ai_user_id: "summary_bot"
        ai_save_response_as: "summary"
      
      - type: "send_message"
        message: "📊 Daily Summary:\n\n${summary}"
        webhooks: ["default"]
```

### AI Action Configuration

| Field | Type | Description |
|-------|------|-------------|
| `ai_prompt` | string | The prompt to send to the AI (supports ${variable} substitution) |
| `ai_user_id` | string | User ID for conversation context (optional, defaults to "task_system") |
| `ai_system_prompt` | string | Override system prompt for this action (optional) |
| `ai_temperature` | float | Override temperature (0.0-2.0, optional) |
| `ai_max_tokens` | int | Override max tokens (optional) |
| `ai_save_response_as` | string | Save AI response to context with this key (optional) |
| `ai_structured_output` | bool | Use structured output validation (default: false) |

### Use Cases

#### 1. Sentiment Analysis

```yaml
actions:
  - type: "ai_query"
    ai_prompt: |
      Analyze the sentiment of this feedback: "${feedback}"
      Respond with only: POSITIVE, NEGATIVE, or NEUTRAL
    ai_user_id: "sentiment_analyzer"
    ai_temperature: 0.3
    ai_save_response_as: "sentiment"
  
  - type: "python_code"
    code: |
      sentiment = context.get('sentiment', '').strip().upper()
      if 'NEGATIVE' in sentiment:
          context['priority'] = 'HIGH'
      elif 'POSITIVE' in sentiment:
          context['priority'] = 'LOW'
      else:
          context['priority'] = 'MEDIUM'
```

#### 2. Content Generation

```yaml
actions:
  - type: "ai_chat"
    ai_prompt: |
      Create an engaging social media post about ${topic}.
      Include a catchy headline, 2-3 key points, and a call-to-action.
      Use emojis. Keep under 280 characters.
    ai_user_id: "content_creator"
    ai_temperature: 0.9
    ai_save_response_as: "social_post"
```

#### 3. Multi-Step Workflow

```yaml
actions:
  # Step 1: Research
  - type: "ai_query"
    ai_prompt: "Research latest trends in ${industry}. Provide 3 key insights."
    ai_user_id: "researcher"
    ai_save_response_as: "research"
  
  # Step 2: Analyze
  - type: "ai_query"
    ai_prompt: |
      Based on this research: ${research}
      Provide analysis of opportunities, challenges, and recommendations.
    ai_user_id: "analyst"
    ai_save_response_as: "analysis"
  
  # Step 3: Summarize
  - type: "ai_query"
    ai_prompt: |
      Create an executive summary based on:
      Research: ${research}
      Analysis: ${analysis}
    ai_user_id: "summarizer"
    ai_save_response_as: "summary"
```

## Configuration Reference

### ModelProviderConfig

```yaml
provider_config:
  provider: "openai"  # Provider name (auto-detected if not specified)
  base_url: null  # Custom API endpoint
  api_version: null  # API version (provider-specific)
  organization_id: null  # Organization ID (for OpenAI)
  timeout: 60.0  # Request timeout in seconds
  max_retries: 2  # Maximum retries for failed requests
  additional_headers: {}  # Additional HTTP headers
  additional_params: {}  # Additional model parameters
```

### AIConfig

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: ${OPENAI_API_KEY}
  provider_config: {}  # ModelProviderConfig
  fallback_models: []  # List of fallback models
  system_prompt: "You are a helpful AI assistant."
  temperature: 0.7
  max_tokens: 1000
  max_conversation_turns: 10
  conversation_timeout_minutes: 30
  tools_enabled: true
  web_search_enabled: true
  web_search_max_results: 5
  structured_output_enabled: false
  output_validators_enabled: false
  retry_on_validation_error: true
  max_retries: 3
```

## Examples

See the `examples/` directory for complete working examples:

- `multi_provider_ai_example.py` - Using different AI providers
- `ai_powered_tasks_example.py` - AI-powered automated tasks
- `ai_tasks_config.yaml` - YAML configuration examples

## Troubleshooting

### API Key Issues

**Problem**: "API key not found" error

**Solution**: Set the appropriate environment variable:

```bash
# OpenAI
export OPENAI_API_KEY='your-key'

# Anthropic
export ANTHROPIC_API_KEY='your-key'

# Google
export GOOGLE_API_KEY='your-key'

# Groq
export GROQ_API_KEY='your-key'

# Cohere
export COHERE_API_KEY='your-key'
```

### Provider-Specific Issues

#### Ollama Connection Error

**Problem**: Cannot connect to Ollama

**Solution**:

1. Ensure Ollama is running: `ollama serve`
2. Verify the base URL: `http://localhost:11434/v1`
3. Check that the model is installed: `ollama list`

#### Rate Limiting

**Problem**: "Rate limit exceeded" error

**Solution**:

1. Use fallback models for redundancy
2. Increase retry delays in provider_config
3. Consider using Groq for faster, higher-rate-limit inference

#### Timeout Errors

**Problem**: Requests timing out

**Solution**:

1. Increase timeout in provider_config
2. Use faster models (e.g., Groq, Gemini Flash)
3. Reduce max_tokens to get faster responses

### AI Task Issues

**Problem**: AI action fails in task

**Solution**:

1. Check that AI is enabled in bot configuration
2. Verify AI agent is passed to TaskManager
3. Check logs for specific error messages
4. Ensure ai_prompt is properly formatted

**Problem**: Variables not substituted in ai_prompt

**Solution**:

1. Use `${variable}` syntax (not `{variable}`)
2. Ensure variable exists in task context
3. Check for typos in variable names

## Best Practices

1. **Choose the Right Provider**:
   - OpenAI: General-purpose, reliable
   - Anthropic: Complex reasoning, analysis
   - Google: Fast, cost-effective
   - Groq: Ultra-fast inference
   - Ollama: Privacy, no API costs

2. **Use Fallback Models**:
   - Always configure at least one fallback
   - Mix providers for redundancy
   - Order by preference and cost

3. **Optimize Prompts**:
   - Be specific and clear
   - Use lower temperature (0.3-0.5) for consistent outputs
   - Use higher temperature (0.8-1.0) for creative tasks

4. **Handle Errors Gracefully**:
   - Configure retry logic in tasks
   - Use error_handling in task definitions
   - Log AI responses for debugging

5. **Monitor Costs**:
   - Use cheaper models for simple tasks
   - Set max_tokens appropriately
   - Consider Ollama for high-volume use cases

## Next Steps

- Review [AI Enhancements](enhancements.md) for advanced features
- Check [MCP Integration](mcp-integration.md) for MCP support
- See the examples directory in the repository for complete working examples
