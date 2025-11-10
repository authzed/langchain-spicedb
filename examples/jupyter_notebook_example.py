"""
Jupyter Notebook Example - Drop-in replacement for existing RAG pipelines

This example shows how to integrate the authorization agent into an existing
Jupyter notebook RAG pipeline with minimal code changes.

This is designed to match the pattern you showed in your Jupyter notebook.
"""

import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from spicedb_rag_auth import SpiceDBAuthorizer


# Mock document store (in your case, this would be Pinecone)
class MockVectorStore:
    """Mock vector store for demonstration"""

    def __init__(self):
        self.documents = [
            Document(
                page_content="Python is a high-level programming language.",
                metadata={"article_id": "doc1"}
            ),
            Document(
                page_content="JavaScript is used for web development.",
                metadata={"article_id": "doc2"}
            ),
            Document(
                page_content="Machine learning is a subset of AI.",
                metadata={"article_id": "doc3"}
            ),
            Document(
                page_content="SpiceDB manages authorization.",
                metadata={"article_id": "doc4"}
            ),
        ]

    def as_retriever(self, search_kwargs=None):
        """Return a retriever interface"""
        async def retrieve(query: str) -> List[Document]:
            k = search_kwargs.get("k", 4) if search_kwargs else 4
            return self.documents[:k]
        return retrieve


async def main():
    print("="*80)
    print("Jupyter Notebook RAG Pipeline Example")
    print("="*80)
    print()

    # =========================================================================
    # SETUP - This is what you already have in your notebook
    # =========================================================================

    SPICEDB_ENDPOINT = "localhost:50051"
    SPICEDB_TOKEN = "sometoken"
    OPENAI_API_KEY = "your-api-key"  # Replace with actual key or load from env

    # Your existing vector store (Pinecone in your case)
    docsearch = MockVectorStore()

    # Your existing retriever
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

    # =========================================================================
    # AUTHORIZATION - Replace your custom filter_docs_with_spicedb function
    # =========================================================================

    # OLD CODE (your custom function):
    # async def filter_docs_with_spicedb(docs: List):
    #     filtered_docs = []
    #     for doc in docs:
    #         article_id = doc.metadata.get("article_id")
    #         resp = await client.CheckPermission(...)
    #         if resp.permissionship == ...:
    #             filtered_docs.append(doc)
    #     return filtered_docs

    # NEW CODE (using the authorization agent):
    authorizer = SpiceDBAuthorizer(
        spicedb_endpoint=SPICEDB_ENDPOINT,
        spicedb_token=SPICEDB_TOKEN,
        resource_type="article",
        subject_type="user",
        permission="view",
        resource_id_key="article_id",  # Match your metadata key
    )

    # Create a wrapper that matches your function signature
    async def filter_docs_with_spicedb(docs: List) -> List:
        """Drop-in replacement for your existing filter function"""
        user_id = "tim"  # The user from your example
        result = await authorizer.filter_documents(docs, subject_id=user_id)
        return result.authorized_documents

    # =========================================================================
    # CHAIN - Your existing chain structure (NO CHANGES NEEDED)
    # =========================================================================

    graph = (
        RunnableParallel({
            "context": retriever | RunnableLambda(filter_docs_with_spicedb),
            "question": RunnablePassthrough(),
        })
        | prompt
        | llm
        | StrOutputParser()
    )

    print("✅ Retrieval + authorization + chain wired up")
    print()

    # =========================================================================
    # TEST - Run some queries
    # =========================================================================

    query = "What programming languages are mentioned?"
    print(f"Query: {query}")
    print("-" * 80)

    answer = await graph.ainvoke(query)
    print(f"\nAnswer:\n{answer}")
    print()


if __name__ == "__main__":
    print()
    print("This example shows how to integrate the authorization agent")
    print("into your existing Jupyter notebook RAG pipeline.")
    print()
    print("Key changes:")
    print("1. Import SpiceDBAuthorizer")
    print("2. Replace your filter_docs_with_spicedb function")
    print("3. No other changes needed!")
    print()
    print("="*80)
    print()

    asyncio.run(main())
