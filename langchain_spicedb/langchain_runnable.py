"""
LangChain Runnable wrapper for SpiceDB authorization.

This module provides a LangChain Runnable interface to the SpiceDB authorizer,
allowing it to be seamlessly integrated into LangChain chains.
"""

from typing import Any, Dict, List, Optional, Union
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.documents import Document
from .core import SpiceDBAuthorizer, AuthorizationResult


class SpiceDBAuthFilter(Runnable):
    """
    LangChain Runnable for SpiceDB authorization filtering.

    This class wraps the SpiceDB authorizer as a LangChain Runnable,
    allowing it to be used in chains with the pipe operator (|).

    Example:
        >>> # ALL parameters are required for SpiceDB to make access decisions
        >>> auth = SpiceDBAuthFilter(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     subject_type="user",
        ...     resource_type="article",
        ...     resource_id_key="article_id",
        ...     permission="view",
        ... )
        >>>
        >>> # Use in a chain
        >>> chain = retriever | auth | prompt | llm
        >>>
        >>> # Pass subject_id in config at runtime
        >>> result = await chain.ainvoke(
        ...     "What is SpiceDB?",
        ...     config={"configurable": {"subject_id": "alice"}}
        ... )
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
        subject_id: Optional[str] = None,
        return_metrics: bool = False,
    ):
        """
        Initialize SpiceDB authorization filter.

        Args:
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type (e.g., "document", "article")
            subject_type: SpiceDB subject type (e.g., "user")
            permission: Permission to check (e.g., "view", "edit")
            resource_id_key: Key in document metadata containing resource ID
            fail_open: If True, allow access on errors
            use_tls: Whether to use TLS for SpiceDB connection
            subject_id: Default subject ID (can be overridden in config)
            return_metrics: If True, return AuthorizationResult instead of just docs
        """
        super().__init__()
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
        self.default_subject_id = subject_id
        self.return_metrics = return_metrics

    def invoke(
        self,
        input: Union[List[Document], Dict[str, Any]],
        config: Optional[RunnableConfig] = None,
    ) -> Union[List[Document], AuthorizationResult]:
        """
        Synchronous invocation (not recommended, use ainvoke instead).
        """
        import asyncio

        return asyncio.run(self.ainvoke(input, config))

    async def ainvoke(
        self,
        input: Union[List[Document], Dict[str, Any]],
        config: Optional[RunnableConfig] = None,
    ) -> Union[List[Document], AuthorizationResult]:
        """
        Filter documents based on SpiceDB permissions.

        Args:
            input: Either a list of documents or a dict with "documents" key
            config: Runnable config that may contain subject_id in configurable

        Returns:
            Filtered documents or AuthorizationResult if return_metrics=True
        """
        # Extract documents from input
        if isinstance(input, list):
            documents = input
        elif isinstance(input, dict):
            documents = input.get("documents", input.get("docs", []))
        else:
            raise ValueError(f"Unsupported input type: {type(input)}")

        # Get subject_id from config or use default
        subject_id = self._get_subject_id(config)

        if not subject_id:
            raise ValueError(
                "subject_id must be provided either in constructor or in config. "
                "Example: config={'configurable': {'subject_id': 'alice'}}"
            )

        # Filter documents
        result = await self.authorizer.filter_documents(
            documents=documents,
            subject_id=subject_id,
        )

        # Return based on return_metrics flag
        if self.return_metrics:
            return result
        else:
            return result.authorized_documents

    def _get_subject_id(self, config: Optional[RunnableConfig]) -> Optional[str]:
        """Extract subject_id from config or use default."""
        if config and "configurable" in config:
            subject_id = config["configurable"].get("subject_id")
            if subject_id:
                return subject_id
        return self.default_subject_id

    def with_config(self, subject_id: Optional[str] = None, **kwargs) -> "SpiceDBAuthFilter":
        """
        Create a new instance with updated configuration.

        Args:
            subject_id: Subject ID to use for authorization
            **kwargs: Additional config parameters

        Returns:
            New SpiceDBAuthFilter instance with updated config
        """
        new_filter = SpiceDBAuthFilter(
            spicedb_endpoint=self.authorizer.spicedb_endpoint,
            spicedb_token=self.authorizer.spicedb_token,
            resource_type=self.authorizer.resource_type,
            subject_type=self.authorizer.subject_type,
            permission=self.authorizer.permission,
            resource_id_key=self.authorizer.resource_id_key,
            fail_open=self.authorizer.fail_open,
            use_tls=self.authorizer.use_tls,
            subject_id=subject_id or self.default_subject_id,
            return_metrics=self.return_metrics,
        )
        return new_filter


class SpiceDBAuthLambda:
    """
    Lightweight wrapper for use with RunnableLambda.

    This is useful when you want to use the authorization filter
    in a RunnableLambda context without the full Runnable interface.

    Example:
        >>> auth = SpiceDBAuthLambda(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ...     subject_id="alice",
        ... )
        >>>
        >>> chain = (
        ...     RunnableParallel({
        ...         "context": retriever | RunnableLambda(auth),
        ...         "question": RunnablePassthrough(),
        ...     })
        ...     | prompt
        ...     | llm
        ... )
    """

    def __init__(
        self,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        permission: str = "view",
        resource_id_key: str = "resource_id",
        subject_id: str = None,
        fail_open: bool = False,
    ):
        """Initialize the authorization lambda."""
        self.authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission=permission,
            resource_id_key=resource_id_key,
            fail_open=fail_open,
        )
        self.subject_id = subject_id

    async def __call__(self, documents: List[Document]) -> List[Document]:
        """
        Filter documents based on SpiceDB permissions.

        Args:
            documents: List of documents to filter

        Returns:
            List of authorized documents
        """
        if not self.subject_id:
            raise ValueError("subject_id must be set")

        result = await self.authorizer.filter_documents(
            documents=documents,
            subject_id=self.subject_id,
        )

        return result.authorized_documents
