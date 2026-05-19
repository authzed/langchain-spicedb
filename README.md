# LangChain-SpiceDB Integration

Authorization library for RAG (Retrieval-Augmented Generation) pipelines using SpiceDB. Designed for LangChain and LangGraph integrations with support for any vector store (Pinecone, FAISS, Weaviate, Chroma, etc.).

This package follows [LangChain's official integration guidelines](https://python.langchain.com/docs/contributing/) and provides standard LangChain components (BaseRetriever, BaseTool) plus additional middleware patterns.

## Features

- **LangChain & LangGraph Integration**: First-class support for modern LLM frameworks
- **Vector Store Agnostic**: Compatible with Pinecone, FAISS, Weaviate, Chroma, and more
- **Post-Filter Authorization**: Retrieve semantically, then filter by SpiceDB permissions
- **Pre-Filter Authorization**: Fetch authorized resource IDs via LookupResources first, then run a filtered vector store search — ideal when users have access to a small fraction of a large corpus
- **Efficient Bulk Permissions**: Uses SpiceDB's native bulk API for optimal performance
- **Observable**: Returns detailed metrics about authorization decisions
- **Type-Safe**: Full type hints for better IDE support
- **Async by Default**: Built for high-performance async operations

## Why This Package?

Most RAG pipelines retrieve documents without considering user permissions. This package solves that by:

1. **Post-retrieval filtering**: Retrieve best semantic matches first, then filter by permissions
2. **Pre-retrieval filtering**: Fetch all resource IDs the user can access via SpiceDB's `LookupResources` API, then run a filtered vector store search — no unauthorized documents are retrieved
3. **Deterministic authorization**: Every document is checked against SpiceDB before being used
4. **Framework integration**: Native LangChain and LangGraph components for seamless integration
5. **Vector store agnostic**: Not tied to any specific vector database

## Which Component Should I Use?

| Component | Pattern | Use Case |
|-----------|---------|----------|
| **SpiceDBAuthFilter** | Post-filter | LangChain LCEL chains. Reusable across different users via `config`. |
| **SpiceDBPreFilterRetriever** | Pre-filter | LangChain LCEL chains. Users have access to a small fraction of a large corpus. Requires a `filter_factory` matching your vector store's filter syntax. |
| **create_auth_node** | Post-filter | LangGraph workflows. Multi-step workflows with state management and authorization metrics. |
| **create_pre_filter_auth_node** | Pre-filter | LangGraph workflows. Single node that calls LookupResources then runs a filtered vector search. No separate retrieval step needed. |
| **SpiceDBPermissionTool** | Check | Agents that need to check a single permission before acting. |
| **SpiceDBBulkPermissionTool** | Check | Agents that need to check permissions on multiple resources at once. |

### Quick Decision Guide

**Post-filter vs Pre-filter:**
- Use **post-filter** (`SpiceDBAuthFilter`, `create_auth_node`) when users have access to most documents — semantic search quality is highest because all documents are candidates.
- Use **pre-filter** (`SpiceDBPreFilterRetriever`, `create_pre_filter_auth_node`) when users have access to a small subset of a large corpus — avoids retrieving unauthorized content entirely.

**LangChain vs LangGraph:**
- Use **LangChain** components (`SpiceDBAuthFilter`, `SpiceDBPreFilterRetriever`) for LCEL chains.
- Use **LangGraph** components (`create_auth_node`, `create_pre_filter_auth_node`) for state graph workflows.

### Example: Same Pipeline, Different Patterns

**Pattern 1: SpiceDBAuthFilter (post-filter, LCEL)**
```python
auth = SpiceDBAuthFilter(...)
chain = retriever | auth | prompt | llm

# Same chain, different users at call time
await chain.ainvoke("question", config={"configurable": {"subject_id": "alice"}})
await chain.ainvoke("question", config={"configurable": {"subject_id": "bob"}})
```

**Pattern 2: SpiceDBPreFilterRetriever (pre-filter, LCEL)**
```python
retriever = SpiceDBPreFilterRetriever(
    vector_store=vector_store,
    filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
    subject_id="alice",
    ...
)
chain = retriever | prompt | llm
```

**Pattern 3: create_auth_node (post-filter, LangGraph)**
```python
graph.add_node("authorize", create_auth_node(...))
# Authorization metrics available in state['auth_results']
```

**Pattern 4: create_pre_filter_auth_node (pre-filter, LangGraph)**
```python
# Single node replaces separate retrieve + authorize nodes
graph.add_node("retrieve_authorized", create_pre_filter_auth_node(
    vector_store=vector_store,
    filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
    ...
))
graph.add_edge("retrieve_authorized", "generate")
```

**Pattern 5: Agent Tool**
```python
tools = [SpiceDBPermissionTool(...)]
agent = create_agent(llm, tools, system_prompt="...")
# Agent can check "Can user alice delete document 123?" and explain the result
```

## Installation

```bash
pip install langchain-spicedb
```

### Optional Dependencies

```bash
# Install with LangChain support
pip install langchain-spicedb[langchain]

# Install with LangGraph support
pip install langchain-spicedb[langgraph]

# Install everything (recommended)
pip install langchain-spicedb[all]
```

### Development Installation

```bash
git clone https://github.com/authzed/langchain-spicedb.git
cd langchain-spicedb
pip install -e ".[all,dev]"
```

## Quick Start

### 1. Start SpiceDB

```bash
docker run --rm -p 50051:50051 authzed/spicedb serve \
    --grpc-preshared-key "sometoken" \
    --grpc-no-tls
```

### 2. Define Schema and Permissions

```python
from authzed.api.v1 import Client, WriteSchemaRequest
from grpcutil import insecure_bearer_token_credentials

client = Client("localhost:50051", insecure_bearer_token_credentials("sometoken"))

schema = """
definition user {}

definition article {
    relation viewer: user
    permission view = viewer
}
"""

await client.WriteSchema(WriteSchemaRequest(schema=schema))
```

### 3. Use in LangChain

```python
from langchain_spicedb import SpiceDBAuthFilter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_type="user",
    resource_type="article",
    resource_id_key="article_id",
    permission="view",
)

chain = (
    RunnableParallel({
        "context": retriever | auth,
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)

answer = await chain.ainvoke(
    "Your question?",
    config={"configurable": {"subject_id": "alice"}}
)
```

### 4. Use in LangGraph

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

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "authorize")
graph.add_edge("authorize", "generate")
graph.add_edge("generate", END)

