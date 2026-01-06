# langchain-spicedb Examples

This directory contains example scripts demonstrating how to use langchain-spicedb to add fine-grained authorization to your LangChain applications.

## Overview

langchain-spicedb provides three main integration patterns:

1. **SpiceDBRetriever** - Authorization-aware document retrieval for RAG pipelines
2. **SpiceDBPermissionTool** - Permission checking tools for agentic workflows
3. **SpiceDBAuthLambda** - Low-level authorization filter for custom chains

## Examples

### 1. SpiceDBRetriever Example (`retriever_example.py`)

**Use Case**: Automatically filter retrieved documents based on user permissions in RAG applications.

```bash
python examples/retriever_example.py
```

**What it demonstrates:**
- Wrapping any LangChain retriever with authorization
- Automatic document filtering before LLM processing
- Synchronous and asynchronous retrieval
- Batch retrieval with authorization
- RAG chain with permission-filtered context

**Key Features:**
- Works with any vector store (Pinecone, Chroma, FAISS, etc.)
- Zero changes to existing retriever code
- Transparent authorization filtering
- Works without OpenAI API key (basic demo mode)

**Example Output:**
```
Documents from base retriever (before authorization):
  - Python Basics (ID: 123)
  - JavaScript Guide (ID: 456)
  - ML Introduction (ID: 789)
  - SpiceDB Overview (ID: 101)

Documents after SpiceDB authorization filter (user: tim):
  ✓ Python Basics (ID: 123)
  ✓ JavaScript Guide (ID: 456)

SpiceDB filtered out 2 unauthorized document(s)
```

### 2. SpiceDBPermissionTool Example (`tool_example.py`)

**Use Case**: Give LangChain agents the ability to check permissions before taking actions.

```bash
python examples/tool_example.py
```

**What it demonstrates:**
- Single permission checks with `SpiceDBPermissionTool`
- Bulk permission checks with `SpiceDBBulkPermissionTool`
- Using tools with LangChain agents
- Direct tool usage without agents
- Multi-permission workflow patterns

**Key Features:**
- Tool-use compatible (works with function calling models)
- Both single and bulk permission checking
- Synchronous and asynchronous support
- Works standalone or with agents
- Can run without OpenAI API key (direct usage mode)

**Example Output:**
```
Agent Response:
Based on the permission check, user tim CAN view article 123. They have the
necessary 'view' permission for this resource.

Bulk Check Result:
User tim can access: 123, 456
User tim cannot access: 789
```

### 3. LangChain Chain Example (`langchain_example.py`)

**Use Case**: Custom authorization filtering using `SpiceDBAuthLambda` in chains.

```bash
python examples/langchain_example.py
```

**What it demonstrates:**
- Low-level authorization filtering with `RunnableLambda`
- Custom chain composition with authorization
- Integration with LangChain LCEL (LangChain Expression Language)

**Note**: For most use cases, prefer `SpiceDBRetriever` over `SpiceDBAuthLambda` as it provides the same functionality with better ergonomics.

### 4. LangGraph Visualization Example (`langgraph_visualization_example.py`)

**Use Case**: Authorization in LangGraph stateful workflows.

```bash
python examples/langgraph_visualization_example.py
```

**What it demonstrates:**
- SpiceDB authorization in LangGraph nodes
- Stateful workflows with authorization
- Graph visualization with authorization steps

## Setup

### 1. Install Dependencies

```bash
# Install the package with all dependencies
pip install -e ".[all]"

# Or install specific dependencies
pip install -e ".[examples]"  # Just example dependencies
pip install langchain-openai  # For LLM examples
```

### 2. Set Up SpiceDB

You need a running SpiceDB instance. Choose one option:

#### Option A: Local SpiceDB with Docker

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

#### Option B: SpiceDB Cloud

1. Sign up at https://app.authzed.com
2. Create a permission system
3. Get your endpoint and token

### 3. Configure SpiceDB Schema

Create a schema file `schema.zed`:

```zed
definition user {}

definition article {
    relation viewer: user
    relation editor: user

    permission view = viewer + editor
    permission edit = editor
}
```

Apply the schema:

```bash
# Using zed CLI
zed schema write schema.zed

# Or via API
curl -X POST http://localhost:50051/v1/schema/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -d @schema.zed
```

### 4. Create Test Relationships

```bash
# Using zed CLI
zed relationship create article:123 viewer user:tim
zed relationship create article:456 viewer user:tim
zed relationship create article:789 viewer user:alice

# Or via API
curl -X POST http://localhost:50051/v1/relationships/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -d '{
    "updates": [
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "123"},
          "relation": "viewer",
          "subject": {"object": {"objectType": "user", "objectId": "tim"}}
        }
      }
    ]
  }'
```

### 5. Configure Environment Variables

Create a `.env` file in the examples directory:

```bash
# SpiceDB Configuration (required)
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_TOKEN=somerandomkeyhere

# For LLM examples (optional)
OPENAI_API_KEY=sk-...

# Test different users (optional)
SUBJECT_ID=tim
```

## Running Examples

### Quick Start (No OpenAI API Key Required)

```bash
# Basic retriever demo
python examples/retriever_example.py

# Basic tool demo
python examples/tool_example.py
```

These examples will run in demo mode, showing authorization filtering without requiring an OpenAI API key.

### Full Examples (With OpenAI)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-...

# Run retriever example with RAG
python examples/retriever_example.py

