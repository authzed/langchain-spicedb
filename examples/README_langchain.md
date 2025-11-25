# LangChain + SpiceDB Authorization Example

This example demonstrates how to integrate SpiceDB authorization into a LangChain RAG (Retrieval-Augmented Generation) pipeline. The example shows how different users receive different answers to the same questions based on their document access permissions.

## What This Example Does

The example creates a simple RAG pipeline with:
- A mock document retriever containing 4 articles about programming languages and SpiceDB
- SpiceDB authorization filter that restricts which documents each user can access
- OpenAI GPT-4 to answer questions based only on authorized documents
- Two test queries to demonstrate permission-based filtering

## Prerequisites

1. **Python dependencies:**
   ```bash
   pip install spicedb-rag-auth langchain langchain-openai python-dotenv
   ```

2. **OpenAI API Key:**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

3. **SpiceDB and zed CLI:**
   - SpiceDB server running locally
   - zed CLI tool for managing schemas and relationships
   ```bash
   spicedb serve --grpc-preshared-key sometoken
   ```

## Setup

### 1. Define the Schema

Create a schema that defines users, articles, and view permissions:

```bash
zed schema write <(cat << EOF
definition user {}
definition article {
    relation viewer: user
    permission view = viewer
}
EOF
) --insecure
```

### 2. Create Relationships

Grant access to specific documents for different users:

```bash
# Alice can view doc4 (SpiceDB article)
zed relationship create article:doc4 viewer user:alice --insecure

# Bob can view doc2 (JavaScript article)
zed relationship create article:doc2 viewer user:bob --insecure

# Grant more permissions as needed
zed relationship create article:doc1 viewer user:charlie --insecure
zed relationship create article:doc3 viewer user:charlie --insecure
```

## Running the Example

```bash
python3 examples/langchain_example.py
```

## Expected Behavior

The example runs two queries:
1. "What programming languages are mentioned?"
2. "Tell me about SpiceDB"

### Example Output for Alice (can only view doc4)

```
Query: What programming languages are mentioned?
Answer: There are no programming languages mentioned in the provided context.

Query: Tell me about SpiceDB
Answer: SpiceDB is an authorization database for managing permissions.
```

Alice only sees doc4, so she can answer about SpiceDB but not about programming languages.

### Example Output for Bob (can only view doc2)

```
Query: What programming languages are mentioned?
Answer: The programming languages mentioned are JavaScript.

Query: Tell me about SpiceDB
Answer: I don't have enough information to provide details about SpiceDB.
```

Bob only sees doc2, so he can answer about JavaScript but not about SpiceDB.

## Testing Different Users

To test with a different user, modify line 69 in `langchain_example.py`:

```python
auth_filter = SpiceDBAuthLambda(
    # ... other parameters ...
    subject_id="alice",  # Change to "bob", "charlie", etc.
)
```

## How It Works

1. **Query Processing**: User submits a question
2. **Document Retrieval**: Mock retriever returns all 4 documents
3. **Authorization Filter**: SpiceDB checks which documents the user can view
4. **Filtered Context**: Only authorized documents are passed to the LLM
5. **Answer Generation**: LLM generates answer using only accessible documents

## Key Components

- **SpiceDBAuthLambda**: Authorization filter that integrates with LangChain's `RunnableLambda`
- **Mock Retriever**: Simulates a vector database or document store
- **LangChain LCEL**: Uses LangChain Expression Language for composable chains
- **Authorization Metadata**: Uses `article_id` field to match documents with SpiceDB resources