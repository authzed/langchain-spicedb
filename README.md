# SpiceDB RAG Authorization

A universal, framework-agnostic authorization library for RAG (Retrieval-Augmented Generation) pipelines using SpiceDB. Works seamlessly with any framework (LangChain, LangGraph, custom pipelines) and any vector store (Pinecone, FAISS, Weaviate, Chroma, etc.).

**NOTE:** This is very much in alpha mode and is intended as a learning exercise rather than a production deployment. I've tested it against the `langchain_example.py` and also the SpiceDB - RAG example in the `authzed/workshops` [repo here](https://github.com/authzed/workshops/blob/main/secure-rag-pipelines/01-rag.ipynb)

## Features

- **Universal Compatibility**: Works with any RAG framework or custom implementation
- **Vector Store Agnostic**: Compatible with Pinecone, FAISS, Weaviate, Chroma, and more
- **Post-Filter Authorization**: Filters retrieved documents based on SpiceDB permissions
- **Batch Processing**: Optimized concurrent permission checks for performance
- **Observable**: Returns detailed metrics about authorization decisions
- **Multiple Interfaces**: Use as standalone, LangChain Runnable, or LangGraph node
- **Type-Safe**: Full type hints for better IDE support
- **Async by Default**: Built for high-performance async operations

## Why This Package?

Most RAG pipelines retrieve documents without considering user permissions. This package solves that by:

1. **Post-retrieval filtering**: Retrieve best semantic matches first, then filter by permissions
2. **Deterministic authorization**: Every document is checked against SpiceDB before being used
3. **Zero vendor lock-in**: Not tied to any specific framework or vector store
4. **Drop-in integration**: Minimal code changes to existing pipelines

## Overview

There are four ways to integrate SpiceDB authorization into a RAG pipeline, from this repo. All modes perform post-retrieval, per-document authorization using SpiceDB based on a resource_id in document metadata.

1. Standalone
Directly call the authorizer in your own code for maximum flexibility outside any framework.

2. Jupyter Notebook
Drop-in wrapper for notebook workflows, enabling quick prototyping with minimal refactoring.

3. LangChain
Use first-class Runnable components (SpiceDBAuthFilter / SpiceDBAuthLambda) to integrate authorization directly into LangChain pipelines or AI workflows

4. LangGraph
Add an authorization node to a stateful LangGraph workflow to enforce permission checks within complex, multi-step graphs or AI Agents.

## Installation

```bash
# Basic installation (works standalone)
pip install spicedb-rag-auth

# With LangChain support
pip install spicedb-rag-auth[langchain]

# With LangGraph support
pip install spicedb-rag-auth[langgraph]

# With everything
pip install spicedb-rag-auth[all]

# For development
pip install -e ".[dev]"
```

## Quick Start

### Prerequisites

1. **SpiceDB running locally**:
```bash
docker run --rm -p 50051:50051 authzed/spicedb serve \
    --grpc-preshared-key "sometoken" \
    --grpc-no-tls
```

2. **Define your schema** (example):
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

3. **Set up permissions** (example):
```python
from authzed.api.v1 import WriteRelationshipsRequest, RelationshipUpdate, Relationship

# Alice can view doc1 and doc2
# Bob can view doc2 and doc3
# etc.
```

## Usage

### Standalone (Framework-Agnostic)

Perfect for Jupyter notebooks or custom RAG pipelines:

```python
from spicedb_rag_auth import SpiceDBAuthorizer

# Initialize authorizer
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    subject_type="user",
    permission="view",
    resource_id_key="article_id",  # Key in your document metadata
)

# Your existing retrieval code
documents = await vector_store.similarity_search(query, k=10)

# Filter by permissions
result = await authorizer.filter_documents(
    documents=documents,
    subject_id="alice",  # The user making the request
)

# Use authorized documents
print(f"Authorized {result.total_authorized}/{result.total_retrieved}")
authorized_docs = result.authorized_documents

# Generate response with authorized docs only
response = await llm.generate(authorized_docs, query)
```

### Jupyter Notebook Integration

Drop-in replacement for your existing Jupyter notebook RAG pipeline:

