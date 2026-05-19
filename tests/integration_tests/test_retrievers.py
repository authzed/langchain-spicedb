"""Integration tests for SpiceDB retrievers.

These tests require a running SpiceDB instance.
Set SPICEDB_ENDPOINT and SPICEDB_TOKEN to run these tests.
"""

import os
import pytest


@pytest.fixture
def spicedb_config():
    """Get SpiceDB configuration from environment."""
    endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    return {
        "spicedb_endpoint": endpoint,
        "spicedb_token": token,
    }
