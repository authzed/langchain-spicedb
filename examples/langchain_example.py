"""
LangChain Example - Using SpiceDB Authorization in a LangChain RAG Pipeline

This example demonstrates how to integrate the authorization agent
into a LangChain chain using the pipe operator.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from langchain_spicedb import SpiceDBAuthLambda

load_dotenv()


async def main():
    print("=" * 80)
    print("LangChain + SpiceDB Authorization Example")
    print("=" * 80)
    print()

    # Configuration
    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    subject_id = os.getenv("SUBJECT_ID", "alice")

    # Mock retriever for demonstration
    sample_docs = [
        Document(
            page_content="Python is a high-level programming language known for simplicity.",
            metadata={"article_id": "123", "topic": "python"},
        ),
        Document(
            page_content="JavaScript is primarily used for web development.",
            metadata={"article_id": "456", "topic": "javascript"},
        ),
        Document(
            page_content="Machine learning enables systems to learn from data.",
            metadata={"article_id": "789", "topic": "ml"},
        ),
        Document(
            page_content="SpiceDB is an authorization database for managing permissions.",
            metadata={"article_id": "101", "topic": "authorization"},
        ),
    ]

    async def mock_retriever(query: str):
        """Mock retriever that returns all documents"""
        print(f"Retrieving documents for query: '{query}'")
        return sample_docs

    # Initialize LLM
    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", temperature=0)

    # Initialize SpiceDB authorization filter
    # Note: We're using SpiceDBAuthLambda for use with RunnableLambda
    auth_filter = SpiceDBAuthLambda(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type="article",
        subject_type="user",
        permission="view",
        resource_id_key="article_id",
        subject_id=subject_id,
    )

    # Create prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer the question based only on the provided context. If you don't have enough information, say so.",
            ),
            ("human", "Question: {question}\n\nContext:\n{context}"),
        ]
    )

    # Build the chain with authorization filter
    chain = (
        RunnableParallel(
            {
                "context": RunnableLambda(mock_retriever) | RunnableLambda(auth_filter),
                "question": RunnablePassthrough(),
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    # Test queries
    queries = [
        "What programming languages are mentioned?",
        "Tell me about SpiceDB",
    ]

    for query in queries:
        print()
        print("-" * 80)
        print(f"Query: {query}")
        print("-" * 80)

        answer = await chain.ainvoke(query)
        print(f"\nAnswer:\n{answer}")
        print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB must be running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print("3. Set OPENAI_API_KEY environment variable")
    print("4. Schema and permissions must be configured in SpiceDB")
    print()
    print("Optional Configuration (via environment variables or .env file):")
    print("  SPICEDB_ENDPOINT=localhost:50051 (default)")
    print("  SPICEDB_TOKEN=somerandomkeyhere (required)")
    print("  SUBJECT_ID=alice (default - change to test different users)")
    print()
    print("=" * 80)
    print()

    asyncio.run(main())