```python
from spicedb_rag_auth import SpiceDBAuthorizer

# Your existing setup
docsearch = PineconeVectorStore.from_existing_index(...)
retriever = docsearch.as_retriever(search_kwargs={"k": 4})
llm = ChatOpenAI(...)

# Replace your custom filter function with this:
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
)

async def filter_docs_with_spicedb(docs):
    """Drop-in replacement for your existing filter"""
    result = await authorizer.filter_documents(docs, subject_id="tim")
    return result.authorized_documents

# Your existing chain (NO OTHER CHANGES NEEDED!)
chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(filter_docs_with_spicedb),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)

answer = await chain.ainvoke("Your question?")
```

### LangChain Integration

Use as a Runnable in LangChain chains:

```python
from spicedb_rag_auth import SpiceDBAuthFilter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Option 1: Pass subject_id in constructor (recommended)
auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
    subject_id="alice",  # Set the user here
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

# Option 2: Pass subject_id at runtime
auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
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

# Invoke with config
answer = await chain.ainvoke(
    "Your question?",
    config={"configurable": {"subject_id": "alice"}}
)

# Or with RunnableLambda (simpler for single user)
from spicedb_rag_auth import SpiceDBAuthLambda

auth_lambda = SpiceDBAuthLambda(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
    subject_id="alice",
)

chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(auth_lambda),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)
```

### LangGraph Integration

Add as a node in your LangGraph state machine:

```python
from langgraph.graph import StateGraph, END
from spicedb_rag_auth import create_auth_node, RAGAuthState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Use the provided RAGAuthState TypedDict
graph = StateGraph(RAGAuthState)

# Define your nodes
def retrieve_node(state):
    """Retrieve documents from vector store"""
    docs = retriever.invoke(state["question"])
    return {"retrieved_documents": docs}

def generate_node(state):
    """Generate answer from authorized documents"""
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer based only on the provided context."),
        ("human", "Question: {question}\n\nContext:\n{context}")
    ])

    # Format context from authorized documents
    context = "\n\n".join([doc.page_content for doc in state["authorized_documents"]])

    # Generate answer
    llm = ChatOpenAI(model="gpt-4o-mini")
    messages = prompt.format_messages(question=state["question"], context=context)
    answer = llm.invoke(messages)

    return {"answer": answer.content}

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

# Compile and run
app = graph.compile()
result = await app.ainvoke({
    "question": "What is SpiceDB?",
    "subject_id": "alice",
})

print(result["answer"])  # The actual answer to the question

# Option 2: Extend RAGAuthState with custom fields
class MyCustomState(RAGAuthState):
    """Extend with your own fields"""
    user_preferences: dict
    conversation_history: list

graph = StateGraph(MyCustomState)
# ... add nodes and edges

# Option 3: Or use class-based node for more control
from spicedb_rag_auth import AuthorizationNode

auth_node = AuthorizationNode(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
)

graph = StateGraph(RAGAuthState)
graph.add_node("authorize", auth_node)
```

## Configuration

### Basic Configuration

```python
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint="localhost:50051",  # SpiceDB address
    spicedb_token="sometoken",                 # Pre-shared key
    resource_type="article",             # Your resource type
    subject_type="user",                 # Your subject type
    permission="view",                   # Permission to check
    resource_id_key="article_id",        # Metadata key for resource ID
)
```

### Advanced Configuration

```python
authorizer = SpiceDBAuthorizer(
    # Connection
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    use_tls=False,                       # Enable TLS if needed

    # Schema
    resource_type="article",
    subject_type="user",
    permission="view",
    resource_id_key="article_id",

    # Performance
    batch_size=10,                       # Concurrent checks per batch

    # Behavior
    fail_open=False,                     # Fail closed by default (deny on errors)
)
```

## Document Metadata Requirements

Your documents must include the resource ID in metadata:

```python
from langchain_core.documents import Document

doc = Document(
    page_content="Your content here...",
    metadata={
        "article_id": "doc123",  # Must match resource_id_key
        # ... other metadata
    }
)
```

Works with any document format that has a `.metadata` dict attribute (LangChain Documents, custom classes, etc.).

## Authorization Results

### Standalone Usage

When using `SpiceDBAuthorizer` directly, `filter_documents` returns detailed metrics:

```python
authorizer = SpiceDBAuthorizer(...)
result = await authorizer.filter_documents(docs, subject_id="alice")

print(result.authorized_documents)      # List of authorized docs
print(result.total_retrieved)           # Total docs checked
print(result.total_authorized)          # Docs that passed
print(result.authorization_rate)        # Percentage (0.0 to 1.0)
print(result.denied_resource_ids)       # List of denied IDs
print(result.check_latency_ms)          # Time spent on checks
```

