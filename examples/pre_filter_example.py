"""
SpiceDBPreFilterRetriever Example - Pre-Filter Authorization RAG Pipeline

This example demonstrates how to use SpiceDBPreFilterRetriever to pre-filter
vector store searches using SpiceDB's LookupResources API.

Unlike SpiceDBRetriever (post-filter), this approach:
1. Calls SpiceDB first to get all resource IDs the user can access
2. Passes those IDs as a filter into the vector store search
3. Only retrieves documents the user is authorized to see

Use this pattern when users have access to a small fraction of a large corpus.
"""

import asyncio
import os
from typing import List
from unittest.mock import AsyncMock
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI

from langchain_spicedb import SpiceDBPreFilterRetriever

load_dotenv()


class MockVectorStore:
    """
    Mock vector store simulating Pinecone with metadata filter support.

    In a real application, replace this with:
        from langchain_pinecone import PineconeVectorStore
        knowledge = PineconeVectorStore.from_existing_index(
            index_name="my-index",
            embedding=OpenAIEmbeddings(...),
        )
    """

    async def asimilarity_search(
        self, query: str, k: int = 4, filter: dict = None
    ) -> List[Document]:
        """Return mock documents, filtered by article_id if filter is provided."""
        all_docs = [
            Document(
                page_content="Python is a high-level programming language known for simplicity.",
                metadata={"article_id": "123", "title": "Python Basics"},
            ),
            Document(
                page_content="JavaScript is the language of the web.",
                metadata={"article_id": "456", "title": "JavaScript Guide"},
            ),
            Document(
                page_content="Machine learning models can be trained on large datasets.",
                metadata={"article_id": "789", "title": "ML Introduction"},
            ),
            Document(
                page_content="SpiceDB is a database for fine-grained authorization.",
                metadata={"article_id": "101", "title": "SpiceDB Overview"},
            ),
        ]

        if filter and "article_id" in filter:
            authorized = filter["article_id"].get("$in", [])
            return [d for d in all_docs if d.metadata["article_id"] in authorized][:k]

        return all_docs[:k]


async def main():
    print("=" * 80)
    print("SpiceDBPreFilterRetriever Example - Pre-Filter Authorization RAG")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    subject_id = os.getenv("SUBJECT_ID", "tim")

    print("Configuration:")
    print(f"  SpiceDB Endpoint: {spicedb_endpoint}")
    print(f"  Subject (User):   {subject_id}")
    print("  Resource Type:    article")
    print("  Permission:       view")
    print()
    print("Pattern: LookupResources → authorized IDs → vector store filter → docs")
    print()

    vector_store = MockVectorStore()

    # SpiceDBPreFilterRetriever:
    # 1. Calls LookupResources(subject=tim, permission=view, resource_type=article)
    # 2. Gets back e.g. ["123", "101"] (articles tim can view)
    # 3. Calls filter_factory(["123", "101"]) → {"filter": {"article_id": {"$in": ["123", "101"]}}}
    # 4. Calls vector_store.asimilarity_search(query, k=4, filter=...)
    # 5. Returns only authorized + semantically relevant documents
    retriever = SpiceDBPreFilterRetriever(
        vector_store=vector_store,
        filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
        subject_id=subject_id,
        resource_type="article",
        permission="view",
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        k=4,
    )

    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Answer questions based only on the provided context. "
            "If the context doesn't contain enough information, say so.",
        ),
        ("human", "Question: {question}\n\nContext:\n{context}"),
    ])

    def format_docs(docs):
        if not docs:
            return "No authorized documents found."
        return "\n\n".join(
            f"Document {i + 1}:\n{doc.page_content}" for i, doc in enumerate(docs)
        )

    rag_chain = (
        RunnableParallel({
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        })
        | prompt
        | llm
        | StrOutputParser()
    )

    query = "Tell me about SpiceDB"
    print(f"Query: {query}")
    print("-" * 40)

    print(f"\nDocuments after pre-filter (user: {subject_id}):")
    authorized_docs = await retriever.ainvoke(query)
    if authorized_docs:
        for doc in authorized_docs:
            print(f"  ✓ {doc.metadata['title']} (ID: {doc.metadata['article_id']})")
    else:
        print("  ✗ No authorized documents")

    print("\nLLM Answer:")
    answer = await rag_chain.ainvoke(query)
    print(answer)
    print()
    print("=" * 80)


async def demo_without_openai():
    """Demo showing document pre-filtering without requiring an LLM."""
    print("=" * 80)
    print("SpiceDBPreFilterRetriever Demo - Pre-Filter Only")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    subject_id = os.getenv("SUBJECT_ID", "tim")

    print(f"Looking up authorized articles for user: {subject_id}")
    print()

    vector_store = MockVectorStore()

    retriever = SpiceDBPreFilterRetriever(
        vector_store=vector_store,
        filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
        subject_id=subject_id,
        resource_type="article",
        permission="view",
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
    )

    query = "programming languages"
    docs = await retriever.ainvoke(query)

    print(f"Documents returned for query '{query}':")
    if docs:
        for doc in docs:
            print(f"  ✓ {doc.metadata['title']} (ID: {doc.metadata['article_id']})")
    else:
        print("  ✗ No authorized documents found")
    print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print("3. SpiceDB schema with 'article' resource type and 'view' permission")
    print("4. Create relationships: zed relationship create article:123 viewer user:tim")
    print()
    print("Optional:")
    print("5. Set OPENAI_API_KEY for full RAG demo")
    print("6. Set SUBJECT_ID to test different users (default: tim)")
    print()
    print("=" * 80)
    print()

    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(main())
    else:
        print("OpenAI API key not found. Running pre-filter demo without LLM...")
        print()
        asyncio.run(demo_without_openai())
