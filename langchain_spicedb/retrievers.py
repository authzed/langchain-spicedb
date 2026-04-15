"""
SpiceDB Retriever - BaseRetriever wrapper for authorization filtering.

This module provides LangChain BaseRetriever implementations that wrap
existing retrievers with SpiceDB authorization.
"""

from typing import List, Optional, Any, Callable, Dict
from pydantic import ConfigDict
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


class SpiceDBPreFilterRetriever(BaseRetriever):
    """
    LangChain retriever that pre-filters using SpiceDB's LookupResources API.

    This retriever follows the pre-filter authorization pattern:
    1. Call SpiceDB LookupResources to get all resource IDs the user can access
    2. Pass those IDs through filter_factory to build vector store search kwargs
    3. Run similarity_search with the filter applied
    4. Return only semantically relevant documents the user is authorized to see

    Use this over SpiceDBRetriever when users have access to a small fraction
    of a large corpus and you want to avoid retrieving unauthorized content.

    Example:
        >>> from langchain_spicedb import SpiceDBPreFilterRetriever
        >>>
        >>> retriever = SpiceDBPreFilterRetriever(
        ...     vector_store=knowledge,
        ...     filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
        ...     subject_id="tim",
        ...     resource_type="article",
        ...     permission="view",
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ... )
        >>>
        >>> chain = retriever | prompt | llm
        >>> answer = await chain.ainvoke("What is SpiceDB?")
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    vector_store: Any
    """The vector store to search after pre-filtering by authorized IDs."""

    filter_factory: Callable[[List[str]], Dict[str, Any]]
    """
    Required. Converts a list of authorized resource IDs into search_kwargs
    for the vector store's similarity_search call.

    Example for Pinecone:
        lambda ids: {"filter": {"article_id": {"$in": ids}}}

    Example for Chroma:
        lambda ids: {"where": {"article_id": {"$in": ids}}}
    """

    subject_id: str
    """User ID to look up authorized resources for."""

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

    use_tls: bool = False
    """Whether to use TLS for SpiceDB connection."""

    k: int = 4
    """Number of documents to retrieve from the vector store."""

    _authorizer: Optional[SpiceDBAuthorizer] = None
    """Internal SpiceDB authorizer instance."""

    def __init__(
        self,
        vector_store: Any,
        filter_factory: Callable[[List[str]], Dict[str, Any]],
        subject_id: str,
        spicedb_endpoint: str = "localhost:50051",
        spicedb_token: str = "sometoken",
        resource_type: str = "document",
        subject_type: str = "user",
        permission: str = "view",
        use_tls: bool = False,
        k: int = 4,
        **kwargs: Any,
    ):
        """
        Initialize SpiceDBPreFilterRetriever.

        Args:
            vector_store: The vector store to search (must support asimilarity_search)
            filter_factory: Converts authorized IDs to vector store search_kwargs
            subject_id: User ID to look up authorized resources for
            spicedb_endpoint: SpiceDB server address
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type
            subject_type: SpiceDB subject type
            permission: Permission to check
            use_tls: Whether to use TLS for SpiceDB connection
            k: Number of documents to return from vector store
        """
        super().__init__(
            vector_store=vector_store,
            filter_factory=filter_factory,
            subject_id=subject_id,
            spicedb_endpoint=spicedb_endpoint,
            spicedb_token=spicedb_token,
            resource_type=resource_type,
            subject_type=subject_type,
            permission=permission,
            use_tls=use_tls,
            k=k,
            **kwargs,
        )

        self._authorizer = SpiceDBAuthorizer(
            spicedb_endpoint=self.spicedb_endpoint,
            spicedb_token=self.spicedb_token,
            resource_type=self.resource_type,
            subject_type=self.subject_type,
            permission=self.permission,
            use_tls=self.use_tls,
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Synchronous retrieval — delegates to async implementation."""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Pre-filter then retrieve documents.

        1. LookupResources → authorized_ids
        2. filter_factory(authorized_ids) → search_kwargs
        3. vector_store.asimilarity_search(query, k, **search_kwargs) → docs
        """
        authorized_ids = await self._authorizer.lookup_resources(
            subject_id=self.subject_id,
        )

        if not authorized_ids:
            return []

        search_kwargs = self.filter_factory(authorized_ids)
        docs = await self.vector_store.asimilarity_search(
            query, k=self.k, **search_kwargs
        )
        return docs

    def with_config(
        self,
        subject_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "SpiceDBPreFilterRetriever":
        """
        Create a new retriever with an updated subject_id.

        Args:
            subject_id: New subject ID to use
            **kwargs: Additional fields to update

        Returns:
            New SpiceDBPreFilterRetriever instance
        """
        updates = {"subject_id": subject_id if subject_id is not None else self.subject_id}
        updates.update(kwargs)
        return self.model_copy(update=updates)