### LangChain Integration

By default, `SpiceDBAuthFilter` returns only the authorized documents. To get metrics, set `return_metrics=True`:

```python
# Without metrics (default)
auth = SpiceDBAuthFilter(..., subject_id="alice")
chain = RunnableParallel({"context": retriever | auth, ...}) | prompt | llm
result = await chain.ainvoke("question")  # Returns final answer

# With metrics
auth = SpiceDBAuthFilter(..., subject_id="alice", return_metrics=True)
result = await auth.ainvoke(docs)  # Call auth directly

print(result.authorized_documents)
print(result.total_authorized)
print(result.check_latency_ms)
# ... all other metrics
```

### LangGraph Integration

Metrics are automatically available in the state under `auth_results`:

```python
graph = StateGraph(RAGAuthState)
# ... add nodes including create_auth_node()

result = await app.ainvoke({"question": "...", "subject_id": "alice"})

# Access metrics from state
print(result["auth_results"]["total_retrieved"])
print(result["auth_results"]["total_authorized"])
print(result["auth_results"]["authorization_rate"])
print(result["auth_results"]["denied_resource_ids"])
print(result["auth_results"]["check_latency_ms"])
```

## Examples

See the `examples/` directory for complete working examples:

- `standalone_example.py` - Basic usage without any framework
- `jupyter_notebook_example.py` - Integration with Jupyter notebooks
- `langchain_example.py` - LangChain integration
- More examples coming soon!

## Performance Considerations

- **Batch Processing**: Permission checks are batched and run concurrently
- **Configurable Batch Size**: Adjust `batch_size` based on your SpiceDB setup
- **Connection Reuse**: SpiceDB client is reused across checks
- **Async Operations**: All operations are async for better performance

### Benchmarks

On a local SpiceDB instance:
- ~10-20ms per batch of 10 documents
- Scales linearly with number of documents
- Network latency is the primary bottleneck

## Vector Store Compatibility

Works with any vector store that returns documents with metadata:

- ✅ Pinecone
- ✅ FAISS
- ✅ Weaviate
- ✅ Chroma
- ✅ Qdrant
- ✅ Milvus
- ✅ Any custom vector store

## Framework Compatibility

- ✅ Standalone (no framework)
- ✅ LangChain
- ✅ LangGraph
- ✅ Custom RAG pipelines
- ✅ Jupyter notebooks
- ✅ FastAPI applications

## Error Handling

### Fail Closed (Default)

By default, the authorizer fails closed - if there's an error checking permissions, access is denied:

```python
authorizer = SpiceDBAuthorizer(..., fail_open=False)
```

### Fail Open

For development or specific use cases, you can fail open:

```python
authorizer = SpiceDBAuthorizer(..., fail_open=True)
```

## Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest tests/ --cov=spicedb_rag_auth
```

## Use Cases

1. **Multi-Tenant SaaS**: Different customers see different documents
2. **Enterprise RAG**: Role-based access control for internal knowledge bases
3. **Healthcare/Legal**: Compliance-required document access controls
4. **Collaborative Platforms**: Team-based permissions for shared documents
5. **Document Management**: Fine-grained access control for sensitive information

## Comparison with Pre-Filter Approach

### Pre-Filter (Filtering at Vector Store Level)
```python
# Filter BEFORE retrieval
retriever = vectorstore.as_retriever(
    search_kwargs={
        "filter": {"article_id": {"$in": authorized_articles}}
    }
)
```

**Pros**: More efficient (It Depends ™️) fewer documents retrieved
**Cons**: Requires knowing authorized docs upfront, may miss relevant results

### Post-Filter (This Package)
```python
# Filter AFTER retrieval
docs = await retriever.retrieve(query)
authorized_docs = await authorizer.filter_documents(docs, subject_id="alice")
```

**Pros**: Gets best semantic matches first, deterministic, observable
**Cons**: May retrieve docs that get filtered out

**Recommendation**: Use post-filter when you want the best semantic matches with guaranteed authorization checks. Use pre-filter when you have the authorized document list upfront and want maximum efficiency.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License

## Related Projects

- [SpiceDB](https://github.com/authzed/spicedb) - Authorization database
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Graph-based LLM workflows