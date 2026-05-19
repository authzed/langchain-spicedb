# langchain-spicedb Examples

Working examples for every component in the library. See the [main README](../README.md) for component descriptions and decision guidance.

## Setup

### 1. Start SpiceDB

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_TOKEN=somerandomkeyhere
OPENAI_API_KEY=sk-...        # Optional — only needed for LLM answer generation
SUBJECT_ID=alice             # Optional — which user to test as
```

### 3. Install the Package

```bash
pip install -e ".[all]"
```

All examples write their own schema and seed their own test data at startup — no manual SpiceDB setup required.

---

## Examples

```
examples/
├── retriever_example.py               # SpiceDBAuthFilter — post-filter in LCEL chain
├── prefilter_retriever_example.py     # SpiceDBPreFilterRetriever — pre-filter in LCEL chain
├── langchain_example.py               # SpiceDBAuthFilter — low-level LCEL usage
├── tool_example.py                    # SpiceDBPermissionTool / SpiceDBBulkPermissionTool
├── langgraph_postfilter_example.py    # create_auth_node — post-filter in LangGraph
└── langgraph_prefilter_example.py     # create_pre_filter_auth_node — pre-filter in LangGraph
```

---

### `retriever_example.py` — Post-filter in LCEL

Uses `SpiceDBAuthFilter` in an LCEL chain. A mock retriever fetches all documents; the auth filter removes any the user isn't authorized to see before the LLM sees them.

```bash
python examples/retriever_example.py           # Filters docs only (no OpenAI needed)
OPENAI_API_KEY=sk-... python examples/retriever_example.py  # Full RAG answer
```

**What it shows:** Two users (`alice`, `tim`) getting different document sets from the same chain, passed at call time via `config={"configurable": {"subject_id": "..."}}`.

---

### `prefilter_retriever_example.py` — Pre-filter in LCEL

Uses `SpiceDBPreFilterRetriever`. Instead of fetching all docs and filtering, it calls SpiceDB's `LookupResources` first to get the user's authorized IDs, then runs a filtered vector search — unauthorized documents are never fetched.

```bash
python examples/prefilter_retriever_example.py
OPENAI_API_KEY=sk-... python examples/prefilter_retriever_example.py
```

**What it shows:** The vector store receives a filter containing only authorized IDs (printed in the output), so the search scope is restricted before any retrieval happens. Uses `retriever.with_config(subject_id=...)` to switch users.

---

### `langchain_example.py` — Low-level LCEL

Direct `SpiceDBAuthFilter` usage in an LCEL chain without a wrapper retriever. Useful as a reference for custom chain construction.

```bash
python examples/langchain_example.py
```

---

### `tool_example.py` — Agent Permission Checks

Uses `SpiceDBPermissionTool` and `SpiceDBBulkPermissionTool` to give a LangChain agent the ability to check permissions. Runs four agent queries covering single checks, bulk checks, different permission types, and denial handling.

```bash
OPENAI_API_KEY=sk-... python examples/tool_example.py
```

**What it shows:** An agent reasoning about permissions — explaining to the user what they can and cannot do, and why.

---

### `langgraph_postfilter_example.py` — Post-filter in LangGraph

Uses `create_auth_node` in a 3-node LangGraph graph: `retrieve → authorize → generate`. The authorize node filters `retrieved_documents` from state and writes `authorized_documents` + `auth_results` (metrics) back to state.

```bash
python examples/langgraph_postfilter_example.py
SUBJECT_ID=tim python examples/langgraph_postfilter_example.py
```

**What it shows:** Graph structure inspection (nodes, edges), live execution trace, and authorization metrics (total retrieved, authorized, latency, denied IDs).

---

### `langgraph_prefilter_example.py` — Pre-filter in LangGraph

Uses `create_pre_filter_auth_node` in a 2-node graph: `retrieve_authorized → generate`. The single node calls `LookupResources` and runs the filtered vector search — no separate retrieve step.

```bash
python examples/langgraph_prefilter_example.py
SUBJECT_ID=alice python examples/langgraph_prefilter_example.py
```

**What it shows:** How the pre-filter graph is simpler (2 nodes vs 3), the vector store filter being applied with only authorized IDs, and which articles were skipped entirely.

---

## Troubleshooting

See the [Configuration Guide](../docs/configuration.md#troubleshooting) for connection errors, missing documents, schema errors, and async issues.

**Quick checks:**
```bash
docker ps | grep spicedb          # Is SpiceDB running?
echo $SPICEDB_ENDPOINT            # Is the endpoint set?
zed permission check article:123 view user:tim  # Does the permission exist?
```

---

## Further Reading

- [Configuration Guide](../docs/configuration.md) — TLS, fail-open, bulk checks, production setup
- [LangGraph Guide](../docs/langgraph-guide.md) — Custom state, reusable nodes, advanced patterns
- [SpiceDB Documentation](https://authzed.com/docs)
