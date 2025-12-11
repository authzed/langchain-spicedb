"""
SpiceDB Tools - BaseTool implementations for permission checking in agents.

This module provides LangChain tools that agents can use to check
SpiceDB permissions before taking actions.
"""

from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from .core import SpiceDBAuthorizer


class SpiceDBPermissionInput(BaseModel):
    """Input schema for SpiceDB permission check tool."""

    subject_id: str = Field(
        description="The user ID to check permissions for (e.g., 'alice', 'user-123')"
    )
    resource_id: str = Field(
        description="The resource ID to check access to (e.g., 'doc1', 'article-456')"
    )
    permission: str = Field(
        default="view",
        description="The permission to check (e.g., 'view', 'edit', 'delete')"
    )


class SpiceDBPermissionTool(BaseTool):
    """
    LangChain tool for checking SpiceDB permissions in agent workflows.

    This tool allows agents to explicitly check whether a user has permission
    to access a resource before retrieving or operating on it.

    Example:
        >>> from langchain.agents import create_react_agent
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
        >>> agent = create_react_agent(llm, tools, prompt)
        >>>
        >>> # Agent can now check permissions before actions
        >>> result = agent.invoke({
        ...     "input": "Can user alice view document doc1?"
        ... })
    """

    name: str = "check_spicedb_permission"
    description: str = """
    Check if a user has permission to access a resource in SpiceDB.
    Use this tool before retrieving sensitive documents or taking actions
    that require authorization. Returns 'true' if permission is granted,
    'false' if denied.

    Input should be:
    - subject_id: User ID (e.g., 'alice', 'user-123')
    - resource_id: Resource ID (e.g., 'doc1', 'article-456')
    - permission: Permission to check (e.g., 'view', 'edit')
    """
    args_schema: Type[BaseModel] = SpiceDBPermissionInput

    spicedb_endpoint: str = Field(
        default="localhost:50051",
        description="SpiceDB server address"
    )
    spicedb_token: str = Field(
        default="sometoken",
        description="Pre-shared key for SpiceDB authentication"
    )
    resource_type: str = Field(
        default="document",
        description="SpiceDB resource type"
    )
    subject_type: str = Field(
        default="user",
        description="SpiceDB subject type"
    )
    batch_size: int = Field(
        default=10,
        description="Number of concurrent permission checks"
    )
    fail_open: bool = Field(
        default=False,
        description="If True, allow access on errors"
    )
    use_tls: bool = Field(
        default=False,
        description="Whether to use TLS for SpiceDB connection"
    )

    _authorizer: Optional[SpiceDBAuthorizer] = None

    def __init__(
        self,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        batch_size: int = 10,
        fail_open: bool = False,
        use_tls: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize SpiceDB permission check tool.

        Args:
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type (e.g., 'document', 'article')
            subject_type: SpiceDB subject type (e.g., 'user')
            batch_size: Number of concurrent permission checks
            fail_open: If True, allow access on errors
            use_tls: Whether to use TLS for SpiceDB connection
            **kwargs: Additional arguments passed to BaseTool
        """
        super().__init__(**kwargs)
        self.spicedb_endpoint = spicedb_endpoint
        self.spicedb_token = spicedb_token
        self.resource_type = resource_type
        self.subject_type = subject_type
        self.batch_size = batch_size
        self.fail_open = fail_open
        self.use_tls = use_tls

        # Initialize authorizer
        self._authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission="view",  # Default, can be overridden per call
            batch_size=batch_size,
            fail_open=fail_open,
            use_tls=use_tls,
        )

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

    subject_id: str = Field(
        description="The user ID to check permissions for"
    )
    resource_ids: str = Field(
        description="Comma-separated list of resource IDs to check (e.g., 'doc1,doc2,doc3')"
    )
    permission: str = Field(
        default="view",
        description="The permission to check"
    )


class SpiceDBBulkPermissionTool(BaseTool):
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

    Input should be:
    - subject_id: User ID
    - resource_ids: Comma-separated resource IDs (e.g., 'doc1,doc2,doc3')
    - permission: Permission to check (default: 'view')
    """
    args_schema: Type[BaseModel] = SpiceDBBulkPermissionInput

    spicedb_endpoint: str = "localhost:50051"
    spicedb_token: str = "sometoken"
    resource_type: str = "document"
    subject_type: str = "user"
    batch_size: int = 10
    fail_open: bool = False
    use_tls: bool = False

    _authorizer: Optional[SpiceDBAuthorizer] = None

    def __init__(
        self,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        batch_size: int = 10,
        fail_open: bool = False,
        use_tls: bool = False,
        **kwargs: Any,
    ):
        """Initialize bulk permission check tool."""
        super().__init__(**kwargs)
        self.spicedb_endpoint = spicedb_endpoint
        self.spicedb_token = spicedb_token
        self.resource_type = resource_type
        self.subject_type = subject_type
        self.batch_size = batch_size
        self.fail_open = fail_open
        self.use_tls = use_tls

        self._authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission="view",
            batch_size=batch_size,
            fail_open=fail_open,
            use_tls=use_tls,
        )

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
