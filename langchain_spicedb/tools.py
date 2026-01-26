"""
SpiceDB Tools - BaseTool implementations for permission checking in agents.

This module provides LangChain tools that agents can use to check
SpiceDB permissions before taking actions.
"""

from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from .core import SpiceDBAuthorizer


class SpiceDBAuthTool(BaseTool):
    """
    Base class for SpiceDB authorization tools.

    Provides shared configuration and authorizer management for all tools
    that interact with SpiceDB for permission checking.
    """

    spicedb_endpoint: str = Field(default="localhost:50051", description="SpiceDB server address")
    spicedb_token: str = Field(
        default="sometoken", description="Pre-shared key for SpiceDB authentication"
    )
    resource_type: str = Field(default="document", description="SpiceDB resource type")
    subject_type: str = Field(default="user", description="SpiceDB subject type")
    fail_open: bool = Field(default=False, description="If True, allow access on errors")
    use_tls: bool = Field(default=False, description="Whether to use TLS for SpiceDB connection")

    _authorizer: Optional[SpiceDBAuthorizer] = None

    def __init__(
        self,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        fail_open: bool = False,
        use_tls: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize SpiceDB authorization tool.

        Args:
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type (e.g., 'document', 'article')
            subject_type: SpiceDB subject type (e.g., 'user')
            fail_open: If True, allow access on errors
            use_tls: Whether to use TLS for SpiceDB connection
            **kwargs: Additional arguments passed to BaseTool
        """
        # Pass all fields to parent __init__ for Pydantic v2 compatibility
        super().__init__(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            fail_open=fail_open,
            use_tls=use_tls,
            **kwargs,
        )

        # Initialize authorizer after Pydantic validation
        self._authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=self.spicedb_endpoint,
            spicedb_token=self.spicedb_token,
            resource_type=self.resource_type,
            subject_type=self.subject_type,
            permission="view",  # Default, can be overridden per call
            fail_open=self.fail_open,
            use_tls=self.use_tls,
        )


class SpiceDBPermissionInput(BaseModel):
    """Input schema for SpiceDB permission check tool."""

    subject_id: str = Field(
        description="The user ID to check permissions for (e.g., 'alice', 'user-123')"
    )
    resource_id: str = Field(
        description="ONLY the ID portion of the resource, without the type prefix. Examples: '123', 'doc1', 'article-456'. Do NOT include the resource type (e.g., use '123' not 'article 123' or 'article-123')."
    )
    permission: str = Field(
        default="view", description="The permission to check (e.g., 'view', 'edit', 'delete')"
    )


class SpiceDBPermissionTool(SpiceDBAuthTool):
    """
    LangChain tool for checking SpiceDB permissions in agent workflows.

    This tool allows agents to explicitly check whether a user has permission
    to access a resource before retrieving or operating on it.

    Example:
        >>> from langchain.agents import create_agent
        >>> from spicedb_rag_auth import SpiceDBPermissionTool
        >>>
        >>> # Create tool
        >>> permission_tool = SpiceDBPermissionTool(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ... )
        >>>
        >>> # Use in agent
        >>> tools = [permission_tool, other_tools...]
        >>> agent = create_agent(
        ...     llm,
        ...     tools,
        ...     system_prompt="You are a helpful assistant."
        ... )
        >>>
        >>> # Agent can now check permissions before actions
        >>> result = agent.invoke({
        ...     "messages": [{"role": "user", "content": "Can user alice view document doc1?"}]
        ... })
    """

    name: str = "check_spicedb_permission"
    description: str = """
    Check if a user has permission to access a resource in SpiceDB.
    Use this tool before retrieving sensitive documents or taking actions
    that require authorization. Returns 'true' if permission is granted,
    'false' if denied.

    IMPORTANT: resource_id should be ONLY the ID portion, not including the resource type.
    For example, if checking "article 123", use resource_id='123' (not 'article 123').

    Input should be:
    - subject_id: User ID (e.g., 'alice', 'user-123')
    - resource_id: ONLY the ID portion (e.g., '123', 'doc1', 'article-456')
    - permission: Permission to check (e.g., 'view', 'edit')
    """
    args_schema: Type[BaseModel] = SpiceDBPermissionInput

    def _run(
        self,
        subject_id: str,
        resource_id: str,
        permission: str = "view",
    ) -> str:
        """
        Synchronously check if a user has permission for a resource.

        Args:
            subject_id: User ID to check permissions for
            resource_id: Resource ID to check access to
            permission: Permission to check (default: 'view')

        Returns:
            String 'true' if permission granted, 'false' if denied
        """
        import asyncio

        result = asyncio.run(self._arun(subject_id, resource_id, permission))
        return result

    async def _arun(
        self,
        subject_id: str,
        resource_id: str,
        permission: str = "view",
    ) -> str:
        """
        Asynchronously check if a user has permission for a resource.

        Args:
            subject_id: User ID to check permissions for
            resource_id: Resource ID to check access to
            permission: Permission to check (default: 'view')

        Returns:
            String 'true' if permission granted, 'false' if denied
        """
        has_permission = await self._authorizer.check_permission(
            subject_id=subject_id,
            resource_id=resource_id,
            permission=permission,
        )

        return "true" if has_permission else "false"


class SpiceDBBulkPermissionInput(BaseModel):
    """Input schema for bulk permission check tool."""

    subject_id: str = Field(description="The user ID to check permissions for")
    resource_ids: str = Field(
        description="Comma-separated list of resource IDs (ONLY the ID portions, no type prefix). Examples: '123,456,789' or 'doc1,doc2,doc3'. Do NOT include resource type."
    )
    permission: str = Field(default="view", description="The permission to check")


class SpiceDBBulkPermissionTool(SpiceDBAuthTool):
    """
    LangChain tool for checking permissions for multiple resources at once.

    This is useful when an agent needs to check access to multiple documents
    before proceeding with an action.

    Example:
        >>> bulk_tool = SpiceDBBulkPermissionTool(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ... )
        >>>
        >>> # Agent checks multiple documents
        >>> result = bulk_tool._run(
        ...     subject_id="alice",
        ...     resource_ids="doc1,doc2,doc3",
        ...     permission="view"
        ... )
        >>> # Returns: "alice can access: doc1, doc3"
    """

    name: str = "check_spicedb_bulk_permissions"
    description: str = """
    Check if a user has permission to access multiple resources in SpiceDB.
    Returns a comma-separated list of resource IDs the user can access.

    IMPORTANT: resource_ids should be ONLY the ID portions, not including resource type.
    For example, for "articles 123, 456, 789", use resource_ids='123,456,789'.

    Input should be:
    - subject_id: User ID
    - resource_ids: Comma-separated IDs (ONLY ID portions, e.g., '123,456,789')
    - permission: Permission to check (default: 'view')
    """
    args_schema: Type[BaseModel] = SpiceDBBulkPermissionInput

    def _run(
        self,
        subject_id: str,
        resource_ids: str,
        permission: str = "view",
    ) -> str:
        """Check permissions for multiple resources."""
        import asyncio

        result = asyncio.run(self._arun(subject_id, resource_ids, permission))
        return result

    async def _arun(
        self,
        subject_id: str,
        resource_ids: str,
        permission: str = "view",
    ) -> str:
        """Async check permissions for multiple resources."""
        # Parse comma-separated IDs
        ids = [rid.strip() for rid in resource_ids.split(",")]

        # Check permissions in batch
        authorized_ids = await self._authorizer._batch_check_permissions(
            subject_id=subject_id,
            subject_type=self.subject_type,
            resource_ids=ids,
            resource_type=self.resource_type,
            permission=permission,
        )

        if authorized_ids:
            return f"{subject_id} can access: {', '.join(authorized_ids)}"
        else:
            return f"{subject_id} cannot access any of the requested resources"
