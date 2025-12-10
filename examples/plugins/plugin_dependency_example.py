#!/usr/bin/env python3
"""Plugin Dependency Checker Example."""

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.dependency_checker import (
    DependencyChecker,
    DependencyCheckResult,
    DependencyStatus,
)
from feishu_webhook_bot.plugins.manifest import PackageDependency

setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


def demo_basic_check():
    print("\n" + "=" * 60)
    print("Demo 1: Basic Dependency Check")
    print("=" * 60)
    
    checker = DependencyChecker()
    
    # Check some common packages
    packages = [
        PackageDependency(name="pydantic", version=">=2.0.0"),
        PackageDependency(name="httpx", version=">=0.27.0"),
        PackageDependency(name="nonexistent-package", version=">=1.0.0"),
    ]
    
    print("Checking package dependencies:")
    for pkg in packages:
        status = checker.check_python_dependency(pkg)
        symbol = "" if status.satisfied else ""
        print(f"  {symbol} {pkg.name}{pkg.version}")
        if status.installed_version:
            print(f"      Installed: {status.installed_version}")
        if status.error:
            print(f"      Error: {status.error}")


def main():
    print("=" * 60)
    print("Plugin Dependency Checker Examples")
    print("=" * 60)
    
    demos = [
        ("Basic Dependency Check", demo_basic_check),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
