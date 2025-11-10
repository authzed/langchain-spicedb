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

from spicedb_rag_auth import SpiceDBAuthLambda

load_dotenv()


async def main():
    print("="*80)
    print("LangChain + SpiceDB Authorization Example")
    print("="*80)
    print()

    # Mock retriever for demonstration
    sample_docs = [
        Document(
            page_content="Python is a high-level programming language known for simplicity.",
            metadata={"article_id": "doc1", "topic": "python"}
        ),
        Document(
            page_content="JavaScript is primarily used for web development.",
            metadata={"article_id": "doc2", "topic": "javascript"}
        ),
        Document(
            page_content="Machine learning enables systems to learn from data.",
            metadata={"article_id": "doc3", "topic": "ml"}
        ),
        Document(
            page_content="SpiceDB is an authorization database for managing permissions.",
            metadata={"article_id": "doc4", "topic": "authorization"}
        ),
    ]

    async def mock_retriever(query: str):
        """Mock retriever that returns all documents"""
        print(f"Retrieving documents for query: '{query}'")
        return sample_docs

    # Initialize LLM
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        temperature=0
    )

    # Initialize SpiceDB authorization filter
    # Note: We're using SpiceDBAuthLambda for use with RunnableLambda
    auth_filter = SpiceDBAuthLambda(
        spicedb_endpoint="localhost:50051",
        spicedb_token="sometoken",
        resource_type="article",
        subject_type="user",
        permission="view",
        resource_id_key="article_id",
        subject_id="alice",  # Change this to test different users
    )

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question based only on the provided context. If you don't have enough information, say so."),
        ("human", "Question: {question}\n\nContext:\n{context}")
    ])

    # Build the chain with authorization filter
    chain = (
        RunnableParallel({
            "context": RunnableLambda(mock_retriever) | RunnableLambda(auth_filter),
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
    print("1. SpiceDB must be running on localhost:50051")
    print("2. OPENAI_API_KEY must be set in .env file")
    print("3. Schema and permissions must be configured")
    print()
    print("Note: This example uses 'alice' as the subject_id.")
    print("      Modify the auth_filter initialization to test other users.")
    print()
    print("="*80)
    print()

    asyncio.run(main())
