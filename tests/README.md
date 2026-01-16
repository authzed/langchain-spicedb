# Tests for langchain-spicedb

This directory contains unit and integration tests for the langchain-spicedb package, following LangChain's standard testing conventions.

## Test Structure

```
tests/
├── unit_tests/          # Tests that run in isolation with mocks
│   ├── test_retrievers.py
│   └── test_tools.py
├── integration_tests/   # Tests that require real SpiceDB instance
│   ├── test_retrievers.py
│   └── test_tools.py
├── conftest.py         # Shared pytest fixtures
└── README.md           # This file
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -e ".[test]"
# or
pip install -e ".[dev]"  # Includes additional dev tools
```

### Unit Tests

Unit tests run in isolation using mocks and do not require external services:

```bash
# Run all unit tests
pytest tests/unit_tests/

# Run specific test file
pytest tests/unit_tests/test_retrievers.py

# Run specific test class
pytest tests/unit_tests/test_retrievers.py::TestSpiceDBRetrieverUnit

# Run specific test
pytest tests/unit_tests/test_retrievers.py::TestSpiceDBRetrieverUnit::test_retriever_initialization
```

### Integration Tests

Integration tests require a running SpiceDB instance. Set environment variables before running:

```bash
export SPICEDB_ENDPOINT="localhost:50051"
export SPICEDB_TOKEN="somerandomkeyhere"
```

Run integration tests:

```bash
# Run all integration tests
pytest tests/integration_tests/

# Run specific integration test file
pytest tests/integration_tests/test_retrievers.py

# Skip integration tests (useful for CI without SpiceDB)
pytest -m "not integration"
```

### Run All Tests

```bash
# Run all tests (unit + integration)
pytest tests/

# Run with coverage
pytest --cov=langchain_spicedb --cov-report=html tests/

# Run with verbose output
pytest -v tests/

# Run async tests
pytest -v --asyncio-mode=auto tests/
```

## Test Organization

### Unit Tests

Unit tests validate components in isolation:
- Use mocks for SpiceDB authorizer
- Test input validation
- Test synchronous and asynchronous methods
- Test error handling
- No external dependencies required

### Integration Tests

Integration tests validate real-world behavior:
- Require running SpiceDB instance
- Test actual authorization checks
- Test network connectivity
- Test TLS configuration
- Test batch operations with real data

Tests are automatically skipped if `SPICEDB_ENDPOINT` is not set:

```python
@pytest.mark.skipif(
    not os.getenv("SPICEDB_ENDPOINT"),
    reason="SPICEDB_ENDPOINT not set - skipping integration test",
)
def test_with_real_spicedb():
    ...
```

## Setting Up SpiceDB for Testing

### Option 1: Local SpiceDB with Docker

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

### Option 2: SpiceDB Cloud

1. Sign up at https://app.authzed.com
2. Create a new permission system
3. Get your endpoint and token
4. Set environment variables:

```bash
export SPICEDB_ENDPOINT="grpc.authzed.com:443"
export SPICEDB_TOKEN="your_token_here"
```

### Set Up Test Schema

Create test relationships in SpiceDB:

```bash
# Using zed CLI
zed schema write tests/schema.zed

# Create test relationships
zed relationship create article:123 viewer user:tim
zed relationship create article:456 viewer user:tim
zed relationship create article:789 viewer user:alice
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Run only unit tests (no external dependencies)
pytest tests/unit_tests/ --tb=short

# Run integration tests if SpiceDB is available
if [ -n "$SPICEDB_ENDPOINT" ]; then
  pytest tests/integration_tests/
fi
```

## Test Coverage

To generate a coverage report:

```bash
pytest --cov=langchain_spicedb --cov-report=html tests/
open htmlcov/index.html
```

## Debugging Tests

Run tests with debugging output:

```bash
# With print statements visible
pytest -s tests/

# With detailed logging
pytest --log-cli-level=DEBUG tests/

# Stop on first failure
pytest -x tests/

# Drop into debugger on failure
pytest --pdb tests/
```

## Common Issues

### Import Errors

If you see import errors, make sure the package is installed in editable mode:

```bash
pip install -e ".[all,test]"
```

### Async Test Failures

If async tests fail, ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### SpiceDB Connection Errors

If integration tests fail with connection errors:

1. Verify SpiceDB is running: `curl localhost:50051`
2. Check environment variables are set
3. Verify the token matches SpiceDB configuration
4. Check firewall rules allow connections to port 50051

## Writing New Tests

When adding new tests:

1. **Unit tests**: Place in `tests/unit_tests/`, use mocks, no external dependencies
2. **Integration tests**: Place in `tests/integration_tests/`, require SpiceDB
3. **Use descriptive names**: `test_retriever_filters_unauthorized_documents`
4. **Add docstrings**: Explain what the test validates
5. **Follow patterns**: Look at existing tests for examples

Example unit test:

```python
def test_new_feature(self, mock_authorizer):
    """Test that new feature works correctly."""
    # Arrange
    retriever = SpiceDBRetriever(...)

    # Act
    result = retriever.invoke("query")

    # Assert
    assert result == expected_value
```

Example integration test:

```python
@pytest.mark.skipif(
    not os.getenv("SPICEDB_ENDPOINT"),
    reason="SPICEDB_ENDPOINT not set",
)
def test_new_feature_integration(self, spicedb_config):
    """Test that new feature works with real SpiceDB."""
    tool = SpiceDBPermissionTool(**spicedb_config)
    result = tool.invoke(...)
    assert result in ["true", "false"]
```