app = graph.compile()
result = await app.ainvoke({
    "question": "What is SpiceDB?",
    "subject_id": "alice",
})
```

## Documentation

- **[Configuration Guide](docs/configuration.md)** - Detailed configuration options, metadata requirements, and error handling
- **[LangGraph Guide](docs/langgraph-guide.md)** - Advanced LangGraph patterns, custom state, and visualization
- **[Examples](examples/README.md)** - Complete working examples and tutorials
- **[Testing Guide](tests/README.md)** - Running tests and integration testing

## Components

### SpiceDBAuthFilter

Post-filter authorization as a LangChain `Runnable`. Sits between a retriever and the rest of the chain, filtering documents based on SpiceDB permissions. Reusable across users via `config`:

```python
from langchain_spicedb import SpiceDBAuthFilter

auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    subject_type="user",
    resource_id_key="article_id",
    permission="view",
)

authorized_docs = await auth.ainvoke(
    docs,
    config={"configurable": {"subject_id": "alice"}}
)
```

### SpiceDBPreFilterRetriever

Pre-filter authorization as a LangChain `BaseRetriever`. Calls SpiceDB's `LookupResources` to get the user's authorized IDs, then runs a filtered vector search:

```python
from langchain_spicedb import SpiceDBPreFilterRetriever

retriever = SpiceDBPreFilterRetriever(
    vector_store=vector_store,
    filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
    subject_id="alice",
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    permission="view",
)

docs = await retriever.ainvoke("What is Python?")
```

### SpiceDBPermissionTool

LangChain tool for agents to check a single permission:

```python
from langchain_spicedb import SpiceDBPermissionTool

tool = SpiceDBPermissionTool(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_type="user",
    resource_type="article",
)

result = tool.invoke({
    "subject_id": "alice",
    "resource_id": "doc123",
    "permission": "view"
})
# Returns: "true" or "false"
```

### SpiceDBBulkPermissionTool

Same as `SpiceDBPermissionTool` but checks multiple resources at once:

```python
from langchain_spicedb import SpiceDBBulkPermissionTool

tool = SpiceDBBulkPermissionTool(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_type="user",
    resource_type="article",
)

result = tool.invoke({
    "subject_id": "alice",
    "resource_ids": "doc1,doc2,doc3",
    "permission": "view"
})
# Returns: "alice can access: doc1, doc2" or "alice cannot access any..."
```

## Performance

- **Native Bulk API**: Uses SpiceDB's `CheckBulkPermissionsRequest` for optimal performance
- **Single API Call**: All permission checks happen in one request, not N individual calls
- **Async Operations**: All operations are async for better performance

## Testing

```bash
# Run unit tests
pytest tests/unit_tests/

# Run integration tests (requires SpiceDB)
SPICEDB_ENDPOINT=localhost:50051 SPICEDB_TOKEN=sometoken pytest tests/integration_tests/

# With coverage
pytest tests/ --cov=langchain_spicedb
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

Apache-2.0 License

## Related Projects

- [SpiceDB](https://github.com/authzed/spicedb) - Authorization database
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Graph-based LLM workflows

---

**Need help?** Check out the [examples](examples/README.md) or open an issue on [GitHub](https://github.com/authzed/langchain-spicedb/issues).
