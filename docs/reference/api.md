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

Webhook client for sending messages and CardBuilder for interactive cards.

::: feishu_webhook_bot.core.client

### feishu_webhook_bot.core.config

Configuration management with Pydantic validation.

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

### feishu_webhook_bot.core.circuit_breaker

Circuit breaker pattern for fault tolerance.

::: feishu_webhook_bot.core.circuit_breaker

### feishu_webhook_bot.core.message_queue

Async message queue with retry support.

::: feishu_webhook_bot.core.message_queue

### feishu_webhook_bot.core.message_tracker

Message delivery tracking and deduplication.

::: feishu_webhook_bot.core.message_tracker

### feishu_webhook_bot.core.config_watcher

Configuration hot-reload support.

::: feishu_webhook_bot.core.config_watcher

### feishu_webhook_bot.core.image_uploader

Feishu image upload utilities.

::: feishu_webhook_bot.core.image_uploader

### feishu_webhook_bot.core.provider

Provider abstraction layer for multi-platform support.

::: feishu_webhook_bot.core.provider

### feishu_webhook_bot.core.validation

Configuration validation utilities.

::: feishu_webhook_bot.core.validation

### feishu_webhook_bot.core.message_handler

Unified message handling interface for multi-platform support.

::: feishu_webhook_bot.core.message_handler

### feishu_webhook_bot.core.message_parsers

Platform-specific message parsers (Feishu, QQ/OneBot11).

::: feishu_webhook_bot.core.message_parsers

## Chat Controller

### feishu_webhook_bot.chat

Unified chat controller for multi-platform message routing.

::: feishu_webhook_bot.chat

### feishu_webhook_bot.chat.controller

ChatController, ChatConfig, and middleware system.

::: feishu_webhook_bot.chat.controller

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

### feishu_webhook_bot.plugins.config_registry

Plugin configuration registry.

::: feishu_webhook_bot.plugins.config_registry

### feishu_webhook_bot.plugins.config_schema

Plugin configuration schema definitions.

::: feishu_webhook_bot.plugins.config_schema

### feishu_webhook_bot.plugins.config_validator

Plugin configuration validation.

::: feishu_webhook_bot.plugins.config_validator

### feishu_webhook_bot.plugins.config_updater

Plugin configuration update utilities.

::: feishu_webhook_bot.plugins.config_updater

### feishu_webhook_bot.plugins.dependency_checker

Plugin dependency checking.

::: feishu_webhook_bot.plugins.dependency_checker

### feishu_webhook_bot.plugins.manifest

Plugin manifest handling.

::: feishu_webhook_bot.plugins.manifest

### feishu_webhook_bot.plugins.setup_wizard

Plugin setup wizard.

::: feishu_webhook_bot.plugins.setup_wizard

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

## Tasks

### feishu_webhook_bot.tasks

Task execution engine for automated tasks.

::: feishu_webhook_bot.tasks

### feishu_webhook_bot.tasks.executor

TaskExecutor for running task actions.

::: feishu_webhook_bot.tasks.executor

### feishu_webhook_bot.tasks.manager

TaskManager for task lifecycle management.

::: feishu_webhook_bot.tasks.manager

### feishu_webhook_bot.tasks.templates

Task template engine for reusable task definitions.

::: feishu_webhook_bot.tasks.templates

## Providers

### feishu_webhook_bot.providers

Message providers for multi-platform support.

::: feishu_webhook_bot.providers

### feishu_webhook_bot.providers.feishu

Feishu message provider implementation.

::: feishu_webhook_bot.providers.feishu

### feishu_webhook_bot.providers.qq_napcat

QQ/Napcat (OneBot11) message provider implementation.

::: feishu_webhook_bot.providers.qq_napcat

### feishu_webhook_bot.providers.base_http

Base HTTP provider for custom implementations.

::: feishu_webhook_bot.providers.base_http

## AI Components

### feishu_webhook_bot.ai

AI capabilities including agents, tools, and MCP support.

::: feishu_webhook_bot.ai

### feishu_webhook_bot.ai.agent

Main AIAgent class for AI-powered conversations.

::: feishu_webhook_bot.ai.agent

### feishu_webhook_bot.ai.config

AI configuration models (AIConfig, MCPConfig, etc.).

::: feishu_webhook_bot.ai.config

### feishu_webhook_bot.ai.conversation

Conversation management with multi-turn support.

::: feishu_webhook_bot.ai.conversation

### feishu_webhook_bot.ai.tools

Tool registry and built-in tools (web search, calculations, etc.).

::: feishu_webhook_bot.ai.tools

### feishu_webhook_bot.ai.mcp_client

MCP (Model Context Protocol) client implementation.

::: feishu_webhook_bot.ai.mcp_client

### feishu_webhook_bot.ai.multi_agent

Multi-agent orchestration (A2A) for complex tasks.

::: feishu_webhook_bot.ai.multi_agent

### feishu_webhook_bot.ai.retry

Retry logic and circuit breaker for AI operations.

::: feishu_webhook_bot.ai.retry

### feishu_webhook_bot.ai.task_integration

AI integration with task execution system.

::: feishu_webhook_bot.ai.task_integration

### feishu_webhook_bot.ai.exceptions

AI-specific exception classes.

::: feishu_webhook_bot.ai.exceptions

### feishu_webhook_bot.ai.commands

Chat command system for handling user commands (/help, /reset, /model, etc.).

::: feishu_webhook_bot.ai.commands

### feishu_webhook_bot.ai.conversation_store

Persistent conversation storage with SQLAlchemy.

::: feishu_webhook_bot.ai.conversation_store

## Providers (Extended)

### feishu_webhook_bot.providers.feishu_api

Feishu Open Platform API client for full bot functionality.

::: feishu_webhook_bot.providers.feishu_api

### feishu_webhook_bot.providers.qq_event_handler

QQ event handler for OneBot11 protocol event parsing.

::: feishu_webhook_bot.providers.qq_event_handler

## Authentication

### feishu_webhook_bot.auth

Authentication system for user management.

::: feishu_webhook_bot.auth

### feishu_webhook_bot.auth.service

AuthService for user registration and authentication.

::: feishu_webhook_bot.auth.service

### feishu_webhook_bot.auth.security

Password hashing, JWT token management.

::: feishu_webhook_bot.auth.security

### feishu_webhook_bot.auth.models

User models and database schema.

::: feishu_webhook_bot.auth.models

### feishu_webhook_bot.auth.database

Database operations for authentication.

::: feishu_webhook_bot.auth.database

### feishu_webhook_bot.auth.middleware

Authentication middleware for FastAPI and NiceGUI.

::: feishu_webhook_bot.auth.middleware

### feishu_webhook_bot.auth.routes

FastAPI authentication routes.

::: feishu_webhook_bot.auth.routes

### feishu_webhook_bot.auth.ui

NiceGUI authentication pages.

::: feishu_webhook_bot.auth.ui

## Configuration UI

### feishu_webhook_bot.config_ui

NiceGUI-based web interface for configuration and control.

::: feishu_webhook_bot.config_ui
