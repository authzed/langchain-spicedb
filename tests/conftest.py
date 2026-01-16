"""Pytest configuration and shared fixtures for langchain-spicedb tests."""

import pytest  # noqa: F401


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio support"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring external services",
    )
