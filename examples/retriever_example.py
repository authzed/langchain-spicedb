"""
SpiceDBAuthFilter Example - Post-filter Authorization RAG Pipeline

This example demonstrates how to use SpiceDBAuthFilter in a LangChain chain.
SpiceDBAuthFilter sits between a retriever and the rest of the chain,
filtering documents based on SpiceDB permissions.

The filter is reusable across users — pass subject_id at call time via config.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from langchain_spicedb import SpiceDBAuthFilter

load_dotenv()


async def main():
    print("=" * 80)
    print("SpiceDBAuthFilter Example - Authorization-Aware RAG")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

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
            page_content="SpiceDB is an authorization database for managing permissions.",
            metadata={"article_id": "789", "topic": "authorization"},
        ),
    ]

    async def mock_retriever(query: str):
        print(f"Retrieving documents for query: '{query}'")
        return sample_docs

    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)

    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", temperature=0)

    auth = SpiceDBAuthFilter(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type="article",
        subject_type="user",
        resource_id_key="article_id",
        permission="view",
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Answer the question based only on the provided context. "
            "If you don't have enough information, say so.",
        ),
        ("human", "Question: {question}\n\nContext:\n{context}"),
    ])

    # Build chain once, reuse for different users via config
    chain = (
        RunnableParallel({
            "context": RunnableLambda(mock_retriever) | auth | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        })
        | prompt
        | llm
        | StrOutputParser()
    )

    for user, query in [
        ("alice", "What programming languages are mentioned?"),
        ("tim", "Tell me about SpiceDB"),
    ]:
        print()
        print("-" * 80)
        print(f"User: {user} | Query: {query}")
        print("-" * 80)

        answer = await chain.ainvoke(
            query,
            config={"configurable": {"subject_id": user}},
        )
        print(f"\nAnswer:\n{answer}")
        print()


async def demo_without_openai():
    """Run the authorization filter without calling OpenAI — for quick testing."""
    print("=" * 80)
    print("SpiceDBAuthFilter Demo - Document Filtering Only")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

    sample_docs = [
        Document(page_content="Article 1", metadata={"article_id": "123"}),
        Document(page_content="Article 2", metadata={"article_id": "456"}),
        Document(page_content="Article 3", metadata={"article_id": "789"}),
    ]

    auth = SpiceDBAuthFilter(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type="article",
        subject_type="user",
        resource_id_key="article_id",
        permission="view",
    )

    for user in ["alice", "tim", "unauthorized_user"]:
        print(f"User: {user}")
        authorized = await auth.ainvoke(
            sample_docs,
            config={"configurable": {"subject_id": user}},
        )
        ids = [d.metadata["article_id"] for d in authorized]
        print(f"  Authorized articles: {ids if ids else 'none'}")
        print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB must be running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print("3. Set OPENAI_API_KEY environment variable (only needed for main())")
    print("4. Schema and permissions must be configured in SpiceDB")
    print()
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(main())
    else:
        asyncio.run(demo_without_openai())
