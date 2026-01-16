"""
SpiceDBRetriever Example - Authorization-Aware RAG Pipeline

This example demonstrates how to use SpiceDBRetriever to automatically filter
retrieved documents based on SpiceDB permissions before passing them to an LLM.

SpiceDBRetriever wraps any LangChain retriever and adds authorization filtering,
ensuring users only see documents they have permission to access.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI

from langchain_spicedb import SpiceDBRetriever

load_dotenv()


# Mock retriever that simulates a vector database
class MockVectorStoreRetriever(BaseRetriever):
    """Mock retriever that returns sample documents for demonstration."""

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        """Return mock documents based on query."""
        # In a real application, this would query a vector database like Pinecone, Chroma, etc.
        return [
            Document(
                page_content="Python is a high-level programming language known for simplicity and readability.",
                metadata={"article_id": "123", "title": "Python Basics", "author": "Alice"}
            ),
            Document(
                page_content="JavaScript is the language of the web, running in browsers and servers.",
                metadata={"article_id": "456", "title": "JavaScript Guide", "author": "Bob"}
            ),
            Document(
                page_content="Machine learning models can be trained on large datasets to make predictions.",
                metadata={"article_id": "789", "title": "ML Introduction", "author": "Charlie"}
            ),
            Document(
                page_content="SpiceDB is a database system for managing fine-grained authorization.",
                metadata={"article_id": "101", "title": "SpiceDB Overview", "author": "Diana"}
            ),
        ]

    async def _aget_relevant_documents(self, query: str, *, run_manager=None):
        """Async version."""
        return self._get_relevant_documents(query)


async def main():
    print("="*80)
    print("SpiceDBRetriever Example - Authorization-Aware RAG")
    print("="*80)
    print()

    # Configuration
    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    subject_id = os.getenv("SUBJECT_ID", "alice")  # Change to test different users

    print("Configuration:")
    print(f"  SpiceDB Endpoint: {spicedb_endpoint}")
    print(f"  Subject (User): {subject_id}")
    print("  Resource Type: article")
    print("  Permission: view")
    print()

    # Create base retriever (would typically be a vector store)
    base_retriever = MockVectorStoreRetriever()

    # Wrap with SpiceDBRetriever for authorization filtering
    authorized_retriever = SpiceDBRetriever(
        base_retriever=base_retriever,
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_id=subject_id,
        subject_type="user",
        resource_type="article",
        resource_id_key="article_id",  # Metadata key containing the resource ID
        permission="view",
        use_tls=False,  # Set to True for production
    )

    # Initialize LLM
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        temperature=0
    )

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Answer questions based only on the provided context. If the context doesn't contain enough information, say so."),
        ("human", "Question: {question}\n\nContext:\n{context}")
    ])

    # Format documents helper
    def format_docs(docs):
        if not docs:
            return "No authorized documents found."
        return "\n\n".join(f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs))

    # Build RAG chain with authorization
    # The SpiceDBRetriever automatically filters documents based on permissions
    rag_chain = (
        RunnableParallel({
            "context": authorized_retriever | format_docs,
            "question": RunnablePassthrough(),
        })
        | prompt
        | llm
        | StrOutputParser()
    )

    # Test queries
    queries = [
        "What programming languages are mentioned?",
        "Tell me about SpiceDB",
        "What is machine learning?",
    ]

    print("-" * 80)
    print("Running Queries")
    print("-" * 80)
    print()

    for query in queries:
        print(f"Query: {query}")
        print("-" * 40)

        # First, show what documents would be retrieved without authorization
        print("\nDocuments from base retriever (before authorization):")
        base_docs = await base_retriever.ainvoke(query)
        for doc in base_docs:
            print(f"  - {doc.metadata['title']} (ID: {doc.metadata['article_id']})")

        # Now show what documents pass authorization
        print(f"\nDocuments after SpiceDB authorization filter (user: {subject_id}):")
        authorized_docs = await authorized_retriever.ainvoke(query)
        if authorized_docs:
            for doc in authorized_docs:
                print(f"  ✓ {doc.metadata['title']} (ID: {doc.metadata['article_id']})")
        else:
            print("  ✗ No authorized documents")

        # Get LLM answer with authorized context
        print("\nLLM Answer:")
        answer = await rag_chain.ainvoke(query)
        print(f"{answer}")
        print()
        print("="*80)
        print()

    # Demonstrate batch retrieval
    print("-" * 80)
    print("Batch Retrieval Example")
    print("-" * 80)
    print()

    batch_queries = ["Python", "JavaScript"]
    print(f"Retrieving for multiple queries: {batch_queries}")
    print()

    batch_results = await authorized_retriever.abatch(batch_queries)
    for query, docs in zip(batch_queries, batch_results):
        print(f"Query: '{query}' -> {len(docs)} authorized document(s)")
    print()


async def demo_without_openai():
    """
    Demo that doesn't require OpenAI API key - just shows document filtering
    """
    print("="*80)
    print("SpiceDBRetriever Demo - Document Filtering Only")
    print("="*80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    subject_id = os.getenv("SUBJECT_ID", "alice")

    print(f"Testing document filtering for user: {subject_id}")
    print()

    base_retriever = MockVectorStoreRetriever()
    authorized_retriever = SpiceDBRetriever(
        base_retriever=base_retriever,
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_id=subject_id,
        subject_type="user",
        resource_type="article",
        resource_id_key="article_id",
        permission="view",
    )

    # Retrieve and show filtering in action
    query = "programming languages"

    base_docs = await base_retriever.ainvoke(query)
    authorized_docs = await authorized_retriever.ainvoke(query)

    print(f"Documents retrieved (before authorization): {len(base_docs)}")
    for doc in base_docs:
        print(f"  - {doc.metadata['title']} (ID: {doc.metadata['article_id']})")
    print()

    print(f"Documents after authorization: {len(authorized_docs)}")
    for doc in authorized_docs:
        print(f"  ✓ {doc.metadata['title']} (ID: {doc.metadata['article_id']})")

    if len(authorized_docs) < len(base_docs):
        print()
        print(f"SpiceDB filtered out {len(base_docs) - len(authorized_docs)} unauthorized document(s)")
    print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print("3. SpiceDB schema configured with 'article' resource type and 'view' permission")
    print("4. Create test relationships (e.g., zed relationship create article:123 viewer user:tim)")
    print()
    print("Optional:")
    print("5. Set OPENAI_API_KEY for full RAG demo (otherwise run basic demo)")
    print("6. Set SUBJECT_ID to test different users (default: tim)")
    print()
    print("="*80)
    print()

    # Check if OpenAI API key is available
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(main())
    else:
        print("OpenAI API key not found. Running basic demo without LLM...")
        print()
        asyncio.run(demo_without_openai())