# Run agent example with permission tools
python examples/tool_example.py

# Run custom chain example
python examples/langchain_example.py
```

### Testing Different Users

```bash
# Test as user 'alice'
export SUBJECT_ID=alice
python examples/retriever_example.py

# Test as user 'bob' (likely no permissions)
export SUBJECT_ID=bob
python examples/retriever_example.py
```

## Example Use Cases

### E-Commerce Platform

**Scenario**: Different customer tiers (free, premium, enterprise) have access to different product documentation.

```python
# Premium customers can access all docs
retriever = SpiceDBRetriever(
    base_retriever=pinecone_retriever,
    subject_id=user_id,
    subject_type="user",
    resource_type="documentation",
    resource_id_key="doc_id",
    permission="view",
    ...
)

docs = retriever.invoke("How do I use the API?")
# Only returns docs the user has permission to see
```

### Healthcare System

**Scenario**: Doctors can only retrieve patient records they're assigned to.

```python
retriever = SpiceDBRetriever(
    base_retriever=medical_records_retriever,
    subject_id=doctor_id,
    subject_type="doctor",
    resource_type="patient_record",
    resource_id_key="record_id",
    permission="read",
    ...
)

records = retriever.invoke("Show diabetic patients")
# Automatically filtered by doctor's patient assignments
```

### Multi-Tenant SaaS

**Scenario**: Users can only access documents within their organization.

```python
retriever = SpiceDBRetriever(
    base_retriever=company_docs_retriever,
    subject_id=user_id,
    subject_type="user",
    resource_type="document",
    resource_id_key="document_id",
    permission="view",
    ...
)

docs = retriever.invoke("company policies")
# Only returns docs from user's organization
```

### Content Management System

**Scenario**: Agent checks if user can edit before performing operations.

```python
agent = create_tool_calling_agent(
    llm=llm,
    tools=[
        SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            ...
        )
    ],
    prompt=prompt
)

# Agent will check permissions before editing
result = agent.invoke({
    "input": "Can I edit article 123? If yes, update the title."
})
```

## Architecture Patterns

### Pattern 1: Authorization at Retrieval Time (Recommended)

```python
# Authorization happens during document retrieval
retriever = SpiceDBRetriever(base_retriever=vector_store)
docs = retriever.invoke(query)  # Already filtered

chain = retriever | prompt | llm
```

**Pros:**
- Simple and transparent
- Works with any vector store
- Minimal code changes

**Cons:**
- Additional latency per query
- May retrieve unauthorized docs unnecessarily

### Pattern 2: Pre-Filtering with Bulk Checks

```python
# Get all relevant doc IDs first
candidate_docs = vector_store.similarity_search(query)
doc_ids = [doc.metadata["id"] for doc in candidate_docs]

# Bulk check permissions
tool = SpiceDBBulkPermissionTool(...)
authorized_ids = tool.invoke({
    "subject_id": user_id,
    "resource_ids": ",".join(doc_ids),
    "permission": "view"
})

# Filter docs
authorized_docs = [d for d in candidate_docs if d.metadata["id"] in authorized_ids]
```

**Pros:**
- Single SpiceDB call for multiple docs
- Efficient for large result sets

**Cons:**
- More complex code
- Still retrieves unauthorized docs

### Pattern 3: Agent-Driven Authorization

```python
# Agent decides when to check permissions
agent = create_tool_calling_agent(
    llm=llm,
    tools=[permission_tool, other_tools],
    prompt="Check permissions before taking actions"
)
```

**Pros:**
- Flexible, context-aware authorization
- Agent can explain permission decisions
- Works for complex workflows

**Cons:**
- LLM must be reliable about checking permissions
- Additional LLM calls
- Requires function calling support

## Performance Considerations

### Caching

```python
# Enable caching for repeated permission checks
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())
```

### Batch Operations

```python
# Use batch operations when checking multiple queries
queries = ["query1", "query2", "query3"]
results = await retriever.abatch(queries)  # Efficient parallel checks
```

### Fail-Open Mode

```python
# Allow access on SpiceDB errors (use cautiously!)
retriever = SpiceDBRetriever(
    ...,
    fail_open=True  # Returns all docs if SpiceDB is unavailable
)
```

## Troubleshooting

### SpiceDB Connection Errors

```
Error: failed to connect to SpiceDB
```

**Solution:**
- Verify SpiceDB is running: `curl http://localhost:50051`
- Check `SPICEDB_ENDPOINT` environment variable
- Verify token: `SPICEDB_TOKEN` should match SpiceDB configuration

### No Documents Returned

```
Documents after authorization: 0
```

**Solution:**
- Check relationships exist: `zed relationship read article:123`
- Verify subject_id matches: Check `SUBJECT_ID` environment variable
- Test permission: `zed permission check article:123 view user:tim`

### Schema Errors

```
Error: relation not found
```

**Solution:**
- Verify schema is applied: `zed schema read`
- Check resource_type and permission names match schema
- Ensure relation names are correct (e.g., "viewer" not "view")

## Additional Resources

- [LangChain Documentation](https://python.langchain.com/)
- [SpiceDB Documentation](https://authzed.com/docs)
- [langchain-spicedb GitHub](https://github.com/yourusername/langchain-spicedb)
- [SpiceDB Playground](https://play.authzed.com)

## Contributing

Found an issue or have a suggestion for a new example? Please open an issue or submit a pull request!
