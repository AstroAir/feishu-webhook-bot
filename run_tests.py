"""Test runner script for enhanced YAML configuration tests."""

import sys
import subprocess


def run_tests():
    """Run all tests with coverage."""
    print("=" * 80)
    print("Running Enhanced YAML Configuration Tests")
    print("=" * 80)
    
    # Test files to run
    test_files = [
        "tests/test_task_executor.py",
        "tests/test_task_manager.py",
        "tests/test_task_templates.py",
        "tests/test_plugin_config.py",
        "tests/test_environment_config.py",
        "tests/test_validation.py",
        "tests/test_config_watcher.py",
        "tests/test_integration.py",
    ]
    
    # Run tests with coverage
    cmd = [
        "pytest",
        "-v",
        "--tb=short",
        "--cov=src/feishu_webhook_bot",
        "--cov-report=term-missing",
        "--cov-report=html",
    ] + test_files
    
    print(f"\nRunning command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    print("\n" + "=" * 80)
    if result.returncode == 0:
        print("✅ All tests passed!")
        print("\nCoverage report generated in htmlcov/index.html")
    else:
        print("❌ Some tests failed!")
        print(f"\nExit code: {result.returncode}")
    print("=" * 80)
    
    return result.returncode


def run_specific_test(test_name):
    """Run a specific test file."""
    print(f"Running {test_name}...")
    
    cmd = ["pytest", "-v", "--tb=short", f"tests/{test_name}"]
    
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if not test_name.startswith("test_"):
            test_name = f"test_{test_name}"
        if not test_name.endswith(".py"):
            test_name = f"{test_name}.py"
        
        exit_code = run_specific_test(test_name)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)

