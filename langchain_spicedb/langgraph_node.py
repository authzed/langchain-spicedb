"""
LangGraph node wrapper for SpiceDB authorization.

This module provides functions to create LangGraph-compatible nodes
for SpiceDB authorization that can be added to state graphs.
"""

from typing import Any, Dict, TypedDict, Optional, List
from .core import SpiceDBAuthorizer


class RAGAuthState(TypedDict, total=False):
    """
    Example TypedDict for LangGraph state with SpiceDB authorization.

    You can use this directly or extend it for your own state.

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from spicedb_rag_auth.langgraph import RAGAuthState
        >>>
        >>> graph = StateGraph(RAGAuthState)
        >>> # ... add nodes and edges

    Or extend it:
        >>> class MyCustomState(RAGAuthState):
        ...     custom_field: str
        ...     another_field: int
    """

    # Input fields (required for authorization)
    retrieved_documents: List[Any]
    subject_id: str

    # Output fields (set by authorization node)
    authorized_documents: List[Any]
    auth_results: Dict[str, Any]

    # Optional configuration
    auth_config: Dict[str, Any]

    # Common RAG fields (optional)
    question: str
    context: str
    answer: str


def create_auth_node(
    spicedb_endpoint: str = "localhost:50051",
    spicedb_token: str = "sometoken",
    resource_type: str = "document",
    subject_type: str = "user",
    permission: str = "view",
    resource_id_key: str = "resource_id",
    fail_open: bool = False,
    use_tls: bool = False,
):
    """
    Create a LangGraph node for SpiceDB authorization.

    This function returns an async function that can be added as a node
    to a LangGraph StateGraph.

    Args:
        spicedb_endpoint: SpiceDB server address
        spicedb_token: Pre-shared key for SpiceDB authentication
        resource_type: SpiceDB resource type
        subject_type: SpiceDB subject type
        permission: Permission to check
        resource_id_key: Key in document metadata containing resource ID
        fail_open: If True, allow access on errors
        use_tls: Whether to use TLS for SpiceDB connection

    Returns:
        Async function that can be used as a LangGraph node

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from spicedb_rag_auth.langgraph import create_auth_node
        >>>
        >>> graph = StateGraph(MyState)
        >>> graph.add_node("authorize", create_auth_node(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ... ))
        >>> graph.add_edge("retrieve", "authorize")
        >>> graph.add_edge("authorize", "generate")
    """
    authorizer = SpiceDBAuthorizer(
        spicedb_endpoint=spicedb_endpoint,
        spicedb_token=spicedb_token,
        resource_type=resource_type,
        subject_type=subject_type,
        permission=permission,
        resource_id_key=resource_id_key,
        fail_open=fail_open,
        use_tls=use_tls,
    )

    async def authorization_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node that filters documents based on SpiceDB permissions.

        Expected state keys:
            - retrieved_documents: List of documents to filter
            - subject_id: User ID for authorization

        Optional state keys:
            - auth_config: Dict with optional overrides for resource_type, permission, etc.

        Returns updated state with:
            - authorized_documents: Filtered documents
            - auth_results: Authorization metrics
        """
        # Get documents from state
        documents = state.get("retrieved_documents", [])

        # Get subject ID
        subject_id = state.get("subject_id")
        if not subject_id:
            raise ValueError("subject_id must be present in state")

        # Get optional config overrides
        auth_config = state.get("auth_config", {})
        override_resource_type = auth_config.get("resource_type")
        override_permission = auth_config.get("permission")
        override_subject_type = auth_config.get("subject_type")

        # Filter documents
        result = await authorizer.filter_documents(
            documents=documents,
            subject_id=subject_id,
            resource_type=override_resource_type,
            permission=override_permission,
            subject_type=override_subject_type,
        )

        # Update state
        return {
            "authorized_documents": result.authorized_documents,
            "auth_results": result.to_dict(),
        }

    return authorization_node


class AuthorizationNode:
    """
    Reusable class-based LangGraph node for SpiceDB authorization.

    This provides more flexibility than the function-based approach,
    allowing you to configure and reuse the node across multiple graphs.

    Example:
        >>> auth_node = AuthorizationNode(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ... )
        >>>
        >>> graph = StateGraph(MyState)
        >>> graph.add_node("authorize", auth_node)
        >>> # Reuse in another graph
        >>> graph2 = StateGraph(MyState)
        >>> graph2.add_node("authorize", auth_node)
    """

    def __init__(
        self,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        permission: str = "view",
        resource_id_key: str = "resource_id",
        fail_open: bool = False,
        use_tls: bool = False,
        state_keys: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize authorization node.

        Args:
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type
            subject_type: SpiceDB subject type
            permission: Permission to check
            resource_id_key: Key in document metadata containing resource ID
            fail_open: If True, allow access on errors
            use_tls: Whether to use TLS for SpiceDB connection
            state_keys: Custom state key mappings (e.g., {"documents": "docs"})
        """
        self.authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission=permission,
            resource_id_key=resource_id_key,
            fail_open=fail_open,
            use_tls=use_tls,
        )

        # State key mappings
        default_keys = {
            "documents": "retrieved_documents",
            "subject_id": "subject_id",
            "authorized_documents": "authorized_documents",
            "auth_results": "auth_results",
        }
        self.state_keys = {**default_keys, **(state_keys or {})}

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process state through authorization.

        Args:
            state: LangGraph state dict

        Returns:
            Updated state with authorized documents and metrics
        """
        # Get documents from state
        docs_key = self.state_keys["documents"]
        documents = state.get(docs_key, [])

        # Get subject ID
        subject_key = self.state_keys["subject_id"]
        subject_id = state.get(subject_key)
        if not subject_id:
            raise ValueError(f"{subject_key} must be present in state")

        # Get optional config overrides
        auth_config = state.get("auth_config", {})

        # Filter documents
        result = await self.authorizer.filter_documents(
            documents=documents,
            subject_id=subject_id,
            resource_type=auth_config.get("resource_type"),
            permission=auth_config.get("permission"),
            subject_type=auth_config.get("subject_type"),
        )

        # Update state with custom keys
        auth_docs_key = self.state_keys["authorized_documents"]
        auth_results_key = self.state_keys["auth_results"]

        return {
            auth_docs_key: result.authorized_documents,
            auth_results_key: result.to_dict(),
        }
