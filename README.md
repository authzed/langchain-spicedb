# LangChain-SpiceDB Integration

Authorization library for RAG (Retrieval-Augmented Generation) pipelines using SpiceDB. Designed for LangChain and LangGraph integrations with support for any vector store (Pinecone, FAISS, Weaviate, Chroma, etc.).

This package follows [LangChain's official integration guidelines](https://python.langchain.com/docs/contributing/) and provides standard LangChain components (BaseRetriever, BaseTool) plus additional middleware patterns.

## Features

- **LangChain & LangGraph Integration**: First-class support for modern LLM frameworks
- **Vector Store Agnostic**: Compatible with Pinecone, FAISS, Weaviate, Chroma, and more
- **Post-Filter Authorization**: Filters retrieved documents based on SpiceDB permissions
- **Efficient Bulk Permissions**: Uses SpiceDB's native bulk API for optimal performance
- **Observable**: Returns detailed metrics about authorization decisions
- **Type-Safe**: Full type hints for better IDE support
- **Async by Default**: Built for high-performance async operations

## Why This Package?

Most RAG pipelines retrieve documents without considering user permissions. This package solves that by:

1. **Post-retrieval filtering**: Retrieve best semantic matches first, then filter by permissions
2. **Deterministic authorization**: Every document is checked against SpiceDB before being used
3. **Framework integration**: Native LangChain and LangGraph components for seamless integration
4. **Vector store agnostic**: Not tied to any specific vector database

## Which Component Should I Use?

Choose the right component based on your use case:

| Component | Use Case | Best For |
|-----------|----------|----------|
| **SpiceDBRetriever** | Simple RAG pipelines | Drop-in replacement for any retriever. Wraps your existing retriever with authorization. |
| **SpiceDBAuthFilter** | LangChain chains with middleware | Filtering documents in the middle of a chain. Reusable across different users via `config`. |
| **create_auth_node** | LangGraph workflows | Complex multi-step workflows with state management. Provides authorization metrics in state. |
| **SpiceDBPermissionTool** | Agentic workflows | Give agents the ability to check permissions before taking actions. |
| **SpiceDBBulkPermissionTool** | Agentic workflows (batch) | Same as above but for checking multiple resources at once. |

### Quick Decision Guide

**Use SpiceDBRetriever if:**
- You have a simple RAG pipeline
- You always use the same user per retriever instance and you don't need to reuse the retriever across different users

**Use SpiceDBAuthFilter if:**
- You're building LangChain LCEL chains
- You want to reuse the same chain for multiple users
- You need to pass user context at runtime via `config`

**Use create_auth_node if:**
- You're using LangGraph for complex workflows
- You need state management and observability
- You're building multi-step agentic workflows

**Use SpiceDBPermissionTool / SpiceDBBulkPermissionTool if:**
- You're building agents with LangChain
- Your agent needs to check permissions as part of its decision-making and you want agents to explain why actions are allowed or denied
- You're implementing permission-aware automation

### Example: Same Pipeline, Different Patterns

**Pattern 1: SpiceDBRetriever (simplest)**
```python
retriever = SpiceDBRetriever(
    base_retriever=vectorstore.as_retriever(),
    subject_id="alice",  # Fixed user
    ...
)
chain = retriever | prompt | llm
```

**Pattern 2: SpiceDBAuthFilter (reusable)**
```python
auth = SpiceDBAuthFilter(...)
chain = retriever | auth | prompt | llm

# Same chain, different users
await chain.ainvoke("question", config={"configurable": {"subject_id": "alice"}})
await chain.ainvoke("question", config={"configurable": {"subject_id": "bob"}})
```

**Pattern 3: LangGraph Node (stateful)**
```python
graph.add_node("authorize", create_auth_node(...))
# Authorization metrics available in state['auth_results']
```

**Pattern 4: Agent Tool (agentic)**
```python
tools = [SpiceDBPermissionTool(...)]
agent = create_agent(llm, tools, system_prompt="You are a helpful assistant.")
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

# Initialize auth filter
auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    subject_type="user",
    resource_type="article",
    resource_id_key="article_id",
    permission="view",
)

# Build chain once
chain = (
    RunnableParallel({
        "context": retriever | auth,  # Authorization happens here
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)

# Pass user at runtime - reuse same chain for different users
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

# Add nodes
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_auth_node(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
))
graph.add_node("generate", generate_node)

# Wire it up
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "authorize")
graph.add_edge("authorize", "generate")
graph.add_edge("generate", END)

# Run
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

### SpiceDBRetriever

Wraps any LangChain retriever with SpiceDB authorization:

```python
from langchain_spicedb import SpiceDBRetriever

retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),
    subject_id="alice",
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
)

docs = await retriever.ainvoke("query")
```

### SpiceDBPermissionTool

LangChain tool for agents to check permissions:

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

Same as `SpiceDBPermissionTool` but check permissions for multiple resources at once:

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
