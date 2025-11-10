# Quick Start: Jupyter Notebook Integration

## 5-Minute Integration Guide

### Step 1: Import the Package (Add to your imports cell)

```python
from spicedb_rag_auth import SpiceDBAuthorizer
```

### Step 2: Initialize the Authorizer (Add after your config)

```python
# Your existing config
SPICEDB_ENDPOINT = "localhost:50051"
SPICEDB_TOKEN = "sometoken"

# NEW: Initialize authorizer
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",  # Your SpiceDB resource type
    resource_id_key="article_id",  # Key in your document metadata
)
```

### Step 3: Replace Your Filter Function

**OLD CODE (Delete this):**
```python
async def filter_docs_with_spicedb(docs: List):
    filtered_docs = []
    for doc in docs:
        article_id = doc.metadata.get("article_id")
        resp = await client.CheckPermission(
            CheckPermissionRequest(
                subject=SubjectReference(
                    object=ObjectReference(
                        object_type="user",
                        object_id="tim",
                    ),
                ),
                resource=ObjectReference(
                    object_type="article",
                    object_id=str(article_id),
                ),
                permission="view",
            )
        )
        if resp.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            filtered_docs.append(doc)
    return filtered_docs
```

**NEW CODE (Replace with this):**
```python
async def filter_docs_with_spicedb(docs: List):
    result = await authorizer.filter_documents(
        documents=docs,
        subject_id="tim",  # Your user ID
    )
    # Optional: Print metrics
    print(f"📊 Authorized {result.total_authorized}/{result.total_retrieved} docs")
    return result.authorized_documents
```

### Step 4: Keep Everything Else the Same!

Your chain code doesn't need to change:

```python
graph = (
    RunnableParallel({
        "context": retriever | RunnableLambda(filter_docs_with_spicedb),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)
```

### Step 5: Test It!

```python
question = "Who won the Oscar for best football movie?"
answer = await graph.ainvoke(question)
print(answer)
```

## That's It!

You've successfully integrated the authorization agent.

## What You Get

✅ Less code (deleted ~15 lines)
✅ Better performance (concurrent checks)
✅ Metrics (see authorization rates)
✅ Reusable (use in other notebooks)
✅ Maintained (package is updated independently)

## Optional: See Detailed Metrics

```python
async def filter_docs_with_spicedb(docs: List):
    result = await authorizer.filter_documents(
        documents=docs,
        subject_id="tim",
    )

    # Print detailed metrics
    print(f"📊 Retrieved: {result.total_retrieved}")
    print(f"✅ Authorized: {result.total_authorized}")
    print(f"📈 Rate: {result.authorization_rate:.1%}")
    print(f"⏱️  Latency: {result.check_latency_ms:.2f}ms")
    if result.denied_resource_ids:
        print(f"🚫 Denied: {result.denied_resource_ids}")

    return result.authorized_documents
```

## Optional: Dynamic User IDs

If you want to test different users:

```python
# Create a reusable filter
def create_filter(user_id: str):
    async def filter_func(docs):
        result = await authorizer.filter_documents(docs, subject_id=user_id)
        return result.authorized_documents
    return filter_func

# Use it
alice_filter = create_filter("alice")
bob_filter = create_filter("bob")

# Build different chains
alice_chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(alice_filter),
        "question": RunnablePassthrough(),
    }) | prompt | llm | StrOutputParser()
)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'spicedb_rag_auth'"

Run in a notebook cell:
```python
!pip install -e /Users/sohan/code-samples/spicedb-rag-auth
```

### "No resource_id found in metadata"

Make sure your metadata key matches:
```python
authorizer = SpiceDBAuthorizer(
    ...
    resource_id_key="article_id",  # Must match your metadata key
)

# Check your documents have it:
print(doc.metadata)  # Should have {"article_id": "..."}
```

### SpiceDB Connection Error

Make sure SpiceDB is running:
```bash
docker run --rm -p 50051:50051 authzed/spicedb serve \
    --grpc-preshared-key "sometoken" \
    --grpc-no-tls
```

## Complete Example Cell

Here's a complete cell you can copy-paste:

```python
# Imports
from spicedb_rag_auth import SpiceDBAuthorizer

# Config
SPICEDB_ENDPOINT = "localhost:50051"
SPICEDB_TOKEN = "sometoken"

# Initialize authorizer
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
)

# Filter function
async def filter_docs_with_spicedb(docs):
    result = await authorizer.filter_documents(docs, subject_id="tim")
    print(f"📊 Authorized {result.total_authorized}/{result.total_retrieved} docs")
    return result.authorized_documents

# Chain (your existing code)
graph = (
    RunnableParallel({
        "context": retriever | RunnableLambda(filter_docs_with_spicedb),
        "question": RunnablePassthrough(),
    })
    | prompt | llm | StrOutputParser()
)

print("✅ Ready!")
```

## Need More Help?

- See **INTEGRATION_GUIDE.md** for detailed step-by-step
- See **examples/jupyter_notebook_example.py** for a complete example
- See **README.md** for all features and options
