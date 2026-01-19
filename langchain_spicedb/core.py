"""
Core SpiceDB Authorization Engine

This module provides framework-agnostic authorization logic that can be used
with any RAG pipeline, regardless of the framework (LangChain, LangGraph, etc.)
or vector store (Pinecone, FAISS, Weaviate, etc.).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time
from authzed.api.v1 import (
    Client,
    CheckPermissionRequest,
    CheckPermissionResponse,
    CheckBulkPermissionsRequest,
    CheckBulkPermissionsRequestItem,
    ObjectReference,
    SubjectReference,
)
from grpcutil import insecure_bearer_token_credentials


@dataclass
class AuthorizationResult:
    """
    Result of authorization check with metrics.

    Attributes:
        authorized_documents: Documents that passed authorization
        total_retrieved: Total number of documents checked
        total_authorized: Number of documents authorized
        authorization_rate: Percentage of documents authorized (0.0 to 1.0)
        denied_resource_ids: List of resource IDs that were denied
        check_latency_ms: Total time spent on authorization checks in milliseconds
    """

    authorized_documents: List[Any]
    total_retrieved: int
    total_authorized: int
    authorization_rate: float
    denied_resource_ids: List[str] = field(default_factory=list)
    check_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total_retrieved": self.total_retrieved,
            "total_authorized": self.total_authorized,
            "authorization_rate": self.authorization_rate,
            "denied_resource_ids": self.denied_resource_ids,
            "check_latency_ms": self.check_latency_ms,
        }


class SpiceDBAuthorizer:
    """
    Core SpiceDB authorization engine for RAG pipelines.

    This class provides document filtering based on SpiceDB permissions.
    It's framework-agnostic and can be used with any RAG implementation.

    Example:
        >>> authorizer = SpiceDBAuthorizer(
        ...     spicedb_endpoint="localhost:50051",
        ...     spicedb_token="sometoken",
        ...     resource_type="article",
        ... )
        >>> result = await authorizer.filter_documents(docs, subject_id="alice")
        >>> print(f"Authorized {result.total_authorized}/{result.total_retrieved}")
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
    ):
        """
        Initialize SpiceDB authorizer.

        Args:
            spicedb_endpoint: SpiceDB server address (e.g., "localhost:50051")
            spicedb_token: Pre-shared key for SpiceDB authentication
            resource_type: SpiceDB resource type (e.g., "document", "article")
            subject_type: SpiceDB subject type (e.g., "user", "service")
            permission: Permission to check (e.g., "view", "edit")
            resource_id_key: Key in document metadata containing resource ID
            fail_open: If True, allow access on errors; if False, deny on errors
            use_tls: Whether to use TLS for SpiceDB connection
        """
        self.spicedb_endpoint = spicedb_endpoint
        self.spicedb_token = spicedb_token
        self.resource_type = resource_type
        self.subject_type = subject_type
        self.permission = permission
        self.resource_id_key = resource_id_key
        self.fail_open = fail_open
        self.use_tls = use_tls

        # Initialize SpiceDB client
        if use_tls:
            from grpcutil import bearer_token_credentials

            credentials = bearer_token_credentials(spicedb_token)
        else:
            credentials = insecure_bearer_token_credentials(spicedb_token)

        self.client = Client(spicedb_endpoint, credentials)

    async def filter_documents(
        self,
        documents: List[Any],
        subject_id: str,
        subject_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        permission: Optional[str] = None,
        include_metrics: bool = True,
    ) -> AuthorizationResult:
        """
        Filter documents based on SpiceDB permissions.

        This method checks each document against SpiceDB permissions and returns
        only the documents the subject has access to.

        Args:
            documents: List of documents to filter (must have .metadata dict)
            subject_id: ID of the subject (user) requesting access
            subject_type: Override default subject type
            resource_type: Override default resource type
            permission: Override default permission
            include_metrics: Whether to include detailed metrics

        Returns:
            AuthorizationResult containing authorized documents and metrics
        """
        start_time = time.time()

        subject_type = subject_type or self.subject_type
        resource_type = resource_type or self.resource_type
        permission = permission or self.permission

        if not documents:
            return AuthorizationResult(
                authorized_documents=[],
                total_retrieved=0,
                total_authorized=0,
                authorization_rate=0.0,
                check_latency_ms=0.0,
            )

        # Extract resource IDs from documents
        doc_resource_map = {}
        for doc in documents:
            resource_id = self._get_resource_id(doc)
            if resource_id:
                doc_resource_map[resource_id] = doc

        if not doc_resource_map:
            # No valid resource IDs found
            return AuthorizationResult(
                authorized_documents=[],
                total_retrieved=len(documents),
                total_authorized=0,
                authorization_rate=0.0,
                check_latency_ms=(time.time() - start_time) * 1000,
            )

        # Batch check permissions
        authorized_ids = await self._batch_check_permissions(
            subject_id=subject_id,
            subject_type=subject_type,
            resource_ids=list(doc_resource_map.keys()),
            resource_type=resource_type,
            permission=permission,
        )

        # Filter documents
        authorized_documents = [doc_resource_map[rid] for rid in authorized_ids]

        denied_ids = [rid for rid in doc_resource_map.keys() if rid not in authorized_ids]

        check_latency_ms = (time.time() - start_time) * 1000

        return AuthorizationResult(
            authorized_documents=authorized_documents,
            total_retrieved=len(documents),
            total_authorized=len(authorized_documents),
            authorization_rate=len(authorized_documents) / len(documents),
            denied_resource_ids=denied_ids if include_metrics else [],
            check_latency_ms=check_latency_ms,
        )

    async def check_permission(
        self,
        subject_id: str,
        resource_id: str,
        subject_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        permission: Optional[str] = None,
    ) -> bool:
        """
        Check if a subject has permission for a single resource.

        Args:
            subject_id: ID of the subject (user)
            resource_id: ID of the resource
            subject_type: Override default subject type
            resource_type: Override default resource type
            permission: Override default permission

        Returns:
            True if permission granted, False otherwise
        """
        subject_type = subject_type or self.subject_type
        resource_type = resource_type or self.resource_type
        permission = permission or self.permission

        try:
            # Await the async gRPC call
            response = await self.client.CheckPermission(
                CheckPermissionRequest(
                    resource=ObjectReference(
                        object_type=resource_type,
                        object_id=str(resource_id),
                    ),
                    permission=permission,
                    subject=SubjectReference(
                        object=ObjectReference(
                            object_type=subject_type,
                            object_id=subject_id,
                        ),
                    ),
                )
            )

            return response.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION

        except Exception:
            if self.fail_open:
                return True
            return False

    async def _batch_check_permissions(
        self,
        subject_id: str,
        subject_type: str,
        resource_ids: List[str],
        resource_type: str,
        permission: str,
    ) -> List[str]:
        """
        Check permissions for multiple resources using SpiceDB's native bulk API.

        Uses CheckBulkPermissionsRequest to check all resources in a single
        API call, which is significantly more efficient than making N individual
        CheckPermissionRequest calls.

        Args:
            subject_id: ID of the subject (user)
            subject_type: Type of the subject (e.g., "user")
            resource_ids: List of resource IDs to check
            resource_type: Type of the resources (e.g., "article")
            permission: Permission to check (e.g., "view")

        Returns:
            List of resource IDs that are authorized
        """
        if not resource_ids:
            return []

        try:
            # Create bulk permission check items
            items = [
                CheckBulkPermissionsRequestItem(
                    resource=ObjectReference(
                        object_type=resource_type,
                        object_id=str(resource_id),
                    ),
                    permission=permission,
                    subject=SubjectReference(
                        object=ObjectReference(
                            object_type=subject_type,
                            object_id=subject_id,
                        ),
                    ),
                )
                for resource_id in resource_ids
            ]

            # Make single bulk permission check request (await async gRPC call)
            response = await self.client.CheckBulkPermissions(
                CheckBulkPermissionsRequest(items=items)
            )

            # Extract authorized resource IDs from response
            authorized_ids = []
            for i, pair in enumerate(response.pairs):
                if (
                    pair.item.permissionship
                    == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                ):
                    authorized_ids.append(resource_ids[i])

            return authorized_ids

        except Exception:
            # Fail-open: return all IDs if configured to do so
            if self.fail_open:
                return resource_ids
            # Fail-closed: return empty list on error
            return []

    def _get_resource_id(self, doc: Any) -> Optional[str]:
        """
        Extract resource ID from document metadata.

        Args:
            doc: Document object (must have .metadata dict)

        Returns:
            Resource ID string or None if not found
        """
        if not hasattr(doc, "metadata"):
            return None

        if not isinstance(doc.metadata, dict):
            return None

        return doc.metadata.get(self.resource_id_key)
