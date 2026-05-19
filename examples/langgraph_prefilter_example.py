"""
LangGraph Pre-filter Authorization Example

This example builds a LangGraph workflow using create_pre_filter_auth_node.
Unlike the post-filter pattern (retrieve → authorize → generate), the pre-filter
node combines retrieval and authorization into a single step:

  Pre-filter graph:   retrieve_authorized → generate
  Post-filter graph:  retrieve → authorize → generate

The node first calls SpiceDB LookupResources to get the user's authorized article
IDs, then runs a filtered vector store search — so unauthorized documents are
never fetched.

Schema and test data are written automatically at startup.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from authzed.api.v1 import (
    Client, WriteSchemaRequest, WriteRelationshipsRequest, DeleteRelationshipsRequest,
    RelationshipUpdate, Relationship, SubjectReference, ObjectReference, RelationshipFilter,
)
from grpcutil import insecure_bearer_token_credentials, bearer_token_credentials

from langchain_spicedb import create_pre_filter_auth_node, RAGAuthState

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


async def generate_node(state: RAGAuthState) -> dict:
    """Generate answer from authorized documents."""
    docs = state["authorized_documents"]
    print(f"🤖 [generate_node] Generating answer from {len(docs)} authorized docs")

    context = "\n\n".join(doc.page_content for doc in docs)

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from langchain_openai import ChatOpenAI
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Answer the question using only the provided context. Be concise."),
            ("human", "Question: {question}\n\nContext:\n{context}"),
        ])
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        messages = prompt.format_messages(question=state["question"], context=context)
        response = await llm.ainvoke(messages)
        answer = response.content
    else:
        answer = (
            f"[No OpenAI key — showing authorized context directly]\n\n"
            f"Question: {state['question']}\n\n"
            f"Authorized documents ({len(docs)}):\n{context}"
        )

    return {"answer": answer}


async def main():
    print("=" * 80)
    print("LangGraph Pre-filter Authorization Example")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    use_tls = os.getenv("SPICEDB_TLS", "false").lower() == "true"
    subject_id = os.getenv("SUBJECT_ID", "tim")

    await setup_spicedb(spicedb_endpoint, spicedb_token, use_tls)

    vector_store = MockVectorStore(SAMPLE_DOCS)

    # =========================================================================
    # BUILD THE GRAPH
    # =========================================================================

    graph = StateGraph(RAGAuthState)

    # retrieve_authorized replaces both retrieve + authorize from the post-filter pattern
    graph.add_node(
        "retrieve_authorized",
        create_pre_filter_auth_node(
            vector_store=vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type="article",
            subject_type="user",
            permission="view",
            use_tls=use_tls,
        ),
    )
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve_authorized")
    graph.add_edge("retrieve_authorized", "generate")
    graph.add_edge("generate", END)

    app = graph.compile()

    print("✅ Graph compiled successfully!")
    print()

    # =========================================================================
    # METHOD 1: Inspect Graph Nodes
    # =========================================================================

    print("METHOD 1: Inspect Graph Nodes")
    print("-" * 80)

    nodes = list(graph.nodes.keys())
    print(f"Total nodes in graph: {len(nodes)}")
    print(f"Node names: {nodes}")
    print()
    print("Note: pre-filter uses 2 nodes (retrieve_authorized + generate).")
    print("      Post-filter uses 3 nodes (retrieve + authorize + generate).")
    print()

    # =========================================================================
    # METHOD 2: Inspect Graph Edges (Flow)
    # =========================================================================

    print("METHOD 2: Inspect Graph Edges (Execution Flow)")
    print("-" * 80)

    edges = graph.edges
    print("Execution flow:")
    if isinstance(edges, set):
        node_order = {"__start__": 0, "retrieve_authorized": 1, "generate": 2, "__end__": 3}
        sorted_edges = sorted(
            edges, key=lambda e: (node_order.get(e[0], 999), node_order.get(e[1], 999))
        )
        for edge in sorted_edges:
            print(f"  {edge[0]} → {edge[1]}")
    elif isinstance(edges, dict):
        for source, targets in edges.items():
            if isinstance(targets, list):
                for target in targets:
                    print(f"  {source} → {target}")
            else:
                print(f"  {source} → {targets}")
    else:
        print(f"  Edges: {edges}")
    print()

    result = await app.ainvoke(
        {
            "question": "What is Python?",
            "subject_id": subject_id,
        }
    )

    print()
    print("Execution trace:")
    print(
        f"  1. retrieve_authorized → authorized_documents: "
        f"{len(result.get('authorized_documents', []))} docs"
    )
    print(f"  2. generate           → answer: {result.get('answer', 'N/A')}")
    print()

    # =========================================================================
    # METHOD 3: Inspect Authorized Documents
    # =========================================================================

    print("METHOD 3: Authorized Documents")
    print("-" * 80)

    authorized = result.get("authorized_documents", [])
    print(f"Subject '{subject_id}' received {len(authorized)} authorized document(s):")
    for doc in authorized:
        aid = doc.metadata["article_id"]
        print(f"  ✓ article {aid}: {doc.page_content}")

    all_ids = {d.metadata["article_id"] for d in SAMPLE_DOCS}
    authorized_ids = {d.metadata["article_id"] for d in authorized}
    denied_ids = sorted(all_ids - authorized_ids)
    if denied_ids:
        print(f"\nArticles not fetched (not in {subject_id}'s authorized set): {denied_ids}")
    print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print()
    print("Schema and test data are written automatically at startup.")
    print()

    asyncio.run(main())
