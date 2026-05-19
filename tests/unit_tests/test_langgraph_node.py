"""Unit tests for LangGraph authorization nodes."""
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.documents import Document

from langchain_spicedb import create_pre_filter_auth_node


class TestCreatePreFilterAuthNode:
    """Unit tests for create_pre_filter_auth_node."""

    @pytest.fixture
    def mock_vector_store(self):
        mock = AsyncMock()
        mock.asimilarity_search = AsyncMock(return_value=[
            Document(page_content="Doc 1", metadata={"article_id": "123"}),
        ])
        return mock

    @pytest.fixture
    def filter_factory(self):
        return lambda ids: {"filter": {"article_id": {"$in": ids}}}

    @pytest.fixture
    def mock_authorizer(self):
        with patch("langchain_spicedb.langgraph_node.SpiceDBAuthorizer") as mock:
            mock_instance = AsyncMock()
            mock_instance.lookup_resources = AsyncMock(return_value=["123", "456"])
            mock.return_value = mock_instance
            yield mock

    def test_returns_callable(self, mock_vector_store, filter_factory, mock_authorizer):
        """create_pre_filter_auth_node returns a callable node."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )
        assert callable(node)

    @pytest.mark.asyncio
    async def test_node_calls_lookup_with_subject_id_from_state(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node reads subject_id from state and passes it to lookup_resources."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        await node({"subject_id": "alice", "question": "What is SpiceDB?"})

        mock_authorizer.return_value.lookup_resources.assert_called_once_with(subject_id="alice")

    @pytest.mark.asyncio
    async def test_node_calls_vector_store_with_filter_and_question(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node passes question + filter_factory output to asimilarity_search."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            k=4,
        )

        await node({"subject_id": "alice", "question": "What is SpiceDB?"})

        mock_vector_store.asimilarity_search.assert_called_once_with(
            "What is SpiceDB?",
            k=4,
            filter={"article_id": {"$in": ["123", "456"]}},
        )

    @pytest.mark.asyncio
    async def test_node_returns_authorized_documents_in_state(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node returns a state update dict with authorized_documents key."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        result = await node({"subject_id": "alice", "question": "What is SpiceDB?"})

        assert "authorized_documents" in result
        assert len(result["authorized_documents"]) == 1
        assert result["authorized_documents"][0].metadata["article_id"] == "123"

    @pytest.mark.asyncio
    async def test_empty_authorized_ids_returns_empty_without_calling_vector_store(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """When lookup_resources returns [], node returns [] without querying the vector store."""
        mock_authorizer.return_value.lookup_resources = AsyncMock(return_value=[])

        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        result = await node({"subject_id": "alice", "question": "What is SpiceDB?"})

        assert result == {"authorized_documents": []}
        mock_vector_store.asimilarity_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_subject_id_missing_from_state(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node raises ValueError when subject_id is absent from state."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(ValueError, match="subject_id"):
            await node({"question": "What is SpiceDB?"})

    @pytest.mark.asyncio
    async def test_raises_when_question_missing_from_state(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node raises ValueError when question is absent from state."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(ValueError, match="question"):
            await node({"subject_id": "alice"})

    @pytest.mark.asyncio
    async def test_raises_when_subject_id_is_empty_string(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node raises ValueError when subject_id is an empty string."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(ValueError, match="subject_id"):
            await node({"subject_id": "", "question": "What is SpiceDB?"})

    @pytest.mark.asyncio
    async def test_raises_when_question_is_empty_string(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """Node raises ValueError when question is an empty string."""
        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(ValueError, match="question"):
            await node({"subject_id": "alice", "question": ""})

    @pytest.mark.asyncio
    async def test_spicedb_error_propagates(
        self, mock_vector_store, filter_factory, mock_authorizer
    ):
        """SpiceDB errors from lookup_resources propagate to the caller."""
        mock_authorizer.return_value.lookup_resources = AsyncMock(
            side_effect=Exception("SpiceDB unavailable")
        )

        node = create_pre_filter_auth_node(
            vector_store=mock_vector_store,
            filter_factory=filter_factory,
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
        )

        with pytest.raises(Exception, match="SpiceDB unavailable"):
            await node({"subject_id": "alice", "question": "What is SpiceDB?"})
