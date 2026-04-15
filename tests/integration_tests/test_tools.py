"""Integration tests for SpiceDB Tools.

These tests require a running SpiceDB instance and will make real authorization checks.
Set environment variables SPICEDB_ENDPOINT and SPICEDB_TOKEN to run these tests.
"""

import os
import pytest

from langchain_spicedb import SpiceDBPermissionTool, SpiceDBBulkPermissionTool


@pytest.fixture
def spicedb_config():
    """Get SpiceDB configuration from environment."""
    endpoint = os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
    token = os.getenv("SPICEDB_TOKEN", "somerandomkeyhere")

    return {
        "spicedb_endpoint": endpoint,
        "spicedb_token": token,
    }


class TestSpiceDBPermissionToolIntegration:
    """Integration tests for SpiceDBPermissionTool with real SpiceDB."""

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_permission_check_with_real_spicedb(self, spicedb_config):
        """Test permission checking with real SpiceDB instance."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check permission for a test resource
        result = tool._run(subject_id="tim", resource_id="123", permission="view")

        # Result should be "true" or "false"
        assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_async_permission_check_with_real_spicedb(self, spicedb_config):
        """Test async permission checking with real SpiceDB instance."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check permission for a test resource
        result = await tool._arun(subject_id="tim", resource_id="123", permission="view")

        # Result should be "true" or "false"
        assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_permission_check_multiple_resources(self, spicedb_config):
        """Test checking permissions for multiple different resources."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check multiple resources
        for resource_id in ["123", "456", "789"]:
            result = tool._run(subject_id="tim", resource_id=resource_id, permission="view")
            assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_permission_check_different_permissions(self, spicedb_config):
        """Test checking different permission types."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check different permissions
        for permission in ["view", "edit"]:
            result = tool._run(subject_id="tim", resource_id="123", permission=permission)
            assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_permission_check_different_subjects(self, spicedb_config):
        """Test checking permissions for different subjects."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check for different users
        for subject_id in ["tim", "alice", "bob"]:
            result = tool._run(subject_id=subject_id, resource_id="123", permission="view")
            assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_tool_invoke_with_real_spicedb(self, spicedb_config):
        """Test tool invocation using invoke method with real SpiceDB."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        result = tool.invoke({"subject_id": "tim", "resource_id": "123", "permission": "view"})

        assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_tool_ainvoke_with_real_spicedb(self, spicedb_config):
        """Test tool async invocation with real SpiceDB."""
        tool = SpiceDBPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        result = await tool.ainvoke(
            {"subject_id": "tim", "resource_id": "123", "permission": "view"}
        )

        assert result in ["true", "false"]

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_tool_with_tls(self, spicedb_config):
        """Test tool with TLS enabled (if endpoint supports it)."""
        # Only test if we're connecting to a non-localhost endpoint
        if "localhost" not in spicedb_config["spicedb_endpoint"]:
            tool = SpiceDBPermissionTool(
                subject_type="user",
                resource_type="article",
                use_tls=True,
                **spicedb_config,
            )

            result = tool._run(subject_id="tim", resource_id="123", permission="view")
            assert result in ["true", "false"]



class TestSpiceDBBulkPermissionToolIntegration:
    """Integration tests for SpiceDBBulkPermissionTool with real SpiceDB."""

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_permission_check_with_real_spicedb(self, spicedb_config):
        """Test bulk permission checking with real SpiceDB instance."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check permissions for multiple resources
        result = tool._run(subject_id="tim", resource_ids="123,456", permission="view")

        # Result should contain permission results - either success or failure
        assert isinstance(result, str)
        # Should contain either resource IDs (if authorized) or "cannot access" (if not)
        assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_async_bulk_permission_check_with_real_spicedb(self, spicedb_config):
        """Test async bulk permission checking with real SpiceDB instance."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Check permissions for multiple resources
        result = await tool._arun(subject_id="tim", resource_ids="123,456", permission="view")

        # Result should contain permission results - either success or failure
        assert isinstance(result, str)
        assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_check_single_resource(self, spicedb_config):
        """Test bulk check with single resource."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        result = tool._run(subject_id="tim", resource_ids="123", permission="view")

        assert isinstance(result, str)
        # Should contain either resource ID (if authorized) or "cannot access" (if not)
        assert "123" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_check_with_whitespace(self, spicedb_config):
        """Test bulk check handles whitespace in resource IDs."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        # Should handle spacing around commas
        result = tool._run(subject_id="tim", resource_ids="123, 456", permission="view")

        assert isinstance(result, str)
        # Should contain either resource IDs (if authorized) or "cannot access" (if not)
        assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_check_different_subjects(self, spicedb_config):
        """Test bulk checking for different subjects."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        for subject_id in ["tim", "alice", "bob"]:
            result = tool._run(subject_id=subject_id, resource_ids="123,456", permission="view")
            assert isinstance(result, str)
            # Should contain either resource IDs (if authorized) or "cannot access" (if not)
            assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_tool_invoke_with_real_spicedb(self, spicedb_config):
        """Test bulk tool invocation using invoke method with real SpiceDB."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        result = tool.invoke(
            {
                "subject_id": "tim",
                "resource_ids": "123,456",
                "permission": "view",
            }
        )

        assert isinstance(result, str)
        # Should contain either resource IDs (if authorized) or "cannot access" (if not)
        assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    @pytest.mark.asyncio
    async def test_bulk_tool_ainvoke_with_real_spicedb(self, spicedb_config):
        """Test bulk tool async invocation with real SpiceDB."""
        tool = SpiceDBBulkPermissionTool(
            subject_type="user",
            resource_type="article",
            **spicedb_config,
        )

        result = await tool.ainvoke(
            {
                "subject_id": "tim",
                "resource_ids": "123,456",
                "permission": "view",
            }
        )

        assert isinstance(result, str)
        # Should contain either resource IDs (if authorized) or "cannot access" (if not)
        assert "123" in result or "456" in result or "cannot access" in result

    @pytest.mark.skipif(
        not os.getenv("SPICEDB_ENDPOINT"),
        reason="SPICEDB_ENDPOINT not set - skipping integration test",
    )
    def test_bulk_tool_with_tls(self, spicedb_config):
        """Test bulk tool with TLS enabled (if endpoint supports it)."""
        # Only test if we're connecting to a non-localhost endpoint
        if "localhost" not in spicedb_config["spicedb_endpoint"]:
            tool = SpiceDBBulkPermissionTool(
                subject_type="user",
                resource_type="article",
                use_tls=True,
                **spicedb_config,
            )

            result = tool._run(subject_id="tim", resource_ids="123,456", permission="view")
            assert isinstance(result, str)

