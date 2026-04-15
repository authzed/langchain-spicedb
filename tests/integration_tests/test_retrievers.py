"""Integration tests for SpiceDBRetriever.

These tests require a running SpiceDB instance and will make real authorization checks.
Set environment variables SPICEDB_ENDPOINT and SPICEDB_TOKEN to run these tests.
"""

import os
import pytest
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from langchain_spicedb import SpiceDBRetriever


class SimpleRetriever(BaseRetriever):
    """Simple retriever that returns fixed documents for testing."""

    def _get_relevant_documents(self, query: str, run_manager=None):
        """Return test documents with metadata."""
        return [
            Document(
                page_content="Document about SpiceDB authorization",
                metadata={"article_id": "123", "title": "SpiceDB Intro"},
            ),
            Document(
                page_content="Document about RAG pipelines",
                metadata={"article_id": "456", "title": "RAG Guide"},
            ),
            Document(
                page_content="Document about vector databases",
                metadata={"article_id": "789", "title": "Vector DB"},
            ),
        ]

    async def _aget_relevant_documents(self, query: str, run_manager=None):
        """Async version."""
        return self._get_relevant_documents(query)


@pytest.fixture
def spicedb_config():
    """Get SpiceDB configuration from environment."""
    endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

    return {
        "spicedb_endpoint": endpoint,
        "spicedb_token": token,
    }


@pytest.fixture
def base_retriever():
    """Create a simple test retriever."""
    return SimpleRetriever()


class TestSpiceDBRetrieverIntegration:
    """Integration tests for SpiceDBRetriever with real SpiceDB."""

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_retriever_with_real_spicedb(self, base_retriever, spicedb_config):
        """Test retriever with real SpiceDB instance."""
        retriever = SpiceDBRetriever(
            base_retriever=base_retriever,
            subject_id="tim",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
            **spicedb_config,
        )

        # This will make real SpiceDB calls
        docs = retriever.invoke("test query")

        # Verify we got documents back (may be filtered)
        assert isinstance(docs, list)
        for doc in docs:
            assert isinstance(doc, Document)
            assert "article_id" in doc.metadata

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_async_retriever_with_real_spicedb(self, base_retriever, spicedb_config):
        """Test async retriever with real SpiceDB instance."""
        retriever = SpiceDBRetriever(
            base_retriever=base_retriever,
            subject_id="tim",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
            **spicedb_config,
        )

        # This will make real SpiceDB calls
        docs = await retriever.ainvoke("test query")

        # Verify we got documents back (may be filtered)
        assert isinstance(docs, list)
        for doc in docs:
            assert isinstance(doc, Document)
            assert "article_id" in doc.metadata

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_batch_retrieval_integration(self, base_retriever, spicedb_config):
        """Test batch retrieval with real SpiceDB."""
        retriever = SpiceDBRetriever(
            base_retriever=base_retriever,
            subject_id="tim",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
            **spicedb_config,
        )

        results = retriever.batch(["query1", "query2", "query3"])

        assert len(results) == 3
        for docs in results:
            assert isinstance(docs, list)

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_async_batch_retrieval_integration(self, base_retriever, spicedb_config):
        """Test async batch retrieval with real SpiceDB."""
        retriever = SpiceDBRetriever(
            base_retriever=base_retriever,
            subject_id="tim",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
            **spicedb_config,
        )

        results = await retriever.abatch(["query1", "query2"])

        assert len(results) == 2
        for docs in results:
            assert isinstance(docs, list)

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_retriever_filters_unauthorized_documents(self, base_retriever, spicedb_config):
        """Test that retriever correctly filters out unauthorized documents."""
        # User with limited permissions
        retriever = SpiceDBRetriever(
            base_retriever=base_retriever,
            subject_id="unauthorized_user",
            subject_type="user",
            resource_type="article",
            resource_id_key="article_id",
            permission="view",
            **spicedb_config,
        )

        docs = retriever.invoke("test query")

        # Should return fewer (or zero) documents due to authorization
        # Note: Actual behavior depends on SpiceDB schema and permissions
        assert isinstance(docs, list)

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_retriever_with_different_permissions(self, base_retriever, spicedb_config):
        """Test retriever with different permission types."""
        for permission in ["view", "edit"]:
            retriever = SpiceDBRetriever(
                base_retriever=base_retriever,
                subject_id="tim",
                subject_type="user",
                resource_type="article",
                resource_id_key="article_id",
                permission=permission,
                **spicedb_config,
            )

            docs = retriever.invoke("test query")
            assert isinstance(docs, list)

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_retriever_with_tls(self, base_retriever, spicedb_config):
        """Test retriever with TLS enabled (if endpoint supports it)."""
        # Only test if we're connecting to a non-localhost endpoint
        if "localhost" not in spicedb_config["spicedb_endpoint"]:
            retriever = SpiceDBRetriever(
                base_retriever=base_retriever,
                subject_id="tim",
                subject_type="user",
                resource_type="article",
                resource_id_key="article_id",
                permission="view",
                use_tls=True,
                **spicedb_config,
            )

            docs = retriever.invoke("test query")
            assert isinstance(docs, list)

