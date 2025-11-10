# Integration Guide for Your Jupyter Notebook

This guide shows you exactly how to integrate `spicedb-rag-auth` into your existing Jupyter notebook.

## Installation

```bash
pip install -e /Users/sohan/code-samples/spicedb-rag-auth
```

Or if you want to install from the current directory:

```bash
cd /Users/sohan/code-samples/spicedb-rag-auth
pip install -e .
```

## Your Current Code (Before)

```python
from authzed.api.v1 import Client, CheckPermissionRequest, CheckPermissionResponse
from grpcutil import insecure_bearer_token_credentials

# Your custom filter function
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

# Your chain
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

## New Code (After Integration)

### Option 1: Drop-in Replacement (Minimal Changes)

```python
from spicedb_rag_auth import SpiceDBAuthorizer
from langchain_core.output_parsers import StrOutputParser

# Initialize the authorizer ONCE at the top of your notebook
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint=SPICEDB_ENDPOINT,  # Your existing variable
    spicedb_token=SPICEDB_TOKEN,         # Your existing variable
    resource_type="article",
    subject_type="user",
    permission="view",
    resource_id_key="article_id",        # Match your metadata key
)

# Replace your filter function with this
async def filter_docs_with_spicedb(docs: List):
    """Drop-in replacement - same signature, new implementation"""
    result = await authorizer.filter_documents(
        documents=docs,
        subject_id="tim",  # Your user
    )
    # Optional: Print metrics
    print(f"Authorized {result.total_authorized}/{result.total_retrieved} docs")
    return result.authorized_documents

# Your chain stays EXACTLY the same - no changes needed!
chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(filter_docs_with_spicedb),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)
```

### Option 2: Using SpiceDBAuthFilter (Recommended)

```python
from spicedb_rag_auth import SpiceDBAuthFilter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Create the auth filter with subject_id
auth = SpiceDBAuthFilter(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
    subject_id="tim",  # Pass user ID here
)

# Your chain with the new filter
chain = (
    RunnableParallel({
        "context": retriever | auth,
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)
```

### Option 3: Using SpiceDBAuthLambda

```python
from spicedb_rag_auth import SpiceDBAuthLambda

# Create the auth filter
auth_filter = SpiceDBAuthLambda(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    subject_id="tim",
    resource_id_key="article_id",
)

# Your chain with the new filter
chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(auth_filter),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()
)
```

## Complete Jupyter Notebook Example

Here's what your notebook cells should look like:

### Cell 1: Imports

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_community.vectorstores import Pinecone as PineconeVectorStore

# NEW: Import the authorization agent
from spicedb_rag_auth import SpiceDBAuthorizer

# Your existing imports
import os
from dotenv import load_dotenv

load_dotenv()
```

### Cell 2: Configuration

```python
# Your existing config
SPICEDB_ENDPOINT = "localhost:50051"
SPICEDB_TOKEN = "sometoken"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

### Cell 3: Initialize Components

```python
# Your existing Pinecone setup
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    namespace=namespace_name,
    embedding=OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        dimensions=1024,
        model="text-embedding-3-large"
    )
)

retriever = docsearch.as_retriever(search_kwargs={"k": 4})

# Your existing LLM
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o-mini",
    temperature=1
)

# Your existing prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You answer strictly from the provided context. If insufficient, say so."),
    ("human", "Question: {question}\n\nContext:\n{context}")
])

# NEW: Initialize the authorization agent
authorizer = SpiceDBAuthorizer(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
)
```

### Cell 4: Create Authorization Filter

```python
# NEW: Create your filter function
async def filter_docs_with_spicedb(docs):
    result = await authorizer.filter_documents(
        documents=docs,
        subject_id="tim",  # Replace with your user variable
    )
    # Optional: Print metrics for debugging
    print(f"📊 Authorized {result.total_authorized}/{result.total_retrieved} documents")
    print(f"⏱️  Authorization took {result.check_latency_ms:.2f}ms")
    return result.authorized_documents
```

### Cell 5: Build the Chain

```python
from langchain_core.output_parsers import StrOutputParser

# Your chain - SAME AS BEFORE!
chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(filter_docs_with_spicedb),
        "question": RunnablePassthrough(),
    })
    | prompt
    | llm
    | StrOutputParser()  # Important: Extracts just the text from response
)

print("✅ Chain ready!")
```

### Cell 6: Run Queries

```python
# Test it out
question = "Who won the Oscar for best football movie?"
answer = await chain.ainvoke(question)
print(f"Question: {question}")
print(f"Answer: {answer}")
```

## Benefits You Get

1. **Less Code**: No need to manually iterate and check each document
2. **Better Performance**: Concurrent permission checks (batched)
3. **Metrics**: See authorization rates and latency
4. **Maintainable**: Reusable across notebooks and projects
5. **Tested**: The package is tested and optimized

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError: No module named 'spicedb_rag_auth'`:

