"""Example demonstrating AI-powered automated tasks.

This example shows how to:
1. Create tasks that use AI for intelligent processing
2. Use AI for sentiment analysis before taking action
3. Generate content using AI in scheduled tasks
4. Build multi-step workflows with AI

Prerequisites:
- Install pydantic-ai: pip install pydantic-ai
- Set OPENAI_API_KEY environment variable
"""

import asyncio
import os
from datetime import datetime

from feishu_webhook_bot.ai import AIAgent, AIConfig
from feishu_webhook_bot.core.config import (
    AutomationScheduleConfig,
    TaskActionConfig,
    TaskDefinitionConfig,
    TaskErrorHandlingConfig,
)
from feishu_webhook_bot.core.logger import get_logger
from feishu_webhook_bot.tasks.executor import TaskExecutor

logger = get_logger("ai_tasks_example")


async def example_1_daily_summary():
    """Example 1: Daily summary task using AI."""
    logger.info("\n=== Example 1: Daily Summary Task ===\n")

    # Create AI agent
    ai_config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a helpful assistant that creates concise daily summaries.",
        temperature=0.7,
        max_tokens=500,
    )

    agent = AIAgent(ai_config)
    agent.start()

    try:
        # Define task with AI action
        task = TaskDefinitionConfig(
            name="daily_summary",
            description="Generate daily summary using AI",
            enabled=True,
            schedule=AutomationScheduleConfig(
                mode="cron",
                arguments={"hour": 18, "minute": 0},  # 6 PM daily
            ),
            conditions=[],
            actions=[
                # AI action to generate summary
                TaskActionConfig(
                    type="ai_query",
                    ai_prompt=(
                        "Generate a brief daily summary for ${date}. "
                        "Include: 1) Key accomplishments, 2) Pending items, "
                        "3) Tomorrow's priorities. "
                        "Keep it under 200 words."
                    ),
                    ai_user_id="daily_summary_bot",
                    ai_temperature=0.7,
                    ai_save_response_as="summary",
                ),
                # Send the summary
                TaskActionConfig(
                    type="send_message",
                    message="📊 Daily Summary:\n\n${summary}",
                    webhooks=["default"],
                ),
            ],
            error_handling=TaskErrorHandlingConfig(
                retry_on_failure=True,
                max_retries=3,
                on_failure_action="log",
            ),
        )

        # Execute task
        context = {"date": datetime.now().strftime("%Y-%m-%d")}
        executor = TaskExecutor(task, context, ai_agent=agent)
        result = executor.execute()

        logger.info("Task result: %s", result)
        logger.info("Generated summary: %s", context.get("summary", "N/A"))

    finally:
        await agent.stop()


async def example_2_sentiment_analysis():
    """Example 2: Sentiment analysis before action."""
    logger.info("\n=== Example 2: Sentiment Analysis Task ===\n")

    # Create AI agent
    ai_config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt=(
            "You are a sentiment analysis expert. "
            "Analyze text and respond with only: POSITIVE, NEGATIVE, or NEUTRAL."
        ),
        temperature=0.3,  # Lower temperature for more consistent classification
        max_tokens=10,
    )

    agent = AIAgent(ai_config)
    agent.start()

    try:
        # Define task with sentiment analysis
        task = TaskDefinitionConfig(
            name="sentiment_based_action",
            description="Analyze sentiment and take appropriate action",
            enabled=True,
            schedule=AutomationScheduleConfig(
                mode="interval",
                arguments={"hours": 1},
            ),
            conditions=[],
            actions=[
                # AI action for sentiment analysis
                TaskActionConfig(
                    type="ai_query",
                    ai_prompt=(
                        "Analyze the sentiment of this feedback: '${feedback}'. "
                        "Respond with only: POSITIVE, NEGATIVE, or NEUTRAL."
                    ),
                    ai_user_id="sentiment_analyzer",
                    ai_temperature=0.3,
                    ai_save_response_as="sentiment",
                ),
                # Python code to check sentiment and take action
                TaskActionConfig(
                    type="python_code",
                    code="""
sentiment = context.get('sentiment', '').strip().upper()
logger.info(f"Detected sentiment: {sentiment}")

if 'NEGATIVE' in sentiment:
    context['action_message'] = "⚠️ Negative feedback detected! Immediate attention required."
    context['priority'] = 'HIGH'
elif 'POSITIVE' in sentiment:
    context['action_message'] = "✅ Positive feedback received! Great job team!"
    context['priority'] = 'LOW'
else:
    context['action_message'] = "ℹ️ Neutral feedback noted."
    context['priority'] = 'MEDIUM'
""",
                ),
                # Send notification based on sentiment
                TaskActionConfig(
                    type="send_message",
                    message="${action_message}\n\nFeedback: ${feedback}\nPriority: ${priority}",
                    webhooks=["default"],
                ),
            ],
            error_handling=TaskErrorHandlingConfig(
                retry_on_failure=True,
                max_retries=2,
                on_failure_action="log",
            ),
        )

        # Execute task with sample feedback
        context = {"feedback": "The new feature is terrible and keeps crashing. Very disappointed!"}
        executor = TaskExecutor(task, context, ai_agent=agent)
        result = executor.execute()

        logger.info("Task result: %s", result)
        logger.info("Sentiment: %s", context.get("sentiment", "N/A"))
        logger.info("Action: %s", context.get("action_message", "N/A"))

    finally:
        await agent.stop()


