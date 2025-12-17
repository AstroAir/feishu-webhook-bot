#!/usr/bin/env python3
"""Tool Registry Example.

This example demonstrates the tool registry system:
- Registering custom tools
- Tool metadata and schemas
- Tool execution
- Built-in tools (web search, etc.)
- Tool validation
- Async tool support
- Tool categories and organization

The tool registry enables AI agents to use external functions and APIs.
"""

import asyncio
from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)

# Check for AI dependencies
try:
    from feishu_webhook_bot.ai import ToolRegistry

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("AI dependencies not available. Install with: pip install pydantic-ai")


# =============================================================================
# Demo 1: Basic Tool Registration
# =============================================================================
def demo_basic_registration() -> None:
    """Demonstrate basic tool registration."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Tool Registration")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Create tool registry
    registry = ToolRegistry()

    # Define a simple tool
    def get_current_time() -> str:
        """Get the current time."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Register the tool
    registry.register(
        name="get_current_time",
        func=get_current_time,
        description="Get the current date and time",
    )

    print("Registered tool: get_current_time")
    print(f"Total tools: {len(registry)}")

    # List registered tools
    print("\nRegistered tools:")
    for tool_name in registry.list_tools():
        print(f"  - {tool_name}")


# =============================================================================
# Demo 2: Tool with Parameters
# =============================================================================
def demo_tool_with_parameters() -> None:
    """Demonstrate tools with parameters."""
    print("\n" + "=" * 60)
    print("Demo 2: Tool with Parameters")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Tool with typed parameters
    def calculate(operation: str, a: float, b: float) -> float:
        """Perform a mathematical calculation.

        Args:
            operation: The operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number

        Returns:
            Result of the calculation
        """
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else float("inf"),
        }
        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")
        return operations[operation](a, b)

    registry.register(
        name="calculate",
        func=calculate,
        description="Perform mathematical calculations",
    )

    print("Registered tool: calculate")

    # Execute the tool
    print("\nExecuting tool:")
    result = calculate("add", 10, 5)
    print(f"  calculate('add', 10, 5) = {result}")

    result = calculate("multiply", 7, 3)
    print(f"  calculate('multiply', 7, 3) = {result}")


# =============================================================================
# Demo 3: Async Tool Support
# =============================================================================
async def demo_async_tools() -> None:
    """Demonstrate async tool support."""
    print("\n" + "=" * 60)
    print("Demo 3: Async Tool Support")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Async tool
    async def fetch_data(url: str) -> dict[str, Any]:
        """Fetch data from a URL (simulated).

        Args:
            url: The URL to fetch data from

        Returns:
            Fetched data as dictionary
        """
        # Simulate async HTTP request
        await asyncio.sleep(0.1)
        return {
            "url": url,
            "status": 200,
            "data": {"message": "Simulated response"},
        }

    registry.register(
        name="fetch_data",
        func=fetch_data,
        description="Fetch data from a URL",
    )

    print("Registered async tool: fetch_data")

    # Execute async tool
    print("\nExecuting async tool:")
    result = await fetch_data("https://api.example.com/data")
    print(f"  Result: {result}")


