"""
SpiceDBPermissionTool Example - Authorization Checks in Agentic Workflows

This example demonstrates how to use SpiceDBPermissionTool to give LangChain agents
the ability to check permissions before performing actions.

The tool allows agents to:
1. Check if a user has specific permissions on resources
2. Make authorization-aware decisions
3. Provide permission-based responses to users
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from authzed.api.v1 import Client, WriteSchemaRequest, WriteRelationshipsRequest, RelationshipUpdate, Relationship, SubjectReference, ObjectReference
from grpcutil import insecure_bearer_token_credentials, bearer_token_credentials

from langchain_spicedb import SpiceDBPermissionTool, SpiceDBBulkPermissionTool

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
                subject=SubjectReference(object=ObjectReference(object_type=sub_type, object_id=sub_id)),
            ),
        ))
    await client.WriteRelationships(WriteRelationshipsRequest(updates=updates))
    print("✓ SpiceDB schema and relationships written")
    print()


async def main():
    print("=" * 80)
    print("SpiceDBPermissionTool Example - Authorization-Aware Agent")
    print("=" * 80)
    print()

    # Configuration
    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")
    use_tls = os.getenv("SPICEDB_TLS", "false").lower() == "true"

    print("Configuration:")
    print(f"  SpiceDB Endpoint: {spicedb_endpoint}")
    print("  Resource Type: article")
    print("  Subject Type: user")
    print()

    await setup_spicedb(spicedb_endpoint, spicedb_token, use_tls)

    # Create SpiceDB permission checking tools
    permission_tool = SpiceDBPermissionTool(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_type="user",
        resource_type="article",
        use_tls=False,
    )

    bulk_permission_tool = SpiceDBBulkPermissionTool(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_type="user",
        resource_type="article",
        use_tls=False,
    )

    # Initialize LLM
    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", temperature=0)

    # Create agent with SpiceDB tools
    tools = [permission_tool, bulk_permission_tool]
    agent = create_agent(
        llm,
        tools,
        system_prompt="""You are a helpful assistant that helps users understand their permissions.

You have access to tools that check permissions in our authorization system (SpiceDB).

When a user asks about accessing resources:
1. Extract ONLY the numeric or alphanumeric ID from the resource reference
   - Example: "article 123" -> use resource_id='123'
   - Example: "articles 123, 456, 789" -> use resource_ids='123,456,789'
   - DO NOT include the resource type in the ID (no 'article-123' or 'article 123')
2. Use the permission tools to check their access
3. Provide clear, helpful responses about what they can and cannot do
4. If they don't have access, politely explain they lack the required permission

Available resource types: article
Available permissions: view, edit, delete
""",
        debug=True,
    )

    print("-" * 80)
    print("Example 1: Checking Single Resource Permission")
    print("-" * 80)
    print()

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Can user alice view article 123?"}]}
    )
    print(f"\nAgent Response:\n{result['messages'][-1].content}")
    print()
    print("=" * 80)
    print()

    print("-" * 80)
    print("Example 2: Checking Multiple Resources")
    print("-" * 80)
    print()

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Which of these articles can user alice view: 123, 456, 789?",
                }
            ]
        }
    )
    print(f"\nAgent Response:\n{result['messages'][-1].content}")
    print()
    print("=" * 80)
    print()

    print("-" * 80)
    print("Example 3: Different Permission Types")
    print("-" * 80)
    print()

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Can user alice edit article 101?"}]}
    )
    print(f"\nAgent Response:\n{result['messages'][-1].content}")
    print()
    print("=" * 80)
    print()

    print("-" * 80)
    print("Example 4: Permission-Based Workflow Decision")
    print("-" * 80)
    print()

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "User bob wants to delete article 456. Check if they have permission and let me know what to tell them.",
                }
            ]
        }
    )
    print(f"\nAgent Response:\n{result['messages'][-1].content}")
    print()
    print("=" * 80)
    print()


async def direct_tool_usage():
    """
    Example showing direct tool usage without an agent
    """
    print("=" * 80)
    print("Direct Tool Usage Example - No Agent Required")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

    # Create the permission tool
    permission_tool = SpiceDBPermissionTool(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_type="user",
        resource_type="article",
    )

    print("Checking permissions directly (no LLM needed):")
    print()

    # Direct async check 1
    print("1. Async check - Can tim view article 123?")
    result = await permission_tool.ainvoke(
        {"subject_id": "tim", "resource_id": "123", "permission": "view"}
    )
    print(f"   Result: {result}")
    print()

    # Direct async check 2
    print("2. Async check - Can alice view article 456?")
    result = await permission_tool.ainvoke(
        {"subject_id": "alice", "resource_id": "456", "permission": "view"}
    )
    print(f"   Result: {result}")
    print()

    # Bulk permission check
    bulk_tool = SpiceDBBulkPermissionTool(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_type="user",
        resource_type="article",
    )

    print("3. Bulk check - Which articles can tim view?")
    result = await bulk_tool.ainvoke(
        {"subject_id": "tim", "resource_ids": "123,456,789", "permission": "view"}
    )
    print(f"   Result: {result}")
    print()

    # Conditional logic based on permissions
    print("4. Using permission check in application logic:")
    user = "tim"
    article = "123"
    can_view = await permission_tool.ainvoke(
        {"subject_id": user, "resource_id": article, "permission": "view"}
    )

    if can_view == "true":
        print(f"   ✓ User {user} has access to article {article}")
        print("   → Proceeding to show article content...")
    else:
        print(f"   ✗ User {user} does NOT have access to article {article}")
        print("   → Returning 403 Forbidden...")
    print()


async def multi_permission_workflow():
    """
    Example showing a workflow that checks multiple permission types
    """
    print("=" * 80)
    print("Multi-Permission Workflow Example")
    print("=" * 80)
    print()

    spicedb_endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    spicedb_token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

    tool = SpiceDBPermissionTool(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        subject_type="user",
        resource_type="article",
    )

    user = "tim"
    article = "123"

    print(f"Checking what user '{user}' can do with article '{article}':")
    print()

    permissions = ["view", "edit", "delete"]
    results = {}

    for permission in permissions:
        result = await tool.ainvoke(
            {"subject_id": user, "resource_id": article, "permission": permission}
        )
        results[permission] = result == "true"
        status = "✓" if results[permission] else "✗"
        print(f"  {status} {permission}")

    print()
    print("Summary:")
    allowed = [p for p, allowed in results.items() if allowed]
    if allowed:
        print(f"  User can: {', '.join(allowed)}")
    else:
        print("  User has no permissions on this article")
    print()


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("1. SpiceDB running on localhost:50051 (or set SPICEDB_ENDPOINT)")
    print("2. Set SPICEDB_TOKEN environment variable")
    print("3. Set OPENAI_API_KEY environment variable (for agent examples)")
    print()
    print("Schema and test data are written automatically at startup.")
    print()
    print("=" * 80)
    print()

    if os.getenv("OPENAI_API_KEY"):
        # Run agent-based examples
        asyncio.run(main())
    else:
        print("OpenAI API key not found. Running examples without agent...")
        print()

    # These examples work without OpenAI
    # asyncio.run(direct_tool_usage())
    # asyncio.run(multi_permission_workflow())
