"""Unit tests for SpiceDB retrievers.

These tests validate the retriever in isolation using mocks, without requiring
a real SpiceDB instance.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from langchain_core.documents import Document

from langchain_spicedb import SpiceDBPreFilterRetriever
from langchain_spicedb.core import SpiceDBAuthorizer


class TestSpiceDBAuthorizerLookupResources:
    """Unit tests for SpiceDBAuthorizer.lookup_resources."""

    @pytest.mark.asyncio
    async def test_lookup_resources_returns_authorized_ids(self):
        """lookup_resources streams responses and returns resource IDs."""
        with patch("langchain_spicedb.core.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            async def mock_stream():
                responses = [
                    Mock(resource_object_id="123"),
                    Mock(resource_object_id="456"),
                ]
                for r in responses:
                    yield r

            mock_client.LookupResources = Mock(return_value=mock_stream())

            authorizer = SpiceDBAuthorizer(
                spicedb_endpoint="localhost:50051",
                spicedb_token="test_token",
                resource_type="article",
                subject_type="user",
                permission="view",
            )

            result = await authorizer.lookup_resources(subject_id="tim")

            assert result == ["123", "456"]
            mock_client.LookupResources.assert_called_once()
            call_args = mock_client.LookupResources.call_args
            request = call_args[0][0]  # first positional arg
            assert request.permission == "view"
            assert request.resource_object_type == "article"
            assert request.subject.object.object_type == "user"
            assert request.subject.object.object_id == "tim"

    @pytest.mark.asyncio
    async def test_lookup_resources_returns_empty_when_no_access(self):
        """lookup_resources returns [] when the user has no authorized resources."""
        with patch("langchain_spicedb.core.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            async def mock_stream():
                return
                yield  # makes this an async generator; never reached

            mock_client.LookupResources = Mock(return_value=mock_stream())

            authorizer = SpiceDBAuthorizer(
                spicedb_endpoint="localhost:50051",
                spicedb_token="test_token",
                resource_type="article",
            )

            result = await authorizer.lookup_resources(subject_id="tim")

            assert result == []
            mock_client.LookupResources.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_resources_propagates_error(self):
        """lookup_resources raises when SpiceDB call fails."""
        with patch("langchain_spicedb.core.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            async def mock_stream_error():
                raise Exception("SpiceDB timeout")
                yield  # makes this an async generator; never reached

            mock_client.LookupResources = Mock(return_value=mock_stream_error())

            authorizer = SpiceDBAuthorizer(
                spicedb_endpoint="localhost:50051",
                spicedb_token="test_token",
                resource_type="article",
            )

            with pytest.raises(Exception, match="SpiceDB timeout"):
                await authorizer.lookup_resources(subject_id="tim")


class TestSpiceDBPreFilterRetrieverUnit:
    """Unit tests for SpiceDBPreFilterRetriever."""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store that returns one document."""
        mock = AsyncMock()
        mock.asimilarity_search = AsyncMock(
            return_value=[
                Document(page_content="Doc 1", metadata={"article_id": "123"}),
            ]
        )
        return mock

    @pytest.fixture
    def mock_authorizer(self):
        """Mock authorizer returning two authorized IDs."""
        with patch("langchain_spicedb.retrievers.SpiceDBAuthorizer") as mock:
            mock_instance = AsyncMock()
            mock_instance.lookup_resources = AsyncMock(return_value=["123", "456"])
            mock.return_value = mock_instance
            yield mock

    def test_pre_filter_retriever_initialization(self, mock_vector_store, mock_authorizer):
        """SpiceDBPreFilterRetriever stores all config correctly."""
        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )
        assert retriever.subject_id == "tim"
        assert retriever.resource_type == "article"
        assert retriever.permission == "view"
        assert retriever.k == 4

    def test_pre_filter_retriever_is_base_retriever(self):
        """SpiceDBPreFilterRetriever is a LangChain BaseRetriever."""
        from langchain_core.retrievers import BaseRetriever

        assert issubclass(SpiceDBPreFilterRetriever, BaseRetriever)

    @pytest.mark.asyncio
    async def test_lookup_called_then_vector_store_searched(
        self, mock_vector_store, mock_authorizer
    ):
        """Retriever calls lookup_resources first, then similarity_search with filter."""

        def filter_factory(ids):
            return {"filter": {"article_id": {"$in": ids}}}

        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        docs = await retriever.ainvoke("test query")

        mock_authorizer.return_value.lookup_resources.assert_called_once_with(subject_id="tim")
        mock_vector_store.asimilarity_search.assert_called_once_with(
            "test query",
            k=4,
            filter={"article_id": {"$in": ["123", "456"]}},
        )
        assert len(docs) == 1
        assert docs[0].metadata["article_id"] == "123"

    @pytest.mark.asyncio
    async def test_empty_authorized_ids_skips_vector_store(
        self, mock_vector_store, mock_authorizer
    ):
        """When no resources are authorized, returns [] without querying the vector store."""
        mock_authorizer.return_value.lookup_resources = AsyncMock(return_value=[])
        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        docs = await retriever.ainvoke("test query")

        assert docs == []
        mock_vector_store.asimilarity_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_spicedb_error_propagates(self, mock_vector_store, mock_authorizer):
        """SpiceDB errors are raised to the caller, never swallowed."""
        mock_authorizer.return_value.lookup_resources = AsyncMock(
            side_effect=Exception("SpiceDB unavailable")
        )
        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(Exception, match="SpiceDB unavailable"):
            await retriever.ainvoke("test query")

    @pytest.mark.asyncio
    async def test_custom_k_forwarded_to_similarity_search(
        self, mock_vector_store, mock_authorizer
    ):
        """k parameter is forwarded to asimilarity_search."""
        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            k=10,
        )
        assert retriever.k == 10

        await retriever.ainvoke("test query")

        mock_vector_store.asimilarity_search.assert_called_once_with(
            "test query",
            k=10,
            filter={"article_id": {"$in": ["123", "456"]}},
        )

    def test_with_config_returns_new_instance_with_updated_subject(
        self, mock_vector_store, mock_authorizer
    ):
        """with_config creates a new retriever with updated subject_id."""
        retriever = SpiceDBPreFilterRetriever(
            vector_store=mock_vector_store,
            filter_factory=lambda ids: {"filter": {"article_id": {"$in": ids}}},
            subject_id="tim",
            resource_type="article",
            permission="view",
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )
        new_retriever = retriever.with_config(subject_id="alice")
        assert new_retriever.subject_id == "alice"
        assert retriever.subject_id == "tim"  # original unchanged