# =============================================================================
# Demo 4: Tool Categories
# =============================================================================
def demo_tool_categories() -> None:
    """Demonstrate organizing tools by category."""
    print("\n" + "=" * 60)
    print("Demo 4: Tool Categories")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Math tools
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    # String tools
    def uppercase(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()

    def reverse(text: str) -> str:
        """Reverse a string."""
        return text[::-1]

    # Register with categories (using naming convention)
    registry.register("math.add", add, "Add two numbers")
    registry.register("math.multiply", multiply, "Multiply two numbers")
    registry.register("string.uppercase", uppercase, "Convert to uppercase")
    registry.register("string.reverse", reverse, "Reverse a string")

    print("Registered tools by category:")

    # Group by category
    tools = registry.list_tools()
    categories: dict[str, list[str]] = {}
    for tool in tools:
        if "." in tool:
            category, name = tool.split(".", 1)
        else:
            category, name = "general", tool
        categories.setdefault(category, []).append(name)

    for category, tool_names in categories.items():
        print(f"\n  {category}:")
        for name in tool_names:
            print(f"    - {name}")


# =============================================================================
# Demo 5: Tool Validation
# =============================================================================
def demo_tool_validation() -> None:
    """Demonstrate tool validation."""
    print("\n" + "=" * 60)
    print("Demo 5: Tool Validation")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Tool with validation
    def send_email(to: str, subject: str, body: str) -> bool:
        """Send an email (simulated).

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            True if sent successfully
        """
        # Validate email format
        if "@" not in to:
            raise ValueError(f"Invalid email address: {to}")
        if not subject:
            raise ValueError("Subject cannot be empty")
        if not body:
            raise ValueError("Body cannot be empty")

        print(f"    Sending email to: {to}")
        print(f"    Subject: {subject}")
        return True

    registry.register(
        name="send_email",
        func=send_email,
        description="Send an email",
    )

    print("Testing tool validation:")

    # Valid call
    print("\n  Valid call:")
    try:
        result = send_email("user@example.com", "Hello", "Test message")
        print(f"    Result: {result}")
    except ValueError as e:
        print(f"    Error: {e}")

    # Invalid email
    print("\n  Invalid email:")
    try:
        send_email("invalid_email", "Hello", "Test")
    except ValueError as e:
        print(f"    Error: {e}")

    # Empty subject
    print("\n  Empty subject:")
    try:
        send_email("user@example.com", "", "Test")
    except ValueError as e:
        print(f"    Error: {e}")


# =============================================================================
# Demo 6: Built-in Web Search Tool
# =============================================================================
def demo_web_search_tool() -> None:
    """Demonstrate built-in web search tool."""
    print("\n" + "=" * 60)
    print("Demo 6: Built-in Web Search Tool")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("The framework includes a built-in web search tool:")
    print("""
    Web Search Tool:
    - Uses DuckDuckGo for privacy-friendly search
    - Caches results to reduce API calls
    - Configurable result count
    - Returns structured search results

    Usage in AIConfig:
        config = AIConfig(
            web_search_enabled=True,
            web_search_cache_ttl=3600,  # 1 hour cache
        )

    The AI agent can then use web search automatically:
        "Search the web for Python async best practices"
    """)


# =============================================================================
# Demo 7: Tool Execution Context
# =============================================================================
def demo_execution_context() -> None:
    """Demonstrate tool execution with context."""
    print("\n" + "=" * 60)
    print("Demo 7: Tool Execution Context")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Tool that uses context
    def get_user_info(user_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get user information.

        Args:
            user_id: User ID to look up
            context: Optional execution context

        Returns:
            User information dictionary
        """
        # Use context for additional info
        session_id = context.get("session_id", "unknown") if context else "unknown"
        caller = context.get("caller", "unknown") if context else "unknown"

        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "session_id": session_id,
            "requested_by": caller,
        }

    registry.register(
        name="get_user_info",
        func=get_user_info,
        description="Get user information",
    )

    print("Tool with execution context:")

    # Execute with context
    context = {
        "session_id": "sess_12345",
        "caller": "ai_agent",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    result = get_user_info("user_789", context=context)
    print("\nResult with context:")
    for key, value in result.items():
        print(f"  {key}: {value}")


# =============================================================================
# Demo 8: Tool Error Handling
# =============================================================================
def demo_error_handling() -> None:
    """Demonstrate tool error handling."""
    print("\n" + "=" * 60)
    print("Demo 8: Tool Error Handling")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    registry = ToolRegistry()

    # Tool that may raise errors
    def divide(a: float, b: float) -> float:
        """Divide two numbers.

        Args:
            a: Dividend
            b: Divisor

        Returns:
            Result of division

        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b

    registry.register(
        name="divide",
        func=divide,
        description="Divide two numbers",
    )

    print("Error handling patterns:")

    # Safe execution wrapper
    def safe_execute(func, *args, **kwargs) -> tuple[Any, str | None]:
        """Execute a tool safely, catching errors."""
        try:
            result = func(*args, **kwargs)
            return result, None
        except Exception as e:
            return None, str(e)

    # Test cases
    test_cases = [
        (10, 2),
        (10, 0),
        (15, 3),
    ]

    print("\nSafe execution results:")
    for a, b in test_cases:
        result, error = safe_execute(divide, a, b)
        if error:
            print(f"  divide({a}, {b}) -> Error: {error}")
        else:
            print(f"  divide({a}, {b}) -> {result}")


# =============================================================================
# Demo 9: Tool Metadata
# =============================================================================
def demo_tool_metadata() -> None:
    """Demonstrate tool metadata and schemas."""
    print("\n" + "=" * 60)
    print("Demo 9: Tool Metadata")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("Tool metadata is automatically extracted from function signatures:")
    print("""
    def search_products(
        query: str,
        category: str | None = None,
        max_results: int = 10,
        sort_by: str = "relevance",
    ) -> list[dict]:
        '''Search for products in the catalog.

        Args:
            query: Search query string
            category: Optional category filter
            max_results: Maximum number of results (default: 10)
            sort_by: Sort order (relevance, price, rating)

        Returns:
            List of matching products
        '''
        ...

    Extracted metadata:
    - Name: search_products
    - Description: Search for products in the catalog
    - Parameters:
        - query (str, required): Search query string
        - category (str, optional): Optional category filter
        - max_results (int, default=10): Maximum number of results
        - sort_by (str, default="relevance"): Sort order
    - Return type: list[dict]
    """)


# =============================================================================
# Demo 10: Real-World Tool Registry
# =============================================================================
def demo_real_world_registry() -> None:
    """Demonstrate a real-world tool registry setup."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Tool Registry")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    class BusinessToolRegistry:
        """Business-focused tool registry."""

        def __init__(self):
            self.registry = ToolRegistry()
            self._setup_tools()

        def _setup_tools(self) -> None:
            """Setup business tools."""
            # CRM tools
            self.registry.register(
                "crm.get_customer",
                self._get_customer,
                "Get customer information by ID",
            )
            self.registry.register(
                "crm.search_customers",
                self._search_customers,
                "Search customers by criteria",
            )

            # Inventory tools
            self.registry.register(
                "inventory.check_stock",
                self._check_stock,
                "Check product stock level",
            )
            self.registry.register(
                "inventory.reserve_item",
                self._reserve_item,
                "Reserve an item for order",
            )

            # Notification tools
            self.registry.register(
                "notify.send_email",
                self._send_email,
                "Send email notification",
            )
            self.registry.register(
                "notify.send_sms",
                self._send_sms,
                "Send SMS notification",
            )

        def _get_customer(self, customer_id: str) -> dict[str, Any]:
            return {"id": customer_id, "name": f"Customer {customer_id}"}

        def _search_customers(self, query: str) -> list[dict[str, Any]]:
            return [{"id": "1", "name": "Match 1"}, {"id": "2", "name": "Match 2"}]

        def _check_stock(self, product_id: str) -> dict[str, Any]:
            return {"product_id": product_id, "quantity": 100, "available": True}

        def _reserve_item(self, product_id: str, quantity: int) -> bool:
            return True

        def _send_email(self, to: str, subject: str, body: str) -> bool:
            return True

        def _send_sms(self, phone: str, message: str) -> bool:
            return True

        def list_all_tools(self) -> dict[str, list[str]]:
            """List all tools by category."""
            tools = self.registry.list_tools()
            categories: dict[str, list[str]] = {}
            for tool in tools:
                if "." in tool:
                    category, name = tool.split(".", 1)
                else:
                    category, name = "general", tool
                categories.setdefault(category, []).append(name)
            return categories

    # Create and display registry
    business_registry = BusinessToolRegistry()

    print("Business Tool Registry:")
    categories = business_registry.list_all_tools()
    for category, tools in categories.items():
        print(f"\n  {category.upper()}:")
        for tool in tools:
            print(f"    - {tool}")

    # Example usage
    print("\n--- Example Usage ---")
    customer = business_registry._get_customer("cust_123")
    print(f"Get customer: {customer}")

    stock = business_registry._check_stock("prod_456")
    print(f"Check stock: {stock}")


# =============================================================================
# Main Entry Point
# =============================================================================
async def main() -> None:
    """Run all tool registry demonstrations."""
    print("=" * 60)
    print("Tool Registry Examples")
    print("=" * 60)

    demos = [
        ("Basic Tool Registration", demo_basic_registration),
        ("Tool with Parameters", demo_tool_with_parameters),
        ("Async Tool Support", demo_async_tools),
        ("Tool Categories", demo_tool_categories),
        ("Tool Validation", demo_tool_validation),
        ("Built-in Web Search Tool", demo_web_search_tool),
        ("Tool Execution Context", demo_execution_context),
        ("Tool Error Handling", demo_error_handling),
        ("Tool Metadata", demo_tool_metadata),
        ("Real-World Tool Registry", demo_real_world_registry),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            if asyncio.iscoroutinefunction(demo_func):
                await demo_func()
            else:
                demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
