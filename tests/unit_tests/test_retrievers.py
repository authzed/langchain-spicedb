"""Unit tests for SpiceDBRetriever.

These tests validate the retriever in isolation using mocks, without requiring
a real SpiceDB instance.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from langchain_spicedb import SpiceDBRetriever


class MockRetriever(BaseRetriever):
    """Mock retriever for testing."""

    def _get_relevant_documents(self, query: str, run_manager=None):
        """Synchronous retrieval."""
        return [
            Document(page_content="Doc 1", metadata={"article_id": "123"}),
            Document(page_content="Doc 2", metadata={"article_id": "456"}),
            Document(page_content="Doc 3", metadata={"article_id": "789"}),
        ]

    async def _aget_relevant_documents(self, query: str, run_manager=None):
        """Asynchronous retrieval."""
        return self._get_relevant_documents(query)


class TestSpiceDBRetrieverUnit:
    """Unit tests for SpiceDBRetriever."""

    @pytest.fixture
    def mock_base_retriever(self):
        """Create a mock base retriever."""
        return MockRetriever()

    @pytest.fixture
    def mock_authorizer(self):
        """Create a mock SpiceDB authorizer."""
        with patch("langchain_spicedb.retrievers.SpiceDBAuthorizer") as mock:
            mock_instance = AsyncMock()
            # filter_documents returns an AuthorizationResult object with authorized_documents attribute
            mock_result = Mock()
            mock_result.authorized_documents = [
                Document(page_content="Doc 1", metadata={"article_id": "123"}),
            ]
            mock_instance.filter_documents = AsyncMock(return_value=mock_result)
            mock.return_value = mock_instance
            yield mock

    def test_retriever_initialization(self, mock_base_retriever, mock_authorizer):
        """Test that SpiceDBRetriever initializes correctly."""
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        assert retriever.base_retriever == mock_base_retriever
        assert retriever.subject_id == "alice"
        assert retriever.subject_type == "user"
        assert retriever.resource_type == "article"
        assert retriever.permission == "view"

    def test_retriever_inherits_from_base_retriever(self):
        """Test that SpiceDBRetriever is a BaseRetriever."""
        assert issubclass(SpiceDBRetriever, BaseRetriever)

    def test_synchronous_retrieval(self, mock_base_retriever, mock_authorizer):
        """Test synchronous document retrieval and filtering."""
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        docs = retriever.invoke("test query")

        # Verify base retriever was called
        assert len(docs) == 1
        assert docs[0].metadata["article_id"] == "123"

        # Verify authorizer was called with correct documents
        mock_authorizer.return_value.filter_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_asynchronous_retrieval(self, mock_base_retriever, mock_authorizer):
        """Test asynchronous document retrieval and filtering."""
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        docs = await retriever.ainvoke("test query")

        # Verify base retriever was called
        assert len(docs) == 1
        assert docs[0].metadata["article_id"] == "123"

        # Verify authorizer was called with correct documents
        # Note: filter_documents is the async method (not afilter_documents)
        mock_authorizer.return_value.filter_documents.assert_called_once()

    def test_batch_retrieval(self, mock_base_retriever, mock_authorizer):
        """Test batch document retrieval."""
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        results = retriever.batch(["query1", "query2"])

        assert len(results) == 2
        for docs in results:
            assert len(docs) == 1
            assert docs[0].metadata["article_id"] == "123"

    @pytest.mark.asyncio
    async def test_async_batch_retrieval(self, mock_base_retriever, mock_authorizer):
        """Test asynchronous batch document retrieval."""
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        results = await retriever.abatch(["query1", "query2"])

        assert len(results) == 2
        for docs in results:
            assert len(docs) == 1
            assert docs[0].metadata["article_id"] == "123"

    def test_empty_results(self, mock_base_retriever, mock_authorizer):
        """Test handling of empty authorization results."""
        # Configure authorizer to return empty list
        empty_result = Mock()
        empty_result.authorized_documents = []
        mock_authorizer.return_value.filter_documents.return_value = empty_result

        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="bob",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
        )

        docs = retriever.invoke("test query")

        assert len(docs) == 0

    def test_missing_metadata_key(self, mock_base_retriever, mock_authorizer):
        """Test handling of documents with missing metadata keys."""
        # Create retriever with different resource_id_key
        retriever = SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_id="alice",
            subject_type="user",
            resource_type="article",
            resource_id_key="nonexistent_key",
            permission="view",
        )

        # Should not raise error, authorizer handles missing keys
        docs = retriever.invoke("test query")
        assert isinstance(docs, list)

    def test_retriever_with_different_permissions(
        self, mock_base_retriever, mock_authorizer
    ):
        """Test retriever with different permission types."""
        for permission in ["view", "edit", "delete", "admin"]:
            retriever = SpiceDBRetriever(
                base_retriever=mock_base_retriever,
                spicedb_endpoint="localhost:50051",
                spicedb_token="test_token",
                subject_id="alice",
                subject_type="user",
                resource_type="article",
                resource_id_key="article_id",
                permission=permission,
            )

            assert retriever.permission == permission

    def test_retriever_with_different_subject_types(
        self, mock_base_retriever, mock_authorizer
    ):
        """Test retriever with different subject types."""
        for subject_type in ["user", "service", "organization"]:
            retriever = SpiceDBRetriever(
                base_retriever=mock_base_retriever,
                spicedb_endpoint="localhost:50051",
                spicedb_token="test_token",
                subject_id="alice",
                subject_type=subject_type,
                resource_type="article",
                resource_id_key="article_id",
                permission="view",
            )

            assert retriever.subject_type == subject_type

    def test_retriever_parameters_passed_to_authorizer(
        self, mock_base_retriever, mock_authorizer
    ):
        """Test that retriever parameters are correctly passed to authorizer."""
        SpiceDBRetriever(
            base_retriever=mock_base_retriever,
            spicedb_endpoint="custom:50051",
            spicedb_token="custom_token",
            subject_id="alice",
            subject_type="user",
            resource_type="document",
            resource_id_key="doc_id",
            permission="edit",
            batch_size=20,
            fail_open=True,
            use_tls=True,
        )

        # Verify authorizer was initialized
        mock_authorizer.assert_called_once()

        # Verify key parameters were passed (handle both positional and keyword args)
        call_args = mock_authorizer.call_args
        # call_args is a tuple of (args, kwargs) or call object
        if hasattr(call_args, 'kwargs'):
            call_kwargs = call_args.kwargs
        else:
            call_kwargs = call_args[1] if len(call_args) > 1 else call_args[0]

        assert call_kwargs.get("spicedb_endpoint") == "custom:50051"
        assert call_kwargs.get("spicedb_token") == "custom_token"
        assert call_kwargs.get("subject_type") == "user"
        assert call_kwargs.get("resource_type") == "document"
        assert call_kwargs.get("permission") == "edit"
