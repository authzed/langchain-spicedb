# Configuration Guide

Complete reference for configuring langchain-spicedb components.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [Advanced Configuration](#advanced-configuration)
- [Document Metadata Requirements](#document-metadata-requirements)
- [Authorization Results](#authorization-results)
- [Error Handling](#error-handling)

## Basic Configuration

All SpiceDB components require these core parameters:

```python
from langchain_spicedb import SpiceDBRetriever, SpiceDBAuthFilter, SpiceDBPermissionTool

# Basic configuration (all parameters required)
config = {
    "spicedb_endpoint": "localhost:50051",  # SpiceDB server address
    "spicedb_token": "sometoken",           # Pre-shared authentication key
    "resource_type": "article",             # Resource type from schema
    "subject_type": "user",                 # Subject type from schema (default: "user")
    "permission": "view",                   # Permission to check (default: "view")
    "resource_id_key": "article_id",        # Metadata key for resource ID
}
```

### SpiceDBRetriever Configuration

```python
from langchain_spicedb import SpiceDBRetriever

retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),  # Your existing retriever
    subject_id="alice",                          # User to authorize for
    **config
)
```

### SpiceDBAuthFilter Configuration

```python
from langchain_spicedb import SpiceDBAuthFilter

auth_filter = SpiceDBAuthFilter(
    subject_id="alice",  # Can be set at runtime via config
    **config
)

# Or configure per-request:
result = await auth_filter.ainvoke(
    docs,
    config={"configurable": {"subject_id": "bob"}}
)
```

### SpiceDBPermissionTool Configuration

```python
from langchain_spicedb import SpiceDBPermissionTool

tool = SpiceDBPermissionTool(
    **config
)

# Subject ID provided when invoking the tool
result = tool.invoke({
    "subject_id": "alice",
    "resource_id": "doc123",
    "permission": "view"
})
```

## Advanced Configuration

### TLS/SSL Configuration

Enable TLS for production deployments:

```python
from langchain_spicedb import SpiceDBAuthorizer

authorizer = SpiceDBAuthorizer(
    spicedb_endpoint="spicedb.example.com:443",
    spicedb_token="your-production-token",
    use_tls=True,  # Enable TLS
    resource_type="article",
    subject_type="user",
    permission="view",
    resource_id_key="article_id",
)
```

### Fail Open vs. Fail Closed

Control behavior when SpiceDB is unavailable:

```python
# Fail Closed (Default - Recommended for Production)
# Denies access if SpiceDB is unreachable
authorizer = SpiceDBAuthorizer(
    fail_open=False,  # Default
    **config
)

# Fail Open (Development/Testing Only)
# Allows access if SpiceDB is unreachable
authorizer = SpiceDBAuthorizer(
    fail_open=True,
    **config
)
```

**Security Note**: Always use `fail_open=False` in production to ensure security.

### Custom Subject and Permission Types

Match your SpiceDB schema:

```python
# Example schema:
# definition organization { ... }
# definition document {
#     relation owner: organization
#     permission read = owner
# }

authorizer = SpiceDBAuthorizer(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="document",      # From schema
    subject_type="organization",   # From schema
    permission="read",             # From schema
    resource_id_key="doc_id",      # Metadata key
)
```

### Environment Variables

Load configuration from environment:

```python
import os
from langchain_spicedb import SpiceDBRetriever

retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),
    spicedb_endpoint=os.getenv("SPICEDB_ENDPOINT", "localhost:50051"),
    spicedb_token=os.getenv("SPICEDB_TOKEN"),
    subject_id=os.getenv("USER_ID"),
    resource_type="article",
    resource_id_key="article_id",
)
```

## Document Metadata Requirements

Your documents must include the resource ID in metadata:

```python
from langchain_core.documents import Document

# Single document
doc = Document(
    page_content="Your content here...",
    metadata={
        "article_id": "doc123",  # Must match resource_id_key
        "title": "Example Article",
        "author": "Alice",
    }
)

# Multiple documents
docs = [
    Document(
        page_content="Content 1",
        metadata={"article_id": "doc1"}
    ),
    Document(
        page_content="Content 2",
        metadata={"article_id": "doc2"}
    ),
]
```

### Metadata Key Flexibility

The `resource_id_key` parameter lets you adapt to any metadata structure:

```python
# Your documents use "doc_id"
SpiceDBRetriever(
    resource_id_key="doc_id",
    ...
)

# Your documents use "resource_identifier"
SpiceDBRetriever(
    resource_id_key="resource_identifier",
    ...
)

# Nested metadata (using dot notation)
SpiceDBRetriever(
    resource_id_key="metadata.document.id",  # Access nested fields
    ...
)
```

### Missing Metadata Handling

Documents without the required metadata key are automatically denied:

```python
docs = [
    Document(page_content="Doc 1", metadata={"article_id": "123"}),  # ✓ Will be checked
    Document(page_content="Doc 2", metadata={"other_field": "value"}),  # ✗ Denied (missing article_id)
]

result = await auth_filter.ainvoke(docs, subject_id="alice")
# result.authorized_documents contains only Doc 1 (if authorized)
# result.denied_resource_ids contains ["MISSING_METADATA"]
```

## Authorization Results

### LangChain Integration

#### Default Behavior (Documents Only)

By default, `SpiceDBAuthFilter` returns only the authorized documents:

```python
from langchain_spicedb import SpiceDBAuthFilter

auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_id="alice",
    subject_type="user",
    resource_type="article",
    resource_id_key="article_id",
    permission="view",
    # return_metrics=False  # Default
)

# Returns: List[Document]
authorized_docs = await auth.ainvoke(docs)
```

#### With Metrics

Set `return_metrics=True` to get detailed authorization information:

```python
auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_id="alice",
    subject_type="user",
    resource_type="article",
    resource_id_key="article_id",
    permission="view",
    return_metrics=True,  # Enable metrics
)

# Returns: AuthorizationResult
result = await auth.ainvoke(docs)

# Access detailed information
print(f"Authorized: {result.total_authorized}/{result.total_retrieved}")
print(f"Authorization rate: {result.authorization_rate:.1%}")
print(f"Latency: {result.check_latency_ms:.2f}ms")
print(f"Denied IDs: {result.denied_resource_ids}")

# Use authorized documents
for doc in result.authorized_documents:
    print(doc.page_content)
```

#### AuthorizationResult Fields

```python
@dataclass
class AuthorizationResult:
    authorized_documents: List[Document]  # Documents user can access
    total_retrieved: int                  # Total documents checked
    total_authorized: int                 # Number authorized
    authorization_rate: float             # Percentage (0.0 to 1.0)
    denied_resource_ids: List[str]        # IDs that were denied
    check_latency_ms: float              # Time taken for checks
```

### LangGraph Integration

Metrics are automatically available in the state under `auth_results`:

```python
from langgraph.graph import StateGraph, END
from langchain_spicedb import create_auth_node, RAGAuthState

graph = StateGraph(RAGAuthState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_auth_node(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
))
graph.add_node("generate", generate_node)

# ... add edges ...

app = graph.compile()
result = await app.ainvoke({
    "question": "What is SpiceDB?",
    "subject_id": "alice"
})

# Access metrics from state
auth_metrics = result["auth_results"]
print(f"Retrieved: {auth_metrics['total_retrieved']}")
print(f"Authorized: {auth_metrics['total_authorized']}")
print(f"Rate: {auth_metrics['authorization_rate']:.1%}")
print(f"Denied: {auth_metrics['denied_resource_ids']}")
print(f"Latency: {auth_metrics['check_latency_ms']:.2f}ms")
```

#### LangGraph Metrics Schema

```python
auth_results = {
    "total_retrieved": 10,               # Documents retrieved
    "total_authorized": 7,               # Documents authorized
    "authorization_rate": 0.7,           # 70% authorized
    "denied_resource_ids": ["3", "5"],   # Denied doc IDs
    "check_latency_ms": 45.2,           # Permission check time
}
```

### SpiceDB Tools Results

Tools return simple string results for LLM consumption:

```python
from langchain_spicedb import SpiceDBPermissionTool, SpiceDBBulkPermissionTool

# Single permission check
permission_tool = SpiceDBPermissionTool(...)
result = permission_tool.invoke({
    "subject_id": "alice",
    "resource_id": "doc123",
    "permission": "view"
})
# Returns: "true" or "false"

# Bulk permission check
bulk_tool = SpiceDBBulkPermissionTool(...)
result = bulk_tool.invoke({
    "subject_id": "alice",
    "resource_ids": "doc1,doc2,doc3",
    "permission": "view"
})
# Returns: "alice can access: doc1, doc2" or "alice cannot access any of the requested resources"
```

## Error Handling

### Connection Errors

```python
try:
    result = await auth_filter.ainvoke(docs, subject_id="alice")
except Exception as e:
    if "failed to connect" in str(e).lower():
        print("SpiceDB is unreachable")
        # Handle connection failure
```

### Authentication Errors

```python
# Invalid token will raise an error
try:
    authorizer = SpiceDBAuthorizer(
        spicedb_endpoint="localhost:50051",
        spicedb_token="invalid-token",
        ...
    )
    result = await authorizer.filter_documents(docs, "alice")
except Exception as e:
    if "unauthenticated" in str(e).lower():
        print("Invalid SpiceDB token")
        # Handle auth failure
```

### Schema Errors

```python
# Non-existent resource type will fail
try:
    authorizer = SpiceDBAuthorizer(
        resource_type="nonexistent",  # Not in schema
        ...
    )
    result = await authorizer.filter_documents(docs, "alice")
except Exception as e:
    print(f"Schema error: {e}")
    # Handle schema mismatch
```

### Logging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("langchain_spicedb")
logger.setLevel(logging.DEBUG)

# Now you'll see detailed logs
result = await auth_filter.ainvoke(docs, subject_id="alice")
```

## Configuration Best Practices

1. **Use Environment Variables**: Keep credentials out of code
2. **Enable TLS in Production**: Use `use_tls=True` for production SpiceDB
3. **Fail Closed**: Keep `fail_open=False` in production
4. **Monitor Metrics**: Track authorization rates and latency
5. **Validate Metadata**: Ensure all documents have required metadata
6. **Test Configuration**: Verify schema matches before deploying

## Example: Complete Production Configuration

```python
import os
from langchain_spicedb import SpiceDBRetriever
from langchain_community.vectorstores import Pinecone

# Load from environment
SPICEDB_ENDPOINT = os.getenv("SPICEDB_ENDPOINT")
SPICEDB_TOKEN = os.getenv("SPICEDB_TOKEN")
USER_ID = os.getenv("USER_ID")

# Create retriever with production config
retriever = SpiceDBRetriever(
    base_retriever=Pinecone.from_existing_index("my-index").as_retriever(),
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    subject_id=USER_ID,
    subject_type="user",
    resource_type="document",
    resource_id_key="doc_id",
    permission="view",
    use_tls=True,       # Production TLS
    fail_open=False,    # Fail closed (secure)
)

# Use in production
try:
    docs = await retriever.ainvoke("user query")
    # Process authorized documents
except Exception as e:
    logger.error(f"Authorization failed: {e}")
    # Handle error gracefully
```

## Next Steps

- See [LangGraph Guide](langgraph-guide.md) for advanced integration patterns
- See [Performance Guide](performance.md) for optimization tips
- See [Examples](../examples/README.md) for complete working examples