async def example_3_content_generation():
    """Example 3: AI content generation task."""
    logger.info("\n=== Example 3: Content Generation Task ===\n")

    # Create AI agent
    ai_config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a creative content writer specializing in social media posts.",
        temperature=0.9,  # Higher temperature for more creative output
        max_tokens=300,
    )

    agent = AIAgent(ai_config)
    agent.start()

    try:
        # Define content generation task
        task = TaskDefinitionConfig(
            name="generate_social_post",
            description="Generate social media content using AI",
            enabled=True,
            schedule=AutomationScheduleConfig(
                mode="cron",
                arguments={"hour": 9, "minute": 0},  # 9 AM daily
            ),
            conditions=[],
            actions=[
                # AI action to generate content
                TaskActionConfig(
                    type="ai_chat",
                    ai_prompt=(
                        "Create an engaging social media post about ${topic}. "
                        "Include: 1) A catchy headline, 2) 2-3 key points, 3) A call-to-action. "
                        "Use emojis appropriately. Keep it under 280 characters."
                    ),
                    ai_user_id="content_generator",
                    ai_temperature=0.9,
                    ai_save_response_as="social_post",
                ),
                # Send the generated content
                TaskActionConfig(
                    type="send_message",
                    message="📱 Generated Social Media Post:\n\n${social_post}\n\n#${topic}",
                    webhooks=["default"],
                ),
            ],
            error_handling=TaskErrorHandlingConfig(
                retry_on_failure=True,
                max_retries=3,
                on_failure_action="log",
            ),
        )

        # Execute task
        context = {"topic": "AI-powered automation"}
        executor = TaskExecutor(task, context, ai_agent=agent)
        result = executor.execute()

        logger.info("Task result: %s", result)
        logger.info("Generated post: %s", context.get("social_post", "N/A"))

    finally:
        await agent.stop()


async def example_4_multi_step_workflow():
    """Example 4: Multi-step AI workflow."""
    logger.info("\n=== Example 4: Multi-Step AI Workflow ===\n")

    # Create AI agent
    ai_config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a helpful AI assistant for data analysis and reporting.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=True,
        web_search_enabled=True,
    )

    agent = AIAgent(ai_config)
    agent.start()

    try:
        # Define multi-step workflow
        task = TaskDefinitionConfig(
            name="multi_step_analysis",
            description="Multi-step AI workflow: research, analyze, report",
            enabled=True,
            schedule=AutomationScheduleConfig(
                mode="interval",
                arguments={"hours": 6},
            ),
            conditions=[],
            actions=[
                # Step 1: Research using AI with web search
                TaskActionConfig(
                    type="ai_query",
                    ai_prompt="Research the latest trends in ${industry}. Provide 3 key insights.",
                    ai_user_id="researcher",
                    ai_save_response_as="research_results",
                ),
                # Step 2: Analyze the research
                TaskActionConfig(
                    type="ai_query",
                    ai_prompt=(
                        "Based on this research: ${research_results}\n\n"
                        "Provide a brief analysis of: 1) Opportunities, "
                        "2) Challenges, 3) Recommendations."
                    ),
                    ai_user_id="analyst",
                    ai_save_response_as="analysis",
                ),
                # Step 3: Generate executive summary
                TaskActionConfig(
                    type="ai_query",
                    ai_prompt=(
                        "Create an executive summary based on:\n"
                        "Research: ${research_results}\n"
                        "Analysis: ${analysis}\n\n"
                        "Keep it concise and actionable (max 150 words)."
                    ),
                    ai_user_id="summarizer",
                    ai_temperature=0.5,
                    ai_save_response_as="executive_summary",
                ),
                # Step 4: Send the complete report
                TaskActionConfig(
                    type="send_message",
                    message=(
                        "📊 ${industry} Industry Report\n\n"
                        "🔍 Research:\n${research_results}\n\n"
                        "📈 Analysis:\n${analysis}\n\n"
                        "📋 Executive Summary:\n${executive_summary}"
                    ),
                    webhooks=["default"],
                ),
            ],
            error_handling=TaskErrorHandlingConfig(
                retry_on_failure=True,
                max_retries=2,
                on_failure_action="log",
            ),
        )

        # Execute task
        context = {"industry": "AI and Machine Learning"}
        executor = TaskExecutor(task, context, ai_agent=agent)
        result = executor.execute()

        logger.info("Task result: %s", result)
        logger.info("\nWorkflow outputs:")
        logger.info("Research: %s", context.get("research_results", "N/A")[:200] + "...")
        logger.info("Analysis: %s", context.get("analysis", "N/A")[:200] + "...")
        logger.info("Summary: %s", context.get("executive_summary", "N/A"))

    finally:
        await agent.stop()


async def main():
    """Run all examples."""
    logger.info("=== AI-Powered Tasks Examples ===\n")

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not set. Please set it to run these examples.")
        logger.info("\nExample: export OPENAI_API_KEY='your-api-key'")
        return

    # Run examples
    await example_1_daily_summary()
    await example_2_sentiment_analysis()
    await example_3_content_generation()
    await example_4_multi_step_workflow()

    logger.info("\n=== All examples completed ===")


if __name__ == "__main__":
    asyncio.run(main())
