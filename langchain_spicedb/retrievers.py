"""
SpiceDB Retriever - BaseRetriever wrapper for authorization filtering.

This module provides LangChain BaseRetriever implementations that wrap
existing retrievers with SpiceDB authorization.
"""

from typing import List, Optional, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from .core import SpiceDBAuthorizer


class SpiceDBRetriever(BaseRetriever):
    """
    LangChain retriever that wraps any base retriever with SpiceDB authorization.

    This retriever follows the post-filter authorization pattern:
    1. Retrieve documents from base retriever (semantic search)
    2. Filter through SpiceDB based on user permissions
    3. Return only authorized documents

    Example:
        >>> from langchain_community.vectorstores import FAISS
        >>> from langchain_openai import OpenAIEmbeddings
        >>> from langchain_spicedb import SpiceDBRetriever
        >>>
        >>> # Create base retriever
        >>> vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
        >>> base_retriever = vectorstore.as_retriever()
        >>>
        >>> # Wrap with SpiceDB authorization
        >>> # ALL parameters are required for SpiceDB to make access decisions
        >>> auth_retriever = SpiceDBRetriever(
        ...     base_retriever=base_retriever,
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     subject_id="alice",
        ...     subject_type="user",
        ...     resource_type="article",
        ...     resource_id_key="article_id",
        ...     permission="view",
        ... )
        >>>
        >>> # Use in chain
        >>> chain = auth_retriever | prompt | llm
        >>> answer = chain.invoke("What is SpiceDB?")
    """

    base_retriever: BaseRetriever
    """The underlying retriever to wrap with authorization."""

    subject_id: str
    """User ID to check permissions for."""

    spicedb_endpoint: str = "localhost:50051"
    """SpiceDB server address."""

    spicedb_token: str = "sometoken"
    """Pre-shared key for SpiceDB authentication."""

    resource_type: str = "document"
    """SpiceDB resource type (e.g., 'document', 'article')."""

    subject_type: str = "user"
    """SpiceDB subject type (e.g., 'user')."""

    permission: str = "view"
    """Permission to check (e.g., 'view', 'edit')."""

    resource_id_key: str = "resource_id"
    """Key in document metadata containing resource ID."""

    fail_open: bool = False
    """If True, allow access on errors; if False, deny on errors."""

    use_tls: bool = False
    """Whether to use TLS for SpiceDB connection."""

    _authorizer: Optional[SpiceDBAuthorizer] = None
    """Internal SpiceDB authorizer instance."""

    def __init__(
        self,
        base_retriever: BaseRetriever,
        subject_id: str,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        permission: str = "view",
        resource_id_key: str = "resource_id",
        fail_open: bool = False,
        use_tls: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize SpiceDB retriever.

        Args:
            base_retriever: The retriever to wrap with authorization
            subject_id: User ID to check permissions for
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type
            subject_type: SpiceDB subject type
            permission: Permission to check
            resource_id_key: Key in document metadata containing resource ID
            fail_open: If True, allow access on errors
            use_tls: Whether to use TLS for SpiceDB connection
            **kwargs: Additional arguments passed to BaseRetriever
        """
        # Pass all fields to parent __init__ for Pydantic v2 compatibility
        super().__init__(
            base_retriever=base_retriever,
            subject_id=subject_id,
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission=permission,
            resource_id_key=resource_id_key,
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
            permission=self.permission,
            resource_id_key=self.resource_id_key,
            fail_open=self.fail_open,
            use_tls=self.use_tls,
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Retrieve and filter documents based on SpiceDB permissions.

        Args:
            query: The query string
            run_manager: Callback manager for retriever run

        Returns:
            List of authorized documents
        """
        # This is the sync version - calls async implementation
        import asyncio

        return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Async retrieve and filter documents based on SpiceDB permissions.

        Args:
            query: The query string
            run_manager: Callback manager for retriever run

        Returns:
            List of authorized documents
        """
        # 1. Retrieve documents from base retriever
        if hasattr(self.base_retriever, "_aget_relevant_documents"):
            documents = await self.base_retriever._aget_relevant_documents(
                query, run_manager=run_manager
            )
        else:
            # Fallback to sync if async not available
            documents = self.base_retriever._get_relevant_documents(query, run_manager=run_manager)

        # 2. Filter through SpiceDB
        result = await self._authorizer.filter_documents(
            documents=documents,
            subject_id=self.subject_id,
        )

        # 3. Return authorized documents
        return result.authorized_documents

    def with_config(
        self,
        subject_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "SpiceDBRetriever":
        """
        Create a new retriever with updated configuration.

        Args:
            subject_id: New subject ID to use
            **kwargs: Additional config parameters

        Returns:
            New SpiceDBRetriever instance
        """
        # Use Pydantic's model_copy for cleaner configuration updates
        updates = {"subject_id": subject_id or self.subject_id}
        updates.update(kwargs)
        return self.model_copy(update=updates)
