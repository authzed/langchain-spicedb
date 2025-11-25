# SpiceDB RAG Authorization

Authorization library for RAG (Retrieval-Augmented Generation) pipelines using SpiceDB. Designed for LangChain and LangGraph integrations with support for any vector store (Pinecone, FAISS, Weaviate, Chroma, etc.).

**NOTE:** This is very much in alpha mode and is intended as a learning exercise rather than a production deployment. I've tested it against the `langchain_example.py` and also the SpiceDB - RAG example in the `authzed/workshops` [repo here](https://github.com/authzed/workshops/blob/main/secure-rag-pipelines/01-rag.ipynb)

## Features

- **LangChain & LangGraph Integration**: First-class support for modern LLM frameworks
- **Vector Store Agnostic**: Compatible with Pinecone, FAISS, Weaviate, Chroma, and more
- **Post-Filter Authorization**: Filters retrieved documents based on SpiceDB permissions
- **Batch Processing**: Optimized concurrent permission checks for performance
- **Observable**: Returns detailed metrics about authorization decisions
- **Type-Safe**: Full type hints for better IDE support
- **Async by Default**: Built for high-performance async operations

## Why This Package?

Most RAG pipelines retrieve documents without considering user permissions. This package solves that by:

1. **Post-retrieval filtering**: Retrieve best semantic matches first, then filter by permissions
2. **Deterministic authorization**: Every document is checked against SpiceDB before being used
3. **Framework integration**: Native LangChain and LangGraph components for seamless integration
4. **Vector store agnostic**: Not tied to any specific vector database

## Overview

This library provides two ways to integrate SpiceDB authorization into RAG pipelines. Both modes perform post-retrieval, per-document authorization using SpiceDB based on a resource_id in document metadata.

1. **LangChain Integration**
Use first-class Runnable components (SpiceDBAuthFilter / SpiceDBAuthLambda) to integrate authorization directly into LangChain pipelines or AI workflows

2. **LangGraph Integration**
Add an authorization node to a stateful LangGraph workflow to enforce permission checks within complex, multi-step graphs or AI Agents.

## Installation

```bash
# With LangChain support
pip install spicedb-rag-auth[langchain]

# With LangGraph support
pip install spicedb-rag-auth[langgraph]

# With both LangChain and LangGraph
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

### LangChain Integration

Use as a Runnable in LangChain chains.

```python
from spicedb_rag_auth import SpiceDBAuthFilter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Initialize auth filter (no subject_id yet)
auth = SpiceDBAuthFilter(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
)

# Build your chain once
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

# Different user, same chain
answer = await chain.ainvoke(
    "Another question?",
    config={"configurable": {"subject_id": "bob"}}
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

### Understanding LangGraph Integration Options

The library provides three approaches for LangGraph integration, each suited for different use cases:

#### **Option 1: Basic Usage** (shown in main example above)
Use the provided `RAGAuthState` and `create_auth_node()` function. This is the **simplest approach** for basic RAG pipelines.

**When to use:** Simple RAG workflows with standard state fields.

#### **Option 2: Extend RAGAuthState**
Add custom fields to track additional state like conversation history, user preferences, or metadata.

```python
class ConversationalRAGState(RAGAuthState):
    conversation_history: list  # Track previous Q&A
    user_preferences: dict      # User settings
    session_id: str            # Session tracking
```

**When to use:**
- Multi-turn conversations that need history
- Personalized responses based on user preferences
- Complex workflows requiring additional context

**Example use case:** A chatbot that remembers previous questions and tailors responses based on user role (engineer vs. manager).

#### **Option 3: Class-Based AuthorizationNode**
Create reusable authorization node instances that can be shared across multiple graphs or configured with custom state key mappings.

```python
# Define once, reuse everywhere
article_auth = AuthorizationNode(resource_type="article", ...)
video_auth = AuthorizationNode(resource_type="video", ...)

# Use in multiple graphs
blog_graph.add_node("auth", article_auth)
media_graph.add_node("auth", video_auth)
learning_graph.add_node("auth_articles", article_auth)  # Reuse!
```

**When to use:**
- Multiple graphs need the same authorization logic
- Your state uses different key names than the defaults
- Building testable code (easy to swap prod/test instances)
- Team collaboration (security team provides authZ nodes)

**Example use case:** A multi-resource platform (articles, videos, code snippets) where each resource type has its own auth node that's reused across different workflows.

For production applications, you'll often use a mix of Option 2 and 3: A custom state for your workflow + reusable authZ nodes for flexibility.

```python
class CustomerSupportState(RAGAuthState):
    conversation_history: list
    customer_tier: str
    sentiment_score: float

docs_auth = AuthorizationNode(resource_type="support_doc", ...)
kb_auth = AuthorizationNode(resource_type="knowledge_base", ...)

graph = StateGraph(CustomerSupportState)
graph.add_node("auth_docs", docs_auth)
graph.add_node("auth_kb", kb_auth)
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

## Visualizing the LangGraph (Teaching & Debugging)

When teaching or debugging, you can prove the authorization node exists in the graph:

```python
from langgraph.graph import StateGraph, END
from spicedb_rag_auth import create_auth_node, RAGAuthState

graph = StateGraph(RAGAuthState)

# Add nodes
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_auth_node(...))
graph.add_node("generate", generate_node)

# Add edges
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "authorize")
graph.add_edge("authorize", "generate")
graph.add_edge("generate", END)

# Compile
app = graph.compile()

# Method 1: Inspect nodes
print("Nodes:", list(graph.nodes.keys()))
# Output: ['retrieve', 'authorize', 'generate']

# Method 2: Inspect edges (execution flow)
print("Edges:", graph.edges)
# Shows: retrieve → authorize → generate → END

# Method 3: Generate Mermaid diagram
mermaid = app.get_graph().draw_mermaid()
print(mermaid)
# Copy to https://mermaid.live to visualize

# Method 4: Trace execution with metrics
result = await app.ainvoke({"question": "...", "subject_id": "alice"})
print(f"Retrieved: {result['auth_results']['total_retrieved']}")
print(f"Authorized: {result['auth_results']['total_authorized']}")
# Proves authorization node executed
```

See `examples/langgraph_visualization_example.py` for a complete demonstration with 7 different methods to prove and visualize the authorization node.

## Examples

See the `examples/` directory for complete working examples:

- `langchain_example.py` - LangChain integration
- `langgraph_visualization_example.py` - **Visualizing and proving the authorization node**

## Performance Considerations

- **Batch Processing**: Permission checks are batched and run concurrently
- **Configurable Batch Size**: Adjust `batch_size` based on your SpiceDB setup
- **Connection Reuse**: SpiceDB client is reused across checks
- **Async Operations**: All operations are async for better performance


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

- ✅ LangChain
- ✅ LangGraph

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

**Pros**: More efficient (It Depends ™️), fewer documents retrieved 
**Cons**: Requires knowing authorized docs upfront, may miss relevant results, `LookupResources` API in SpiceDB can be computationally expensive depending on the number of relationships, shape of schema etc.

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