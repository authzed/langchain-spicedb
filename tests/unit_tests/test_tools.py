"""Unit tests for SpiceDB Tools.

These tests validate the tools in isolation using mocks, without requiring
a real SpiceDB instance.
"""

import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.tools import BaseTool

from langchain_spicedb import SpiceDBPermissionTool, SpiceDBBulkPermissionTool


class TestSpiceDBPermissionToolUnit:
    """Unit tests for SpiceDBPermissionTool."""

    @pytest.fixture
    def mock_authorizer(self):
        """Create a mock SpiceDB authorizer."""
        with patch("langchain_spicedb.tools.SpiceDBAuthorizer") as mock:
            mock_instance = AsyncMock()
            # Configure async methods to return values
            mock_instance.check_permission = AsyncMock(return_value=True)
            mock_instance.acheck_permission = AsyncMock(return_value=True)
            mock.return_value = mock_instance
            yield mock

    def test_tool_initialization(self, mock_authorizer):
        """Test that SpiceDBPermissionTool initializes correctly."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        assert tool.name == "check_spicedb_permission"
        assert "permission" in tool.description.lower()
        assert "resource" in tool.description.lower()
        assert tool.subject_type == "user"
        assert tool.resource_type == "article"

    def test_tool_inherits_from_base_tool(self):
        """Test that SpiceDBPermissionTool is a BaseTool."""
        assert issubclass(SpiceDBPermissionTool, BaseTool)

    def test_tool_schema(self, mock_authorizer):
        """Test that tool has correct input schema."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        # Check that tool accepts required parameters
        schema = tool.args_schema
        assert schema is not None

        # Verify required fields in schema
        fields = schema.model_fields
        assert "subject_id" in fields
        assert "resource_id" in fields
        assert "permission" in fields

    def test_synchronous_permission_check(self, mock_authorizer):
        """Test synchronous permission checking."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(
            subject_id="alice", resource_id="123", permission="view"
        )

        assert result == "true"
        mock_authorizer.return_value.check_permission.assert_called_once_with(
            subject_id="alice", resource_id="123", permission="view"
        )

    @pytest.mark.asyncio
    async def test_asynchronous_permission_check(self, mock_authorizer):
        """Test asynchronous permission checking."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = await tool._arun(
            subject_id="alice", resource_id="123", permission="view"
        )

        assert result == "true"
        # The tool calls check_permission (which is async), not acheck_permission
        mock_authorizer.return_value.check_permission.assert_called_once()

    def test_permission_denied(self, mock_authorizer):
        """Test handling of permission denial."""
        # Configure authorizer to return False
        mock_authorizer.return_value.check_permission.return_value = False

        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(subject_id="bob", resource_id="123", permission="view")

        assert result == "false"

    def test_tool_invoke_method(self, mock_authorizer):
        """Test tool invocation using invoke method."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool.invoke(
            {"subject_id": "alice", "resource_id": "123", "permission": "view"}
        )

        assert result == "true"

    @pytest.mark.asyncio
    async def test_tool_ainvoke_method(self, mock_authorizer):
        """Test tool invocation using ainvoke method."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = await tool.ainvoke(
            {"subject_id": "alice", "resource_id": "123", "permission": "view"}
        )

        assert result == "true"

    def test_different_permissions(self, mock_authorizer):
        """Test tool with different permission types."""
        tool = SpiceDBPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        for permission in ["view", "edit", "delete", "admin"]:
            result = tool._run(
                subject_id="alice", resource_id="123", permission=permission
            )
            assert result in ["true", "false"]

    def test_tool_parameters_passed_to_authorizer(self, mock_authorizer):
        """Test that tool parameters are correctly passed to authorizer."""
        SpiceDBPermissionTool(
            spicedb_endpoint="custom:50051",
            spicedb_token="custom_token",
            subject_type="service",
            resource_type="document",
            fail_open=True,
            use_tls=True,
        )

        # Verify authorizer was initialized
        mock_authorizer.assert_called_once()

        # Verify key parameters were passed (handle both positional and keyword args)
        call_args = mock_authorizer.call_args
        if hasattr(call_args, 'kwargs'):
            call_kwargs = call_args.kwargs
        else:
            call_kwargs = call_args[1] if len(call_args) > 1 else call_args[0]

        assert call_kwargs.get("spicedb_endpoint") == "custom:50051"
        assert call_kwargs.get("spicedb_token") == "custom_token"
        assert call_kwargs.get("subject_type") == "service"
        assert call_kwargs.get("resource_type") == "document"


