"""
SpiceDB Retriever - Pre-filter authorization via LookupResources.

This module provides a LangChain BaseRetriever implementation that uses
SpiceDB's LookupResources API to pre-filter documents before vector search.
"""

from typing import List, Optional, Any, Callable, Dict
from pydantic import ConfigDict
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from .core import SpiceDBAuthorizer


class SpiceDBPreFilterRetriever(BaseRetriever):
    """
    LangChain retriever that pre-filters using SpiceDB's LookupResources API.

    This retriever follows the pre-filter authorization pattern:
    1. Call SpiceDB LookupResources to get all resource IDs the user can access
    2. Pass those IDs through filter_factory to build vector store search kwargs
    3. Run similarity_search with the filter applied
    4. Return only semantically relevant documents the user is authorized to see

    Use pre-filter when users have access to only a small fraction
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
        docs = await self.vector_store.asimilarity_search(query, k=self.k, **search_kwargs)
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
