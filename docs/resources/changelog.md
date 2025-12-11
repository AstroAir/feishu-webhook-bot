# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Comprehensive documentation overhaul
- Multi-provider support (Feishu, QQ/Napcat)
- Advanced task execution system
- Message queue with batching and retry
- Message tracking and delivery status
- Circuit breaker for fault tolerance
- Configuration hot-reload
- AI multi-provider support (OpenAI, Anthropic, Google)
- MCP (Model Context Protocol) integration
- Multi-agent orchestration
- Authentication system with JWT
- Web UI for configuration management
- CLI improvements with plugin management

### Changed

- Improved plugin system with better lifecycle hooks
- Improved automation engine with more action types
- Better error handling and logging
- Updated dependencies

### Fixed

- Various bug fixes and stability improvements

## [0.1.0] - 2025-11-04

### Added

- Initial release
- Basic webhook client for Feishu
- Plugin system with hot-reload
- Task scheduler with APScheduler
- Automation engine with declarative rules
- Template system for messages
- Event server for receiving webhooks
- Configuration management with Pydantic
- Logging with structured output
- CLI for bot management
- Documentation with MkDocs

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2025-11-04 | Initial release |

## Upgrade Guide

### From 0.x to 1.0

When upgrading to version 1.0, note the following breaking changes:

1. **Configuration format changes**
   - `webhook_url` is now under `webhooks` list
   - AI configuration moved to `ai` section

2. **API changes**
   - `FeishuBot.send()` renamed to `FeishuBot.send_text()`
   - Plugin `setup()` renamed to `on_enable()`

3. **Dependency updates**
   - Minimum Python version is now 3.10
   - Updated to Pydantic v2

See [Migration Guide](migration.md) for detailed instructions.

## Contributing

See [Contributing Guide](contributing.md) for how to contribute to this project.

## Links

- [GitHub Repository](https://github.com/AstroAir/feishu-webhook-bot)
- [Issue Tracker](https://github.com/AstroAir/feishu-webhook-bot/issues)
- [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)