class TestSpiceDBBulkPermissionToolUnit:
    """Unit tests for SpiceDBBulkPermissionTool."""

    @pytest.fixture
    def mock_authorizer(self):
        """Create a mock SpiceDB authorizer."""
        with patch("langchain_spicedb.tools.SpiceDBAuthorizer") as mock:
            mock_instance = AsyncMock()
            # Configure _batch_check_permissions to return authorized IDs
            mock_instance._batch_check_permissions = AsyncMock(
                return_value=["123", "456"]  # Returns list of authorized IDs
            )
            mock.return_value = mock_instance
            yield mock

    def test_bulk_tool_initialization(self, mock_authorizer):
        """Test that SpiceDBBulkPermissionTool initializes correctly."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        assert tool.name == "check_spicedb_bulk_permissions"
        assert "permission" in tool.description.lower()
        assert "multiple" in tool.description.lower() or "bulk" in tool.description.lower()

    def test_bulk_tool_inherits_from_base_tool(self):
        """Test that SpiceDBBulkPermissionTool is a BaseTool."""
        assert issubclass(SpiceDBBulkPermissionTool, BaseTool)

    def test_bulk_tool_schema(self, mock_authorizer):
        """Test that bulk tool has correct input schema."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        schema = tool.args_schema
        assert schema is not None

        fields = schema.model_fields
        assert "subject_id" in fields
        assert "resource_ids" in fields
        assert "permission" in fields

    def test_synchronous_bulk_permission_check(self, mock_authorizer):
        """Test synchronous bulk permission checking."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(
            subject_id="alice", resource_ids="123,456,789", permission="view"
        )

        # Result should contain authorized resource IDs
        assert isinstance(result, str)
        assert "123" in result
        assert "456" in result
        assert "can access" in result or ":" in result  # Accept either format

        mock_authorizer.return_value._batch_check_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_asynchronous_bulk_permission_check(self, mock_authorizer):
        """Test asynchronous bulk permission checking."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = await tool._arun(
            subject_id="alice", resource_ids="123,456,789", permission="view"
        )

        # Result should contain authorized resource IDs
        assert isinstance(result, str)
        assert "123" in result
        assert "456" in result
        assert "can access" in result or ":" in result

        mock_authorizer.return_value._batch_check_permissions.assert_called_once()

    def test_bulk_check_with_single_resource(self, mock_authorizer):
        """Test bulk check with single resource ID."""
        mock_authorizer.return_value._batch_check_permissions.return_value = ["123"]

        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(subject_id="alice", resource_ids="123", permission="view")

        assert isinstance(result, str)
        assert "123" in result

    def test_bulk_check_with_whitespace(self, mock_authorizer):
        """Test bulk check handles whitespace in resource IDs."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        # Should handle spacing around commas
        result = tool._run(
            subject_id="alice", resource_ids="123, 456, 789", permission="view"
        )

        assert isinstance(result, str)

    def test_bulk_tool_invoke_method(self, mock_authorizer):
        """Test bulk tool invocation using invoke method."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool.invoke(
            {
                "subject_id": "alice",
                "resource_ids": "123,456,789",
                "permission": "view",
            }
        )

        assert isinstance(result, str)
        assert "123" in result

    @pytest.mark.asyncio
    async def test_bulk_tool_ainvoke_method(self, mock_authorizer):
        """Test bulk tool invocation using ainvoke method."""
        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = await tool.ainvoke(
            {
                "subject_id": "alice",
                "resource_ids": "123,456,789",
                "permission": "view",
            }
        )

        assert isinstance(result, str)
        assert "123" in result

    def test_all_denied_bulk_check(self, mock_authorizer):
        """Test bulk check when all permissions are denied."""
        mock_authorizer.return_value._batch_check_permissions.return_value = []  # No authorized IDs

        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(subject_id="bob", resource_ids="123,456", permission="view")

        assert isinstance(result, str)
        # When no resources are authorized, should say "cannot access"
        assert "cannot access" in result.lower() or "no" in result.lower()

    def test_all_allowed_bulk_check(self, mock_authorizer):
        """Test bulk check when all permissions are allowed."""
        mock_authorizer.return_value._batch_check_permissions.return_value = ["123", "456"]  # All authorized

        tool = SpiceDBBulkPermissionTool(
            spicedb_endpoint="localhost:50051",
            spicedb_token="test_token",
            subject_type="user",
            resource_type="article",
        )

        result = tool._run(
            subject_id="alice", resource_ids="123,456", permission="view"
        )

        assert isinstance(result, str)
        assert "123" in result
        assert "456" in result
