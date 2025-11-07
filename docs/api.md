# API Reference

Complete API documentation for the Feishu Webhook Bot framework.

## Core Modules

### feishu_webhook_bot

Main package exports.

::: feishu_webhook_bot

## Core Components

### feishu_webhook_bot.core

Core functionality including webhook client, configuration, and logging.

::: feishu_webhook_bot.core

### feishu_webhook_bot.core.client

Webhook client for sending messages.

::: feishu_webhook_bot.core.client

### feishu_webhook_bot.core.config

Configuration management with Pydantic.

::: feishu_webhook_bot.core.config

### feishu_webhook_bot.core.logger

Logging utilities with Rich formatting.

::: feishu_webhook_bot.core.logger

### feishu_webhook_bot.core.event_server

FastAPI event server for receiving Feishu webhooks.

::: feishu_webhook_bot.core.event_server

### feishu_webhook_bot.core.templates

Message template registry and rendering.

::: feishu_webhook_bot.core.templates

## Bot & Orchestration

### feishu_webhook_bot.bot

Main bot class that orchestrates all components.

::: feishu_webhook_bot.bot

### feishu_webhook_bot.cli

Command-line interface.

::: feishu_webhook_bot.cli

## Plugins

### feishu_webhook_bot.plugins

Plugin system with base class and manager.

::: feishu_webhook_bot.plugins

### feishu_webhook_bot.plugins.base

Base plugin class with lifecycle hooks.

::: feishu_webhook_bot.plugins.base

### feishu_webhook_bot.plugins.manager

Plugin manager with hot-reload support.

::: feishu_webhook_bot.plugins.manager

## Scheduling

### feishu_webhook_bot.scheduler

Task scheduling with APScheduler.

::: feishu_webhook_bot.scheduler

### feishu_webhook_bot.scheduler.scheduler

TaskScheduler class and job decorator.

::: feishu_webhook_bot.scheduler.scheduler

## Automation

### feishu_webhook_bot.automation

Automation engine for declarative workflows.

::: feishu_webhook_bot.automation

### feishu_webhook_bot.automation.engine

AutomationEngine for executing workflows.

::: feishu_webhook_bot.automation.engine

## Configuration UI

### feishu_webhook_bot.config_ui

NiceGUI-based web interface for configuration and control.

::: feishu_webhook_bot.config_ui