```bash
# Make sure you installed it
pip install -e /Users/sohan/code-samples/spicedb-rag-auth

# Or in your notebook:
!pip install -e /Users/sohan/code-samples/spicedb-rag-auth
```

### SpiceDB Connection Error

Make sure SpiceDB is running:

```bash
docker run --rm -p 50051:50051 authzed/spicedb serve \
    --grpc-preshared-key "sometoken" \
    --grpc-no-tls
```

### Metadata Key Mismatch

If your documents use a different metadata key (not `article_id`), specify it:

```python
authorizer = SpiceDBAuthorizer(
    ...
    resource_id_key="doc_id",  # Or whatever key you use
)
```

## Testing Different Users

To test authorization for different users, you have several options:

### Option 1: Create separate auth instances

```python
from spicedb_rag_auth import SpiceDBAuthFilter

# Create separate filters for each user
alice_auth = SpiceDBAuthFilter(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
    subject_id="alice",
)

bob_auth = SpiceDBAuthFilter(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
    subject_id="bob",
)

# Use in chains
alice_chain = (
    RunnableParallel({
        "context": retriever | alice_auth,
        "question": RunnablePassthrough(),
    })
    | prompt | llm | StrOutputParser()
)

bob_chain = (
    RunnableParallel({
        "context": retriever | bob_auth,
        "question": RunnablePassthrough(),
    })
    | prompt | llm | StrOutputParser()
)
```

### Option 2: Pass subject_id at runtime

```python
# Create one filter without subject_id
auth = SpiceDBAuthFilter(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
)

chain = (
    RunnableParallel({
        "context": retriever | auth,
        "question": RunnablePassthrough(),
    })
    | prompt | llm | StrOutputParser()
)

# Test with different users
alice_answer = await chain.ainvoke(
    "Your question?",
    config={"configurable": {"subject_id": "alice"}}
)

bob_answer = await chain.ainvoke(
    "Your question?",
    config={"configurable": {"subject_id": "bob"}}
)
```

## Using with LangGraph

If you're using LangGraph instead of LangChain, you can use the provided `RAGAuthState` TypedDict:

```python
from langgraph.graph import StateGraph, END
from spicedb_rag_auth import create_auth_node, RAGAuthState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Use the provided state type
graph = StateGraph(RAGAuthState)

# Add your retrieval node
def retrieve_node(state):
    """Retrieve documents from vector store"""
    docs = retriever.invoke(state["question"])
    return {"retrieved_documents": docs}

# Add generation node to answer the question
def generate_node(state):
    """Generate answer using authorized documents"""
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer strictly from the provided context."),
        ("human", "Question: {question}\n\nContext:\n{context}")
    ])

    # Format context from authorized documents
    context = "\n\n".join([doc.page_content for doc in state["authorized_documents"]])

    # Generate answer
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
    messages = prompt.format_messages(question=state["question"], context=context)
    answer = llm.invoke(messages)

    return {"answer": answer.content}

# Add nodes
graph.add_node("retrieve", retrieve_node)
graph.add_node("authorize", create_auth_node(
    spicedb_endpoint=SPICEDB_ENDPOINT,
    spicedb_token=SPICEDB_TOKEN,
    resource_type="article",
    resource_id_key="article_id",
))
graph.add_node("generate", generate_node)

# Add edges
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "authorize")
graph.add_edge("authorize", "generate")
graph.add_edge("generate", END)

# Compile and run
app = graph.compile()
result = await app.ainvoke({
    "question": "Who won the Oscar for best football movie?",
    "subject_id": "tim",
})

print(f"Question: {result['question']}")
print(f"Answer: {result['answer']}")
print(f"Authorization: {result['auth_results']['total_authorized']}/{result['auth_results']['total_retrieved']} docs")
```

### Extending RAGAuthState

You can extend the provided state with your own fields:

```python
from spicedb_rag_auth import RAGAuthState

class MyCustomState(RAGAuthState):
    """Extend with custom fields"""
    user_preferences: dict
    conversation_history: list
    custom_metadata: str

graph = StateGraph(MyCustomState)
# ... use as normal
```

## Next Steps

1. Test in your notebook with a simple query
2. Compare results with your old implementation
3. Check the metrics (authorization rate, latency)
4. If everything works, you can remove your old `filter_docs_with_spicedb` function

## Support

If you encounter any issues:
1. Check the main README.md for more examples
2. Look at `examples/jupyter_notebook_example.py`
3. Open an issue on GitHub
