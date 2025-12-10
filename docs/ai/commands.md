# AI Commands System

Complete guide to the chat command system for handling user commands like `/help`, `/reset`, `/model`, etc.

## Table of Contents

- [Overview](#overview)
- [Built-in Commands](#built-in-commands)
- [CommandHandler](#commandhandler)
- [CommandResult](#commandresult)
- [Custom Commands](#custom-commands)
- [Integration](#integration)
- [Best Practices](#best-practices)

## Overview

The command system (`feishu_webhook_bot.ai.commands`) provides a flexible way to handle slash commands in chat conversations. It integrates with the AI agent and conversation manager to provide user-facing controls.

### Key Features

- **Built-in commands**: `/help`, `/reset`, `/history`, `/model`, `/stats`, `/clear`
- **Custom command registration**: Add your own commands with decorators
- **Case-insensitive**: Commands work regardless of case
- **Argument parsing**: Automatic parsing of command arguments
- **Async support**: All command handlers are async

## Built-in Commands

| Command    | Description                              | Example         |
| ---------- | ---------------------------------------- | --------------- |
| `/help`    | Show available commands                  | `/help`         |
| `/reset`   | Reset conversation, clear context        | `/reset`        |
| `/history` | Show conversation history summary        | `/history`      |
| `/model`   | Switch AI model or show current          | `/model gpt-4o` |
| `/stats`   | Show usage statistics                    | `/stats`        |
| `/clear`   | Clear conversation context (keep record) | `/clear`        |

### Command Details

#### `/help`

Shows all available commands including built-in and custom commands.

```text
**可用命令:**

  `/help` - 显示帮助信息
  `/reset` - 重置当前对话，清除上下文
  `/history` - 显示对话历史摘要
  `/model` - 切换AI模型 (用法: /model gpt-4o)
  `/stats` - 显示使用统计
  `/clear` - 清除当前会话的上下文

**自定义命令:**
  `/weather`

**可用模型:** gpt-4o, gpt-4o-mini, claude-3-sonnet
```

#### `/reset`

Completely resets the conversation, clearing all message history and context.

```text
对话已重置，让我们重新开始吧！
```

#### `/history`

Shows a summary of the current conversation including message count, token usage, and duration.

```text
**对话统计:**
- 消息数: 24
- 输入Token: 3500
- 输出Token: 5200
- 总Token: 8700
- 会话时长: 15 分钟
```

#### `/model`

Without arguments, shows current model and available models:

```text
当前模型: gpt-4o
可用模型: gpt-4o, gpt-4o-mini, claude-3-sonnet

用法: /model <模型名>
```

With argument, switches to the specified model:

```text
/model claude-3-sonnet
已切换到模型: claude-3-sonnet
```

#### `/stats`

Shows usage statistics for the current user.

```text
**使用统计:**
- 总消息数: 150
- 输入Token: 25000
- 输出Token: 38000
- 总Token数: 63000
- 对话时长: 45.5 分钟
```

#### `/clear`

Clears message context but keeps the conversation record.

```text
已清除 24 条消息的上下文
```

## CommandHandler

The main class for handling commands.

### Basic Usage

```python
from feishu_webhook_bot.ai.commands import CommandHandler, CommandResult
from feishu_webhook_bot.ai import AIAgent
from feishu_webhook_bot.core.message_handler import IncomingMessage

# Create handler
handler = CommandHandler(
    ai_agent=ai_agent,
    conversation_manager=ai_agent.conversation_manager,
    command_prefix="/",
    available_models=["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"],
)

# Process a message
message = IncomingMessage(
    id="msg_123",
    platform="feishu",
    chat_type="private",
    chat_id="",
    sender_id="user_123",
    sender_name="Alice",
    content="/help",
)

is_cmd, result = await handler.process(message)
if is_cmd:
    print(result.response)
```

### Constructor Parameters

| Parameter              | Type                          | Description                                 |
| ---------------------- | ----------------------------- | ------------------------------------------- |
| `ai_agent`             | `AIAgent \| None`             | AI agent for model operations               |
| `conversation_manager` | `ConversationManager \| None` | Conversation manager for history operations |
| `command_prefix`       | `str`                         | Prefix for commands (default: `"/"`)        |
| `available_models`     | `list[str] \| None`           | Models available for `/model` command       |

### Methods

#### `process(message) -> tuple[bool, CommandResult | None]`

Process a message for commands.

```python
is_cmd, result = await handler.process(message)

if is_cmd:
    if result.success:
        await send_reply(message, result.response)
    else:
        await send_error(message, result.response)
else:
    # Not a command, process normally
    pass
```

#### `is_command(text) -> bool`

Check if text is a command.

```python
if handler.is_command("/help"):
    print("This is a command")
```

#### `parse_command(text) -> tuple[str, list[str]]`

Parse command text into command name and arguments.

```python
cmd, args = handler.parse_command("/model gpt-4o foo bar")
# cmd = "/model"
# args = ["gpt-4o", "foo", "bar"]
```

#### `register(name) -> Callable`

Decorator to register a custom command.

```python
@handler.register("/weather")
async def weather_cmd(handler, message, args):
    city = args[0] if args else "Beijing"
    return CommandResult(True, f"Weather for {city}: Sunny, 25°C")
```

#### `unregister(name) -> bool`

Unregister a custom command.

```python
success = handler.unregister("/weather")
```

## CommandResult

Data class for command execution results.

### Attributes

| Attribute         | Type           | Description                                          |
| ----------------- | -------------- | ---------------------------------------------------- |
| `success`         | `bool`         | Whether the command executed successfully            |
| `response`        | `str`          | Response text to send back to the user               |
| `should_continue` | `bool`         | Whether to continue with AI processing after command |
| `data`            | `dict \| None` | Additional data returned by the command handler      |

### Usage

```python
from feishu_webhook_bot.ai.commands import CommandResult

# Success result
result = CommandResult(
    success=True,
    response="Command executed successfully!",
)

# Failure result
result = CommandResult(
    success=False,
    response="Command failed: invalid argument",
)

# Result with additional data
result = CommandResult(
    success=True,
    response="Weather data retrieved",
    data={"temperature": 25, "condition": "sunny"},
)

# Result that allows AI to continue processing
result = CommandResult(
    success=True,
    response="Noted.",
    should_continue=True,  # AI will also process the message
)
```

## Custom Commands

### Registering Custom Commands

Use the `@handler.register()` decorator:

```python
@handler.register("/weather")
async def weather_cmd(handler, message, args):
    """Get weather for a city."""
    if not args:
        return CommandResult(False, "用法: /weather <城市名>")

    city = args[0]
    # Fetch weather data...
    weather = await get_weather(city)

    return CommandResult(
        success=True,
        response=f"**{city}天气:**\n温度: {weather['temp']}°C\n天气: {weather['condition']}",
    )
```

### Command Handler Signature

Custom command handlers receive:

1. `handler`: The CommandHandler instance
2. `message`: The IncomingMessage
3. `args`: List of command arguments

```python
async def my_command(
    handler: CommandHandler,
    message: IncomingMessage,
    args: list[str],
) -> CommandResult:
    # handler - access to AI agent, conversation manager
    # message - full message context
    # args - parsed arguments
    return CommandResult(success=True, response="Done!")
```

### Examples

#### Echo Command

```python
@handler.register("/echo")
async def echo_cmd(handler, message, args):
    if not args:
        return CommandResult(False, "用法: /echo <消息>")

    text = " ".join(args)
    return CommandResult(True, f"Echo: {text}")
```

#### User Info Command

```python
@handler.register("/whoami")
async def whoami_cmd(handler, message, args):
    info = f"""**用户信息:**
- 平台: {message.platform}
- 用户ID: {message.sender_id}
- 用户名: {message.sender_name}
- 聊天类型: {message.chat_type}
- 聊天ID: {message.chat_id or "N/A"}"""

    return CommandResult(True, info)
```

#### Admin Command

```python
ADMIN_IDS = {"admin_123", "admin_456"}

@handler.register("/admin")
async def admin_cmd(handler, message, args):
    if message.sender_id not in ADMIN_IDS:
        return CommandResult(False, "您没有管理员权限")

    if not args:
        return CommandResult(False, "用法: /admin <操作>")

    action = args[0]
    if action == "stats":
        stats = await handler.ai_agent.get_stats()
        return CommandResult(True, f"系统统计: {stats}")
    elif action == "clear_cache":
        await clear_cache()
        return CommandResult(True, "缓存已清除")
    else:
        return CommandResult(False, f"未知操作: {action}")
```

#### Async External API Command

```python
import httpx

@handler.register("/translate")
async def translate_cmd(handler, message, args):
    if len(args) < 2:
        return CommandResult(False, "用法: /translate <目标语言> <文本>")

    target_lang = args[0]
    text = " ".join(args[1:])

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.translation.service/translate",
                json={"text": text, "target": target_lang},
            )
            result = response.json()
            return CommandResult(True, f"翻译结果: {result['translation']}")
    except Exception as e:
        return CommandResult(False, f"翻译失败: {str(e)}")
```

### Unregistering Commands

```python
# Unregister a custom command
success = handler.unregister("/weather")

# Cannot unregister built-in commands
success = handler.unregister("/help")  # Returns False, logs warning
```

## Integration

### With ChatController

The recommended way to use commands is through `ChatController`:

```python
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig

controller = create_chat_controller(
    ai_agent=ai_agent,
    providers=providers,
    config=ChatConfig(command_prefix="/"),
    available_models=["gpt-4o", "claude-3-sonnet"],
)

# Commands are automatically handled
await controller.handle_incoming(message)
```

### Manual Integration

```python
from feishu_webhook_bot.ai.commands import CommandHandler

handler = CommandHandler(
    ai_agent=ai_agent,
    conversation_manager=ai_agent.conversation_manager,
)

async def process_message(message: IncomingMessage):
    # Check for commands first
    is_cmd, result = await handler.process(message)

    if is_cmd:
        await send_reply(message, result.response)
        return

    # Not a command, process with AI
    response = await ai_agent.chat(user_key, message.content)
    await send_reply(message, response)
```

### With Event Server

```python
@bot.on_event("im.message.receive_v1")
async def handle_message(event):
    message = parse_message(event)

    # Check for commands
    is_cmd, result = await command_handler.process(message)

    if is_cmd:
        await bot.send_text(result.response, chat_id=message.chat_id)
        return

    # Process with AI
    response = await ai_agent.chat(get_user_key(message), message.content)
    await bot.send_text(response, chat_id=message.chat_id)
```

## Best Practices

### 1. Provide Clear Help Messages

```python
@handler.register("/mycommand")
async def my_cmd(handler, message, args):
    if not args:
        return CommandResult(
            False,
            "**用法:** /mycommand <参数1> [参数2]\n\n"
            "**参数:**\n"
            "- 参数1: 必需，描述...\n"
            "- 参数2: 可选，描述...\n\n"
            "**示例:**\n"
            "- `/mycommand foo`\n"
            "- `/mycommand foo bar`"
        )
    # ...
```

### 2. Validate Arguments

```python
@handler.register("/setlimit")
async def setlimit_cmd(handler, message, args):
    if not args:
        return CommandResult(False, "用法: /setlimit <数字>")

    try:
        limit = int(args[0])
        if limit < 1 or limit > 100:
            return CommandResult(False, "限制必须在 1-100 之间")
    except ValueError:
        return CommandResult(False, "请输入有效的数字")

    # Process valid limit
    return CommandResult(True, f"限制已设置为 {limit}")
```

### 3. Handle Errors Gracefully

```python
@handler.register("/fetch")
async def fetch_cmd(handler, message, args):
    try:
        result = await external_api_call()
        return CommandResult(True, f"结果: {result}")
    except ConnectionError:
        return CommandResult(False, "无法连接到服务器，请稍后重试")
    except TimeoutError:
        return CommandResult(False, "请求超时，请稍后重试")
    except Exception as e:
        logger.error("Fetch command error: %s", e)
        return CommandResult(False, "发生未知错误，请联系管理员")
```

### 4. Use Consistent Response Formatting

```python
# Use markdown for rich formatting
response = """**操作成功!**

- 项目1: 完成
- 项目2: 完成
- 项目3: 完成

*提示: 使用 /help 查看更多命令*"""

return CommandResult(True, response)
```

### 5. Log Command Usage

```python
@handler.register("/important")
async def important_cmd(handler, message, args):
    logger.info(
        "Important command executed by %s: args=%s",
        message.sender_id,
        args,
    )
    # ...
```

## See Also

- [Chat Controller Guide](../guides/chat-controller-guide.md) - Unified chat handling
- [AI Multi-Provider](multi-provider.md) - AI agent configuration
- [AI Enhancements](enhancements.md) - Advanced AI features
- [Conversation Store](conversation-store.md) - Persistent conversations
