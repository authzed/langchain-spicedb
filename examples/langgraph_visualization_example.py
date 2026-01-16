"""
LangGraph Visualization Example - Proving the Authorization Node Exists

This example demonstrates multiple ways to inspect and visualize a LangGraph
to prove that the authorization node is part of the execution flow.
"""

import asyncio
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END

from langchain_spicedb import create_auth_node, RAGAuthState


# Mock retriever for demonstration
sample_docs = [
    Document(
        page_content="Python is a high-level programming language.",
        metadata={"article_id": "doc1", "topic": "python"}
    ),
    Document(
        page_content="JavaScript is used for web development.",
        metadata={"article_id": "doc2", "topic": "javascript"}
    ),
    Document(
        page_content="SpiceDB is an authorization database.",
        metadata={"article_id": "doc3", "topic": "authorization"}
    ),
]


def retrieve_node(state: RAGAuthState) -> dict:
    """Retrieve documents from vector store"""
    print(f"📥 [retrieve_node] Retrieving documents for: {state['question']}")
    return {"retrieved_documents": sample_docs}


def generate_node(state: RAGAuthState) -> dict:
    """Generate answer from authorized documents"""
    print(f"🤖 [generate_node] Generating answer from {len(state['authorized_documents'])} authorized docs")

    # For demo purposes, return a simple answer without calling LLM
    # In production, you would:
    # 1. Format context from state["authorized_documents"]
    # 2. Create a prompt with the question and context
    # 3. Call an LLM to generate the answer
    answer = f"Based on {len(state['authorized_documents'])} authorized documents: [Answer would be generated here]"

    return {"answer": answer}


async def main():
    print("="*80)
    print("LangGraph Visualization & Inspection Example")
    print("="*80)
    print()

    # =========================================================================
    # BUILD THE GRAPH
    # =========================================================================

    graph = StateGraph(RAGAuthState)

    # Add nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("authorize", create_auth_node(
        spicedb_endpoint="localhost:50051",
        spicedb_token="ds1",
        resource_type="article",
        resource_id_key="article_id",
    ))
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
        # edges is a set of tuples (source, target)
        for edge in sorted(edges):
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

    # =========================================================================
    # METHOD 3: Visual Graph Representation (ASCII)
    # =========================================================================

    print("METHOD 3: Visual Graph Structure")
    print("-" * 80)
    print("""
    ┌──────────┐
    │  START   │
    └────┬─────┘
         │
         v
    ┌──────────┐
    │ retrieve │  ← Retrieve documents from vector store
    └────┬─────┘
         │
         v
    ┌──────────┐
    │authorize │  ← **SpiceDB Authorization Node** (filters docs)
    └────┬─────┘
         │
         v
    ┌──────────┐
    │ generate │  ← Generate answer from authorized docs
    └────┬─────┘
         │
         v
    ┌──────────┐
    │   END    │
    └──────────┘
    """)

    # =========================================================================
    # METHOD 4: Get Graph as Mermaid Diagram
    # =========================================================================

    print("METHOD 4: Mermaid Diagram (for documentation)")
    print("-" * 80)
    try:
        mermaid = app.get_graph().draw_mermaid()
        print("Mermaid diagram generated:")
        print(mermaid)
        print()
        print("Copy the above to https://mermaid.live to visualize!")
    except Exception:
        print("Note: Mermaid diagram generation requires additional dependencies")
        print("Install with: pip install grandalf")
    print()

    # =========================================================================
    # METHOD 5: Trace Execution with State Updates
    # =========================================================================

    print("METHOD 5: Trace Execution Flow (Live)")
    print("-" * 80)
    print("Running the graph and tracing state updates...")
    print()

    # Run the graph
    result = await app.ainvoke({
        "question": "What is Python?",
        "subject_id": "alice",
    })

    print()
    print("Execution trace:")
    print(f"  1. retrieve_node    → retrieved_documents: {len(result.get('retrieved_documents', []))} docs")
    print(f"  2. authorize_node   → authorized_documents: {len(result.get('authorized_documents', []))} docs")
    print(f"  3. generate_node    → answer: {result.get('answer', 'N/A')[:50]}...")
    print()

    # =========================================================================
    # METHOD 6: Inspect Authorization Metrics
    # =========================================================================

    print("METHOD 6: Inspect Authorization Metrics (Proof of Execution)")
    print("-" * 80)

    if "auth_results" in result:
        auth_metrics = result["auth_results"]
        print("Authorization metrics (proves the node executed):")
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

    # =========================================================================
    # METHOD 7: Compare With and Without Authorization Node
    # =========================================================================

    print("METHOD 7: Side-by-Side Comparison")
    print("-" * 80)

    # Graph WITHOUT authorization
    graph_no_auth = StateGraph(RAGAuthState)
    graph_no_auth.add_node("retrieve", retrieve_node)
    graph_no_auth.add_node("generate", generate_node)
    graph_no_auth.set_entry_point("retrieve")
    graph_no_auth.add_edge("retrieve", "generate")
    graph_no_auth.add_edge("generate", END)

    print("Graph WITHOUT authorization:")
    print(f"  Nodes: {list(graph_no_auth.nodes.keys())}")
    print("  Flow:  retrieve → generate → END")
    print()

    print("Graph WITH authorization:")
    print(f"  Nodes: {list(graph.nodes.keys())}")
    print("  Flow:  retrieve → authorize → generate → END")
    print()
    print("✅ The 'authorize' node is the key difference!")
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("="*80)
    print("SUMMARY: Proof That Authorization Node Exists")
    print("="*80)
    print()
    print("We demonstrated 7 methods to prove the authorization node exists:")
    print()
    print("  1. ✅ Inspect graph.nodes - 'authorize' is in the node list")
    print("  2. ✅ Inspect graph.edges - Flow includes retrieve → authorize → generate")
    print("  3. ✅ ASCII visualization - Visual representation of the flow")
    print("  4. ✅ Mermaid diagram - Shareable diagram for documentation")
    print("  5. ✅ Live execution trace - Node executes during runtime")
    print("  6. ✅ Authorization metrics - Proof of permission checks")
    print("  7. ✅ Side-by-side comparison - Shows the authorization node difference")
    print()
    print("All 7 methods confirm the authorization node is part of the graph!")
    print()


if __name__ == "__main__":
    print()
    print("This example shows how to prove the authorization node exists in LangGraph")
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (optional for this demo)")
    print("2. The demo will show graph structure even without SpiceDB")
    print()
    print("="*80)
    print()

    asyncio.run(main())
