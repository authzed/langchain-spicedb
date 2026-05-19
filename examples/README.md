# langchain-spicedb Examples

Complete guide to using langchain-spicedb for adding fine-grained authorization to your LangChain applications.

## Table of Contents

- [What is langchain-spicedb?](#what-is-langchain-spicedb)
- [Quick Start](#quick-start) - Get running in 5 minutes
- [Examples Overview](#examples-overview)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## What is langchain-spicedb?

langchain-spicedb integrates [SpiceDB](https://authzed.com) authorization into [LangChain](https://python.langchain.com/), enabling you to build RAG applications and AI agents that respect fine-grained permissions.

> 💡 **New to langchain-spicedb?** See the [main README](../README.md) for a quick overview and installation guide, or check the [configuration documentation](../docs/configuration.md) for detailed setup options.

**Key Features:**
- ✓ Authorization-aware document retrieval for RAG
- ✓ Permission checking tools for AI agents
- ✓ Works with any vector store (Pinecone, Chroma, FAISS, etc.)
- ✓ Efficient bulk permission checks using SpiceDB's native API
- ✓ Async/sync support
- ✓ Production-ready with TLS and fail-open modes

**Why use it?**

In multi-tenant applications, healthcare systems, or any environment with sensitive data, you need to ensure users only access documents they're authorized to see. langchain-spicedb makes this transparent:

```python
# Without authorization - everyone sees everything
retriever = vector_store.as_retriever()
docs = retriever.invoke("query")  # Returns all matches

# With authorization - automatic filtering
retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),
    subject_id=user_id,
    resource_type="article",
    permission="view",
    ...
)
docs = retriever.invoke("query")  # Returns only authorized documents
```

---

## Quick Start

Get up and running in 5 minutes:

### 1. Start SpiceDB (1 minute)

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

Keep this running in a terminal window.

### 2. Install zed CLI (Optional but recommended)

```bash
# macOS
brew install authzed/tap/zed

# Linux
curl -L https://github.com/authzed/zed/releases/latest/download/zed-linux-amd64 -o zed
chmod +x zed
sudo mv zed /usr/local/bin/
```

Configure zed:

```bash
zed context set local localhost:50051 somerandomkeyhere --insecure
```

### 3. Create Schema (1 minute)

Create a file `schema.zed`:

```zed
definition user {}

definition article {
    relation viewer: user
    relation editor: user
    permission view = viewer + editor
    permission edit = editor
}
```
This schema defines:
- **user**: Represents people in your system
- **article**: Represents documents/content
- **viewer relation**: User can see the article
- **editor relation**: User can modify the article
- **view permission**: Granted to viewers and editors
- **edit permission**: Granted to editors only

Apply it:

```bash
zed schema write schema.zed
```

### 4. Create Test Relationships (1 minute)

```bash
# Tim can view articles 123 and 456
zed relationship create article:123 viewer user:tim
zed relationship create article:456 viewer user:tim

# Alice can view article 789 and edit article 123
zed relationship create article:789 viewer user:alice
zed relationship create article:123 editor user:alice
```

**What this means:**
- Tim has **view** permission on articles 123 and 456
- Alice has **view** permission on article 789
- Alice has **edit** permission on article 123 (which also grants view)

### 5. Set Environment Variables (30 seconds)

Create a `.env` file in the examples directory (copy from .env.example):

```bash
cp .env.example .env
```

Then edit `.env` with your values:

```bash
# SpiceDB Configuration
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_TOKEN=somerandomkeyhere

# User to test as
SUBJECT_ID=tim

# OpenAI API Key (optional, for full RAG demos)
OPENAI_API_KEY=sk-your-key-here
```

### 6. Install Package (1 minute)

```bash
pip install -e ".[all]"
```

### 7. Run Examples (1 minute)

```bash
# No OpenAI API key needed for basic demos
python examples/retriever_example.py
python examples/tool_example.py

# With OpenAI for full RAG demo (optional)
export OPENAI_API_KEY=sk-...
python examples/retriever_example.py
```

---

## Examples Overview

### Example Files

```
examples/
├── README.md                          # This file
├── retriever_example.py               # SpiceDBRetriever demo
├── tool_example.py                    # SpiceDBPermissionTool demo
├── langchain_example.py               # Custom chains with SpiceDBAuthFilter
└── langgraph_postfilter_example.py # LangGraph post-filter authorization
```

### 1. SpiceDBRetriever Example (`retriever_example.py`)

**What it does:** Automatically filters retrieved documents based on user permissions before passing them to an LLM.

**Use cases:**
- Multi-tenant SaaS (users only see their organization's data)
- Healthcare (doctors only access assigned patient records)
- E-commerce (different docs for free/premium customers)

**Key features:**
- Wraps any LangChain retriever
- Transparent authorization filtering
- Works with vector stores (Pinecone, Chroma, FAISS)
- Single bulk API call for all permission checks
- Runs without OpenAI for demos

**Run it:**

```bash
# Basic demo (no API key needed)
python examples/retriever_example.py

# Full RAG demo
export OPENAI_API_KEY=sk-...
python examples/retriever_example.py

# Test different users
export SUBJECT_ID=alice
python examples/retriever_example.py
```

**Expected output:**

```
Documents from base retriever (before authorization): 4
  - Python Basics (ID: 123)
  - JavaScript Guide (ID: 456)
  - ML Introduction (ID: 789)
  - SpiceDB Overview (ID: 101)

Documents after SpiceDB authorization filter (user: tim): 2
  ✓ Python Basics (ID: 123)
  ✓ JavaScript Guide (ID: 456)

SpiceDB filtered out 2 unauthorized documents
```

### 2. SpiceDBPermissionTool Example (`tool_example.py`)

**What it does:** Gives AI agents the ability to check permissions before taking actions.

**Use cases:**
- Content management (agent checks edit permissions)
- Admin panels (agent verifies admin rights)
- Document workflows (agent checks approval permissions)

**Key features:**
- Single permission checks
- Bulk permission checks (multiple resources at once)
- Works with LangChain agents
- Direct usage without agents
- Runs without OpenAI for basic demos

**Run it:**

```bash
# Basic demo (no API key needed)
python examples/tool_example.py

# With agent (requires OpenAI)
export OPENAI_API_KEY=sk-...
python examples/tool_example.py
```

**Expected output:**

```
Agent Response:
User tim CAN view article 123. They have the necessary 'view' permission.

Bulk check result:
User tim can access: 123, 456
User tim cannot access: 789
```

### 3. LangGraph Integration Example (`langgraph_postfilter_example.py`)

**What it does:** Demonstrates how to add authorization as a node in LangGraph workflows with state management and observability.

**Use cases:**
- Complex multi-step agentic workflows
- Workflows requiring authorization metrics and observability
- State-based applications where you need to track authorization decisions
- Production LangGraph applications with permission-aware flows

**Key features:**
- Authorization as a graph node using `create_auth_node()`
- Authorization metrics available in state (`auth_results`)
- Works with `RAGAuthState` for typed state management
- Shows how to integrate authorization into LangGraph's state machine

**Run it:**

```bash
# Works without OpenAI - shows graph structure and flow
python examples/langgraph_postfilter_example.py

# Test different users
export SUBJECT_ID=tim
python examples/langgraph_postfilter_example.py
```

**Expected output:**

```
METHOD 1: Inspect Graph Nodes
Nodes: ['retrieve', 'authorize', 'generate']
✅ Authorization node EXISTS in the graph

METHOD 2: Inspect Graph Edges (Execution Flow)
Execution flow:
  __start__ → retrieve
  retrieve → authorize
  authorize → generate
  generate → __end__

METHOD 6: Authorization Metrics
  Total retrieved:     3
  Total authorized:    2
  Authorization rate:  66.7%
  Check latency:       12.34ms
```

**What it demonstrates:**
- Graph structure inspection and visualization
- Live execution tracing with state updates
- Authorization metrics for monitoring and debugging
- Mermaid diagram generation for documentation

Read [this doc](https://github.com/authzed/langchain-spicedb/blob/main/docs/langgraph-guide.md) for more comprehensive examples on using SpiceDB in LangGraph.

### 4. Custom Chain Example (`langchain_example.py`)

Low-level authorization filtering using `SpiceDBAuthFilter` directly in a LangChain Expression Language (LCEL) chain.

**Note:** For most use cases, prefer `SpiceDBRetriever` (example 1)

---

## Troubleshooting

Having issues? The [Configuration Guide](../docs/configuration.md#troubleshooting) has comprehensive troubleshooting steps for:

- **SpiceDB Connection Errors** - Connectivity and authentication issues
- **No Documents Returned** - Permission and relationship problems
- **Schema Errors** - Type and permission mismatches
- **Invalid Resource IDs** - ID format validation
- **AsyncIO Errors** - Async/sync usage patterns
- **Port Conflicts** - Docker port management
- **Missing Metadata** - Document metadata requirements

**Quick diagnostic:**
```bash
# Verify SpiceDB is running
docker ps | grep spicedb

# Test connection
zed permission check article:123 view user:tim

# Check environment
echo $SPICEDB_ENDPOINT
echo $SPICEDB_TOKEN
```

For detailed solutions, see the [Troubleshooting section](../docs/configuration.md#troubleshooting) in the configuration guide.

---

## Advanced Configuration

For production deployments and advanced use cases, see the [Configuration Guide](../docs/configuration.md#advanced-configuration) which covers:

- **TLS/SSL Configuration** - Secure production deployments
- **Fail-Open vs Fail-Closed** - Availability vs security trade-offs
- **Bulk Permission Checks** - Performance optimization (automatic)
- **Custom Subject Types** - Service accounts, organizations, etc.
- **Environment Variables** - Configuration management
- **Logging and Debugging** - Troubleshooting tools
- **Production Best Practices** - Complete production setup

**Quick production setup:**

```python
retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),
    spicedb_endpoint=os.getenv("SPICEDB_ENDPOINT"),
    spicedb_token=os.getenv("SPICEDB_TOKEN"),
    subject_id=os.getenv("USER_ID"),
    resource_type="article",
    resource_id_key="article_id",
    permission="view",
    use_tls=True,      # Enable for production
    fail_open=False,   # Fail closed (secure)
)
```

See the [complete configuration reference](../docs/configuration.md) for all options and detailed examples.

---

## Additional Resources

- **LangChain Documentation**: https://python.langchain.com/
- **SpiceDB Documentation**: https://authzed.com/docs
- **SpiceDB Playground**: https://play.authzed.com (interactive schema design)
- **langchain-spicedb GitHub**: https://github.com/authzed/langchain-spicedb
- **SpiceDB Discord**: https://discord.gg/spicedb
- **LangChain Discord**: https://discord.gg/langchain

---

## Next Steps

1. ✅ Complete Quick Start
2. Run examples with your data
3. Design your SpiceDB schema for your use case
4. Integrate into your application
5. Deploy with SpiceDB Cloud for production

## Questions or Issues?

- Open an issue: https://github.com/authzed/langchain-spicedb/issues
- Check SpiceDB docs: https://authzed.com/docs
- Join Discord communities (links above)

---

**Happy building with langchain-spicedb! 🚀**
