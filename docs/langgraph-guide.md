# LangGraph Integration Guide

This guide covers advanced patterns for integrating SpiceDB authorization into LangGraph workflows.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Integration Options](#integration-options)
- [Custom State](#custom-state)
- [Reusable Authorization Nodes](#reusable-authorization-nodes)
- [Visualization & Debugging](#visualization--debugging)

## Basic Usage

Add an authorization node to your LangGraph state machine:

```python
from langgraph.graph import StateGraph, END
from langchain_spicedb import create_check_permissions_node, RAGAuthState
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
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer based only on the provided context."),
        ("human", "Question: {question}\n\nContext:\n{context}")
    ])

    context = "\n\n".join([doc.page_content for doc in state["authorized_documents"]])
    llm = ChatOpenAI(model="gpt-4o-mini")
    messages = prompt.format_messages(question=state["question"], context=context)
    answer = llm.invoke(messages)

    return {"answer": answer.content}

# Add nodes
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_check_permissions_node(
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

print(result["answer"])
```

## Integration Options

The library provides three approaches for LangGraph integration, each suited for different use cases:

### Option 1: Basic Usage (Recommended for Getting Started)

Use the provided `RAGAuthState` and `create_check_permissions_node()` function. This is the **simplest approach** for basic RAG pipelines.

```python
from langchain_spicedb import create_check_permissions_node, RAGAuthState

graph = StateGraph(RAGAuthState)
graph.add_node("authorize", create_check_permissions_node(...))
```

**When to use:** Simple RAG workflows with standard state fields.

**State fields provided:**
- `question`: str - User's question
- `subject_id`: str - User ID for authorization
- `retrieved_documents`: List[Document] - Docs from retrieval
- `authorized_documents`: List[Document] - Authorized docs
- `answer`: str - Generated answer
- `auth_results`: dict - Authorization metrics

### Option 2: Extend RAGAuthState

Add custom fields to track additional state like conversation history, user preferences, or metadata.

```python
from langchain_spicedb import RAGAuthState

class ConversationalRAGState(RAGAuthState):
    """Extend with your own fields"""
    conversation_history: list  # Track previous Q&A
    user_preferences: dict      # User settings
    session_id: str            # Session tracking

graph = StateGraph(ConversationalRAGState)
# ... add nodes and edges
```

**When to use:**
- Multi-turn conversations that need history
- Personalized responses based on user preferences
- Complex workflows requiring additional context

**Example use case:** A chatbot that remembers previous questions and tailors responses based on user role (engineer vs. manager).

### Option 3: Class-Based Authorization Node

Create reusable authorization node instances that can be shared across multiple graphs or configured with custom state key mappings.

```python
from langchain_spicedb import AuthorizationNode

# Define once, reuse everywhere
article_auth = AuthorizationNode(
    spicedb_endpoint="localhost:50051",
    spicedb_token="sometoken",
    resource_type="article",
    resource_id_key="article_id",
)

video_auth = AuthorizationNode(
    resource_type="video",
    resource_id_key="video_id",
    ...
)

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

## Custom State

For production applications, you'll often use a mix of Option 2 and 3: A custom state for your workflow + reusable authZ nodes for flexibility.

```python
from langchain_spicedb import RAGAuthState, AuthorizationNode

class CustomerSupportState(RAGAuthState):
    """Custom state for customer support workflow"""
    conversation_history: list
    customer_tier: str
    sentiment_score: float

# Reusable authorization nodes
docs_auth = AuthorizationNode(resource_type="support_doc", ...)
kb_auth = AuthorizationNode(resource_type="knowledge_base", ...)

# Build graph
graph = StateGraph(CustomerSupportState)
graph.add_node("auth_docs", docs_auth)
graph.add_node("auth_kb", kb_auth)
# ... add other nodes
```

## Reusable Authorization Nodes

### Pattern: Authorization Node Factory

Create a factory function to generate configured authorization nodes:

```python
from langchain_spicedb import AuthorizationNode

def create_article_auth(spicedb_config: dict) -> AuthorizationNode:
    """Factory for article authorization nodes"""
    return AuthorizationNode(
        spicedb_endpoint=spicedb_config["endpoint"],
        spicedb_token=spicedb_config["token"],
        resource_type="article",
        resource_id_key="article_id",
        permission="view",
    )

# Use in multiple graphs
config = {"endpoint": "localhost:50051", "token": "sometoken"}
blog_auth = create_article_auth(config)
news_auth = create_article_auth(config)
```

### Pattern: Multi-Resource Authorization

Handle different resource types in a single graph:

```python
from langchain_spicedb import AuthorizationNode

# Create auth nodes for different resources
article_auth = AuthorizationNode(resource_type="article", ...)
video_auth = AuthorizationNode(resource_type="video", ...)
dataset_auth = AuthorizationNode(resource_type="dataset", ...)

# Conditional routing based on resource type
def route_by_resource_type(state):
    resource_type = state["resource_type"]
    if resource_type == "article":
        return "auth_article"
    elif resource_type == "video":
        return "auth_video"
    else:
        return "auth_dataset"

graph.add_conditional_edges("retrieve", route_by_resource_type)
graph.add_node("auth_article", article_auth)
graph.add_node("auth_video", video_auth)
graph.add_node("auth_dataset", dataset_auth)
```

## Visualization & Debugging

When teaching or debugging, you can prove the authorization node exists in the graph:

```python
from langgraph.graph import StateGraph, END
from langchain_spicedb import create_check_permissions_node, RAGAuthState

graph = StateGraph(RAGAuthState)

# Add nodes
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_check_permissions_node(...))
graph.add_node("generate", generate_node)

# Add edges
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "authorize")
graph.add_edge("authorize", "generate")
graph.add_edge("generate", END)

# Compile
app = graph.compile()
```

### Method 1: Inspect Nodes

```python
print("Nodes:", list(graph.nodes.keys()))
# Output: ['retrieve', 'authorize', 'generate']
```

### Method 2: Inspect Edges

```python
print("Edges:", graph.edges)
# Shows: retrieve → authorize → generate → END
```

### Method 3: Generate Mermaid Diagram

```python
mermaid = app.get_graph().draw_mermaid()
print(mermaid)
# Copy to https://mermaid.live to visualize
```

### Method 4: Trace Execution with Metrics

```python
result = await app.ainvoke({"question": "...", "subject_id": "alice"})

# Access authorization metrics from state
print(f"Retrieved: {result['auth_results']['total_retrieved']}")
print(f"Authorized: {result['auth_results']['total_authorized']}")
print(f"Authorization rate: {result['auth_results']['authorization_rate']:.1%}")
print(f"Denied IDs: {result['auth_results']['denied_resource_ids']}")
print(f"Latency: {result['auth_results']['check_latency_ms']:.2f}ms")
```

### Authorization Metrics in State

The authorization node automatically adds metrics to the state under the `auth_results` key:

```python
{
    "total_retrieved": 10,           # Documents retrieved
    "total_authorized": 7,           # Documents authorized
    "authorization_rate": 0.7,       # Percentage authorized
    "denied_resource_ids": ["3", "5", "8"],  # Denied doc IDs
    "check_latency_ms": 45.2,       # Permission check time
}
```

### Complete Visualization Example

See `examples/langgraph_postfilter_example.py` for a complete working example of a post-filter authorization graph with inspection and metrics.

## Advanced Patterns

### Pattern: Conditional Authorization

Only authorize if certain conditions are met:

```python
def should_authorize(state):
    """Decide if authorization is needed"""
    if state.get("skip_auth"):
        return "generate"
    return "authorize"

graph.add_conditional_edges("retrieve", should_authorize)
graph.add_node("authorize", create_check_permissions_node(...))
```

### Pattern: Fallback on Denial

Handle the case where no documents are authorized:

```python
def check_authorized_count(state):
    """Route based on authorized document count"""
    if len(state["authorized_documents"]) == 0:
        return "fallback"
    return "generate"

graph.add_conditional_edges("authorize", check_authorized_count)
graph.add_node("fallback", fallback_node)
graph.add_node("generate", generate_node)
```

### Pattern: Multi-Stage Authorization

Check permissions at multiple stages:

```python
# Stage 1: Coarse-grained check (fast)
graph.add_node("pre_auth", create_check_permissions_node(permission="view"))

# Stage 2: Fine-grained check (detailed)
graph.add_node("fine_auth", create_check_permissions_node(permission="read_sensitive"))

graph.add_edge("retrieve", "pre_auth")
graph.add_edge("pre_auth", "fine_auth")
graph.add_edge("fine_auth", "generate")
```

## Best Practices

1. **Use RAGAuthState for Simple Workflows**: Start with the provided state and extend only when needed.

2. **Reuse Authorization Nodes**: Create auth nodes once and reuse them across graphs to maintain consistency.

3. **Monitor Authorization Metrics**: Always check `auth_results` in production to detect authorization issues.

4. **Fail Closed by Default**: Keep `fail_open=False` in production to ensure security.

5. **Test Authorization Logic**: Write unit tests that verify your authorization nodes work correctly.

6. **Document State Requirements**: Clearly document what state fields your nodes expect and produce.

## Troubleshooting

### Issue: Authorization node doesn't filter documents

**Solution**: Verify the state includes:
- `retrieved_documents`: List of documents from retrieval
- `subject_id`: User ID for authorization

### Issue: State type errors

**Solution**: Ensure your custom state extends `RAGAuthState`:
```python
class MyState(RAGAuthState):  # Must extend RAGAuthState
    custom_field: str
```

### Issue: Authorization metrics not available

**Solution**: Check that you're accessing `auth_results` from the final state:
```python
result = await app.ainvoke(...)
metrics = result["auth_results"]  # Available after execution
```

## Next Steps

- See [Configuration Guide](configuration.md) for all configuration options
- See [Examples](../examples/README.md) for complete working examples
- See [Performance Guide](performance.md) for optimization tips
