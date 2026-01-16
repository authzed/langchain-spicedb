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

Check permissions for multiple resources at once:

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

## Use Cases

1. **Multi-Tenant SaaS**: Different customers see different documents
2. **Enterprise RAG**: Role-based access control for internal knowledge bases
3. **Healthcare/Legal**: Compliance-required document access controls
4. **Collaborative Platforms**: Team-based permissions for shared documents
5. **Document Management**: Fine-grained access control for sensitive information

## Vector Store Compatibility

Works with any vector store that returns documents with metadata:

✅ Pinecone • ✅ FAISS • ✅ Weaviate • ✅ Chroma • ✅ Qdrant • ✅ Milvus • ✅ Any custom vector store

## Performance

- **Native Bulk API**: Uses SpiceDB's `CheckBulkPermissionsRequest` for optimal performance
- **Single API Call**: All permission checks happen in one request, not N individual calls
- **Async Operations**: All operations are async for better performance

**Performance Impact:**
- Before: 100 documents = 100 API calls
- After: 100 documents = 1 API call
- Result: Lower latency, reduced network overhead, better throughput

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
