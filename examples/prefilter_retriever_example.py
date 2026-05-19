"""
SpiceDBPreFilterRetriever Example - Pre-filter Authorization RAG Pipeline

Pre-filter approach:
  1. Ask SpiceDB which article IDs the user can access (LookupResources)
  2. Pass those IDs to the vector store as a filter
  3. Retrieve only semantically relevant documents the user is authorized to see

Contrast with post-filter (SpiceDBAuthFilter):
  Post-filter: fetch top-k docs → check each with SpiceDB → drop unauthorized
  Pre-filter:  get authorized IDs → search only within those IDs → no wasted fetches

Schema and test data are written automatically at startup.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from authzed.api.v1 import (
    Client, WriteSchemaRequest, WriteRelationshipsRequest, DeleteRelationshipsRequest,
    RelationshipUpdate, Relationship, SubjectReference, ObjectReference, RelationshipFilter,
)
from grpcutil import insecure_bearer_token_credentials, bearer_token_credentials

from langchain_spicedb import SpiceDBPreFilterRetriever

load_dotenv()

SCHEMA = """
definition user {}

definition article {
    relation viewer: user
    relation editor: user
    relation deleter: user
    permission view = viewer + editor + deleter
    permission edit = editor + deleter
    permission delete = deleter
}
"""

RELATIONSHIPS = [
    ("article", "123", "viewer", "user", "tim"),
    ("article", "123", "viewer", "user", "alice"),
    ("article", "456", "editor", "user", "alice"),
    ("article", "456", "deleter", "user", "tim"),
    ("article", "789", "viewer", "user", "alice"),
    ("article", "101", "viewer", "user", "alice"),
]

SAMPLE_DOCS = [
    Document(
        page_content="Python is a high-level programming language known for its simplicity.",
        metadata={"article_id": "123"},
    ),
    Document(
        page_content="JavaScript is primarily used for web development and runs in browsers.",
        metadata={"article_id": "456"},
    ),
    Document(
        page_content="Machine learning enables computers to learn patterns from data.",
        metadata={"article_id": "789"},
    ),
    Document(
        page_content="SpiceDB is an authorization database based on Google Zanzibar.",
        metadata={"article_id": "101"},
    ),
]


async def setup_spicedb(endpoint: str, token: str, use_tls: bool = False):
    """Write schema and seed relationships so the example is self-contained."""
    creds = bearer_token_credentials(token) if use_tls else insecure_bearer_token_credentials(token)
    client = Client(endpoint, creds)
    await client.WriteSchema(WriteSchemaRequest(schema=SCHEMA))

    # Clear all existing article relationships so this example starts from a known state
    await client.DeleteRelationships(DeleteRelationshipsRequest(
        relationship_filter=RelationshipFilter(resource_type="article")
    ))

    updates = []
    for res_type, res_id, relation, sub_type, sub_id in RELATIONSHIPS:
        updates.append(RelationshipUpdate(
            operation=RelationshipUpdate.OPERATION_TOUCH,
            relationship=Relationship(
                resource=ObjectReference(object_type=res_type, object_id=res_id),
                relation=relation,
                subject=SubjectReference(
                    object=ObjectReference(object_type=sub_type, object_id=sub_id)
                ),
            ),
        ))
    await client.WriteRelationships(WriteRelationshipsRequest(updates=updates))
    print("✓ SpiceDB schema and relationships written")
    print()


class MockVectorStore:
    """
    In-memory vector store for demonstration.

    Accepts Pinecone-style metadata filters:
        {"article_id": {"$in": ["123", "456"]}}

    In production, replace with Pinecone, Chroma, FAISS, Weaviate, etc.
    """

    def __init__(self, docs: list):
        self._docs = {d.metadata["article_id"]: d for d in docs}

    async def asimilarity_search(
        self, query: str, k: int = 4, filter: dict = None, **kwargs
    ) -> list:
        if filter and "article_id" in filter:
            allowed_ids = set(filter["article_id"]["$in"])
            print(f"  → Pre-filter applied: searching only article IDs {sorted(allowed_ids)}")
            candidates = [d for aid, d in self._docs.items() if aid in allowed_ids]
        else:
            print(f"  → No filter: searching all {len(self._docs)} articles")
            candidates = list(self._docs.values())

        query_words = set(query.lower().split())

        def score(doc):
            return len(query_words & set(doc.page_content.lower().split()))

        return sorted(candidates, key=score, reverse=True)[:k]


async def demo_without_openai():
    """Show pre-filter retrieval for multiple users without calling an LLM."""
    print("=" * 80)
    print("SpiceDBPreFilterRetriever Demo - Document Pre-filtering")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    use_tls = os.getenv("SPICEDB_TLS", "false").lower() == "true"

    await setup_spicedb(spicedb_endpoint, spicedb_token, use_tls)

    vector_store = MockVectorStore(SAMPLE_DOCS)

    print(f"Corpus: {len(SAMPLE_DOCS)} articles")
    print("  article 123: Python")
    print("  article 456: JavaScript")
    print("  article 789: Machine Learning")
    print("  article 101: SpiceDB")
    print()
    print("Permissions:")
    print("  tim   can view: 123, 456")
    print("  alice can view: 123, 456, 789, 101")
    print()

    base_retriever = SpiceDBPreFilterRetriever(
        vector_store=vector_store,
        filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
        subject_id="placeholder",
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type="article",
        subject_type="user",
        permission="view",
        use_tls=use_tls,
    )

    for user, query in [
        ("tim", "What programming languages are mentioned?"),
        ("alice", "Tell me about authorization databases"),
    ]:
        print("-" * 60)
        print(f"User: {user}  |  Query: \"{query}\"")
        retriever = base_retriever.with_config(subject_id=user)
        docs = await retriever.ainvoke(query)
        print(f"  Retrieved {len(docs)} document(s):")
        for doc in docs:
            aid = doc.metadata["article_id"]
            print(f"    ✓ article {aid}: {doc.page_content}")
        print()


async def main():
    """Full RAG pipeline with answer generation."""
    print("=" * 80)
    print("SpiceDBPreFilterRetriever Example - Authorization-Aware RAG")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    use_tls = os.getenv("SPICEDB_TLS", "false").lower() == "true"

    await setup_spicedb(spicedb_endpoint, spicedb_token, use_tls)

    vector_store = MockVectorStore(SAMPLE_DOCS)

    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)

    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Answer the question based only on the provided context. "
            "If the context doesn't contain enough information, say so.",
        ),
        ("human", "Question: {question}\n\nContext:\n{context}"),
    ])

    base_retriever = SpiceDBPreFilterRetriever(
        vector_store=vector_store,
        filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
        subject_id="placeholder",
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type="article",
        subject_type="user",
        permission="view",
        use_tls=use_tls,
    )

    for user, query in [
        ("tim", "What programming languages are available?"),
        ("alice", "Tell me about SpiceDB and authorization"),
    ]:
        print()
        print("-" * 80)
        print(f"User: {user}  |  Query: \"{query}\"")
        print("-" * 80)

        retriever = base_retriever.with_config(subject_id=user)

        chain = (
            RunnableParallel({
                "context": retriever | RunnableLambda(format_docs),
                "question": RunnablePassthrough(),
            })
            | prompt
            | llm
            | StrOutputParser()
        )

        answer = await chain.ainvoke(query)
        print(f"\nAnswer:\n{answer}")
        print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print()
    print("Schema and test data are written automatically at startup.")
    print()
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(main())
    else:
        asyncio.run(demo_without_openai())
