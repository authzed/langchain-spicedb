"""
Standalone Example - Using SpiceDB Authorization without any framework

This example shows how to use the authorization agent as a standalone
component, without LangChain or LangGraph.
"""

import asyncio
from spicedb_rag_auth import SpiceDBAuthorizer


# Mock document class for demonstration
class MockDocument:
    def __init__(self, content: str, resource_id: str):
        self.page_content = content
        self.metadata = {"resource_id": resource_id}

    def __repr__(self):
        return f"Document(resource_id={self.metadata['resource_id']}, content={self.page_content[:50]}...)"


async def main():
    print("="*80)
    print("Standalone SpiceDB Authorization Example")
    print("="*80)
    print()

    # Initialize authorizer
    authorizer = SpiceDBAuthorizer(
        spicedb_endpoint="localhost:50051",
        spicedb_token="sometoken",
        resource_type="article",
        subject_type="user",
        permission="view",
        resource_id_key="resource_id",
    )

    # Create sample documents
    documents = [
        MockDocument("Python is a high-level programming language.", "doc1"),
        MockDocument("JavaScript is used for web development.", "doc2"),
        MockDocument("Machine learning is a subset of AI.", "doc3"),
        MockDocument("SpiceDB is an authorization database.", "doc4"),
        MockDocument("LangGraph is a framework for LLM applications.", "doc5"),
    ]

    print(f"Total documents: {len(documents)}")
    print()

    # Test with different users
    users = ["alice", "bob", "charlie"]

    for user in users:
        print(f"Checking permissions for user: {user}")
        print("-" * 80)

        # Filter documents based on permissions
        result = await authorizer.filter_documents(
            documents=documents,
            subject_id=user,
        )

        print(f"Retrieved: {result.total_retrieved}")
        print(f"Authorized: {result.total_authorized}")
        print(f"Authorization Rate: {result.authorization_rate:.1%}")
        print(f"Check Latency: {result.check_latency_ms:.2f}ms")
        print(f"Denied IDs: {result.denied_resource_ids}")
        print()

        print(f"Authorized documents for {user}:")
        for doc in result.authorized_documents:
            print(f"  - {doc.metadata['resource_id']}: {doc.page_content[:60]}...")

        print()
        print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB must be running:")
    print("   docker run --rm -p 50051:50051 authzed/spicedb serve \\")
    print("       --grpc-preshared-key 'sometoken' --grpc-no-tls")
    print()
    print("2. Schema and permissions must be set up")
    print("   (See the README for setup instructions)")
    print()
    print("="*80)
    print()

    asyncio.run(main())
