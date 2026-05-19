"""
LangGraph Authorization Example - Inspecting and Running an Authorized RAG Graph

This example builds a LangGraph workflow with SpiceDB authorization, inspects
its structure, and runs it live against a real SpiceDB instance.

Schema and test data are written automatically at startup.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from authzed.api.v1 import (
    Client, WriteSchemaRequest, WriteRelationshipsRequest,
    RelationshipUpdate, Relationship, SubjectReference, ObjectReference,
)
from grpcutil import insecure_bearer_token_credentials, bearer_token_credentials

from langchain_spicedb import create_auth_node, RAGAuthState

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
    ("article", "123", "viewer", "user", "alice"),
    ("article", "101", "viewer", "user", "alice"),
]


async def setup_spicedb(endpoint: str, token: str, use_tls: bool = False):
    """Write schema and seed relationships so the example is self-contained."""
    creds = bearer_token_credentials(token) if use_tls else insecure_bearer_token_credentials(token)
    client = Client(endpoint, creds)
    await client.WriteSchema(WriteSchemaRequest(schema=SCHEMA))

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


# Mock retriever for demonstration
sample_docs = [
    Document(
        page_content="Python is a high-level programming language.",
        metadata={"article_id": "123", "topic": "python"},
    ),
    Document(
        page_content="JavaScript is used for web development.",
        metadata={"article_id": "456", "topic": "javascript"},
    ),
    Document(
        page_content="SpiceDB is an authorization database.",
        metadata={"article_id": "101", "topic": "authorization"},
    ),
]


def retrieve_node(state: RAGAuthState) -> dict:
    """Retrieve documents from vector store"""
    print(f"📥 [retrieve_node] Retrieving documents for: {state['question']}")
    return {"retrieved_documents": sample_docs}


async def generate_node(state: RAGAuthState) -> dict:
    """Generate answer from authorized documents"""
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
    print("LangGraph Visualization & Inspection Example")
    print("=" * 80)
    print()

    # Configuration
    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    use_tls = os.getenv("SPICEDB_TLS", "false").lower() == "true"
    subject_id = os.getenv("SUBJECT_ID", "alice")

    await setup_spicedb(spicedb_endpoint, spicedb_token, use_tls)

    # =========================================================================
    # BUILD THE GRAPH
    # =========================================================================

    graph = StateGraph(RAGAuthState)

    # Add nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node(
        "authorize",
        create_auth_node(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type="article",
            resource_id_key="article_id",
        ),
    )
    graph.add_node("generate", generate_node)

    # Add edges
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "authorize")
    graph.add_edge("authorize", "generate")
    graph.add_edge("generate", END)

    # Compile
    app = graph.compile()

    print("✅ Graph compiled successfully!")
    print()

    # =========================================================================
    # METHOD 1: Inspect Graph Structure
    # =========================================================================

    print("METHOD 1: Inspect Graph Nodes")
    print("-" * 80)

    # Get all nodes in the graph
    nodes = list(graph.nodes.keys())
    print(f"Total nodes in graph: {len(nodes)}")
    print(f"Node names: {nodes}")
    print()

    # Check if authorization node exists
    if "authorize" in nodes:
        print("✅ Authorization node EXISTS in the graph")
    else:
        print("❌ Authorization node NOT FOUND")
    print()

    # =========================================================================
    # METHOD 2: Inspect Graph Edges (Flow)
    # =========================================================================

    print("METHOD 2: Inspect Graph Edges (Execution Flow)")
    print("-" * 80)

    # Show the execution flow
    edges = graph.edges
    print("Execution flow:")
    if isinstance(edges, set):
        # Sort edges in execution order (topological sort approximation)
        # Order nodes by their position in the flow
        node_order = {"__start__": 0, "retrieve": 1, "authorize": 2, "generate": 3, "__end__": 4}
        sorted_edges = sorted(
            edges, key=lambda e: (node_order.get(e[0], 999), node_order.get(e[1], 999))
        )
        for edge in sorted_edges:
            print(f"  {edge[0]} → {edge[1]}")
    elif isinstance(edges, dict):
        # edges is a dict {source: target(s)}
        for source, targets in edges.items():
            if isinstance(targets, list):
                for target in targets:
                    print(f"  {source} → {target}")
            else:
                print(f"  {source} → {targets}")
    else:
        print(f"  Edges: {edges}")
    print()

    # Run the graph
    result = await app.ainvoke(
        {
            "question": "What is Python?",
            "subject_id": subject_id,
        }
    )

    print()
    print("Execution trace:")
    print(
        f"  1. retrieve_node    → retrieved_documents: {len(result.get('retrieved_documents', []))} docs"
    )
    print(
        f"  2. authorize_node   → authorized_documents: {len(result.get('authorized_documents', []))} docs"
    )
    answer_preview = result.get("answer", "N/A")
    print(f"  3. generate_node    → answer: {answer_preview}")
    print()

    # =========================================================================
    # METHOD 3: Inspect Authorization Metrics
    # =========================================================================

    print("METHOD 3: Inspect Authorization Metrics")
    print("-" * 80)

    if "auth_results" in result:
        auth_metrics = result["auth_results"]
        print(f"  Total retrieved:     {auth_metrics['total_retrieved']}")
        print(f"  Total authorized:    {auth_metrics['total_authorized']}")
        print(f"  Authorization rate:  {auth_metrics['authorization_rate']:.1%}")
        print(f"  Check latency:       {auth_metrics['check_latency_ms']:.2f}ms")
        print(f"  Denied resource IDs: {auth_metrics['denied_resource_ids']}")
        print()
        print("✅ Authorization node executed successfully!")
    else:
        print("❌ No authorization metrics found (node may not have executed)")
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
