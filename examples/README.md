# langchain-spicedb Examples

Complete guide to using langchain-spicedb for adding fine-grained authorization to your LangChain applications.

## Table of Contents

- [Quick Start](#quick-start) - Get running in 5 minutes
- [What is langchain-spicedb?](#what-is-langchain-spicedb)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration) - Using .env file (recommended)
- [SpiceDB Setup](#spicedb-setup)
- [Examples Overview](#examples-overview)
- [Running Examples](#running-examples)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

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

## What is langchain-spicedb?

langchain-spicedb integrates [SpiceDB](https://authzed.com) authorization into [LangChain](https://python.langchain.com/), enabling you to build RAG applications and AI agents that respect fine-grained permissions.

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

## Installation

### Install langchain-spicedb

```bash
# From PyPI (when published)
pip install langchain-spicedb

# Or from source
git clone https://github.com/sohanmaheshwar/spicedb-rag-authorization/tree/langchain
cd langchain-spicedb
pip install -e ".[all]"
```

### Install Example Dependencies

```bash
# For basic examples (no LLM)
pip install -e ".[dev]"

# For full RAG examples with OpenAI
pip install langchain-openai python-dotenv
```

---

### Configure Schema

Create `schema.zed`:

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

**Apply the schema:**

```bash
# With zed CLI
zed schema write schema.zed

# Or with curl
curl -X POST http://localhost:50051/v1/schema/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -H "Content-Type: application/json" \
  -d '{
    "schema": "definition user {}\n\ndefinition article {\n    relation viewer: user\n    relation editor: user\n    permission view = viewer + editor\n    permission edit = editor\n}"
  }'
```

### Create Test Relationships

These relationships define who can access what:

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

**Verify permissions:**

```bash
# Should return true
zed permission check article:123 view user:tim
zed permission check article:456 view user:tim
zed permission check article:789 view user:alice
zed permission check article:123 edit user:alice

# Should return false
zed permission check article:789 view user:tim
zed permission check article:456 edit user:alice
```

---

## Examples Overview

### Example Files

```
examples/
├── README.md                          # This file
├── retriever_example.py               # SpiceDBRetriever demo
├── tool_example.py                    # SpiceDBPermissionTool demo
├── langchain_example.py               # Custom chains with SpiceDBAuthLambda
└── langgraph_visualization_example.py # LangGraph integration
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

### 3. Custom Chain Example (`langchain_example.py`)

Low-level authorization filtering using `SpiceDBAuthLambda` with LangChain Expression Language (LCEL).

**Note:** For most use cases, prefer `SpiceDBRetriever` which provides the same functionality with better ergonomics.

---

## Running Examples

### Without OpenAI API Key

The examples include demo modes that work without an API key:

```bash
python examples/retriever_example.py
python examples/tool_example.py
```

These will:
- Show document filtering in action
- Demonstrate permission checks
- Display before/after authorization results
- Skip LLM-based Q&A

### With OpenAI API Key

For full RAG demonstrations:

```bash
export OPENAI_API_KEY=sk-...
python examples/retriever_example.py
python examples/tool_example.py
```

These will:
- Include LLM-based question answering
- Show agent reasoning
- Demonstrate permission-aware responses

### Testing Different Users

To test different users, edit the `SUBJECT_ID` in your `.env` file:

```bash
# Edit .env file
SUBJECT_ID=alice  # Change from 'tim' to 'alice'
```

Then run the examples:

```bash
# Test as Alice (can view 789, edit 123)
python examples/retriever_example.py

# Test as Bob (no permissions)
# Edit .env: SUBJECT_ID=bob
python examples/retriever_example.py
```

**Alternative:** You can also override temporarily via terminal export (less secure):

```bash
SUBJECT_ID=alice python examples/retriever_example.py
```

### Expected Results by User

**User: tim**
- ✓ Can view articles 123, 456
- ✗ Cannot view article 789
- ✗ Cannot edit any articles

**User: alice**
- ✓ Can view articles 123, 789
- ✓ Can edit article 123
- ✗ Cannot view article 456

---

## Use Cases

### Multi-Tenant SaaS

**Scenario:** Different customer organizations should only access their own data.

```python
retriever = SpiceDBRetriever(
    base_retriever=vector_store.as_retriever(),
    subject_id=user_id,
    subject_type="user",
    resource_type="document",
    resource_id_key="doc_id",
    permission="view",
    spicedb_endpoint="grpc.authzed.com:443",
    spicedb_token=os.getenv("SPICEDB_TOKEN"),
    use_tls=True,
)

# Automatically filters to user's organization
docs = retriever.invoke("company policies")
```

### Healthcare System

**Scenario:** Doctors can only retrieve patient records they're assigned to.

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

records = retriever.invoke("diabetic patients")
# Automatically filtered by doctor's patient assignments
```

### Content Management System

**Scenario:** Agent checks if user can edit before performing operations.

```python
from langchain.agents import create_tool_calling_agent

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

---

## Troubleshooting

### SpiceDB Connection Errors

**Error:** `failed to connect to SpiceDB`

**Solutions:**
1. Verify SpiceDB is running:
   ```bash
   docker ps | grep spicedb
   ```
2. Check environment variables:
   ```bash
   echo $SPICEDB_ENDPOINT
   echo $SPICEDB_TOKEN
   ```
3. Test connection:
   ```bash
   zed permission check article:123 view user:tim
   ```

### No Documents Returned

**Error:** `Documents after authorization: 0`

**Solutions:**
1. Verify relationships exist:
   ```bash
   zed relationship read article:123
   ```
2. Check user ID matches:
   ```bash
   echo $SUBJECT_ID
   ```
3. Test permission directly:
   ```bash
   zed permission check article:123 view user:tim
   ```

### Schema/Relation Errors

**Error:** `relation not found` or `permission not found`

**Solutions:**
1. Verify schema is applied:
   ```bash
   zed schema read
   ```
2. Check resource type and permission names match your schema
3. Ensure relation names are correct (e.g., "viewer" not "view")

### Invalid Resource ID Error

**Error:** `invalid ObjectReference.ObjectId: value does not match regex pattern`

**Cause:** Resource ID contains invalid characters or spaces

**Solution:** Ensure resource IDs:
- Contain only alphanumeric characters, hyphens, underscores
- Don't include spaces or special characters
- Examples: "123", "article-456", "doc_id_789" ✓
- Bad examples: "article 123", "doc@456" ✗

### AsyncIO Runtime Error

**Error:** `asyncio.run() cannot be called from a running event loop`

**Solution:** Use `await` with `ainvoke()` instead of `invoke()` in async functions:

```python
# Wrong (in async function)
result = tool.invoke({...})

# Correct (in async function)
result = await tool.ainvoke({...})
```

### Port Already in Use

**Error:** `bind: address already in use`

**Solution:** Stop existing SpiceDB or use different port:

```bash
# Stop existing container
docker stop $(docker ps -q --filter ancestor=authzed/spicedb)

# Or use different port
docker run --rm -p 50052:50051 ...
# Then: export SPICEDB_ENDPOINT=localhost:50052
```

---

## Advanced Configuration

### TLS for Production

```python
retriever = SpiceDBRetriever(
    ...,
    use_tls=True,  # Enable TLS
)
```

Start SpiceDB with TLS:

```bash
docker run --rm -p 50051:50051 \
  -v $(pwd)/tls:/tls \
  authzed/spicedb serve \
  --grpc-preshared-key "your-token" \
  --grpc-tls-cert-path /tls/server.crt \
  --grpc-tls-key-path /tls/server.key
```

### Bulk Permission Checks

The library uses SpiceDB's native `CheckBulkPermissionsRequest` API, which checks all resources in a single efficient API call:

```python
retriever = SpiceDBRetriever(
    ...,
    # All resources are checked in one bulk API call
    # No manual tuning needed - automatically optimal
)
```

This is significantly more efficient than making N individual permission checks.

### Fail-Open Mode

For high availability, allow access if SpiceDB is unavailable:

```python
retriever = SpiceDBRetriever(
    ...,
    fail_open=True,  # Allow access on SpiceDB errors (use cautiously!)
)
```

**Warning:** Only use fail-open in specific scenarios where availability is more important than security.

### Custom Subject Types

Support different subject types beyond "user":

```python
# Service accounts
retriever = SpiceDBRetriever(
    ...,
    subject_type="service",
    subject_id="api-service-1",
)

# Organizations
retriever = SpiceDBRetriever(
    ...,
    subject_type="organization",
    subject_id="acme-corp",
)
```

Update your schema accordingly:

```zed
definition service {}
definition organization {}

definition document {
    relation viewer: user | service | organization
    permission view = viewer
}
```

---

## Additional Resources

- **LangChain Documentation**: https://python.langchain.com/
- **SpiceDB Documentation**: https://authzed.com/docs
- **SpiceDB Playground**: https://play.authzed.com (interactive schema design)
- **langchain-spicedb GitHub**: https://github.com/yourusername/langchain-spicedb
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

- Open an issue: https://github.com/yourusername/langchain-spicedb/issues
- Check SpiceDB docs: https://authzed.com/docs
- Join Discord communities (links above)

---

**Happy building with langchain-spicedb! 🚀**
