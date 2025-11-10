"""
SpiceDB RAG Authorization

A universal authorization library for RAG pipelines using SpiceDB.
Works with any framework (LangChain, LangGraph) and any vector store
(Pinecone, FAISS, Weaviate, etc.).

Example (Standalone):
    >>> from spicedb_rag_auth import SpiceDBAuthorizer
    >>>
    >>> authorizer = SpiceDBAuthorizer(
    ...     spicedb_endpoint="localhost:50051",
    ...     spicedb_token="sometoken",
    ...     resource_type="article",
    ... )
    >>>
    >>> result = await authorizer.filter_documents(docs, subject_id="alice")
    >>> print(f"Authorized {result.total_authorized}/{result.total_retrieved}")

Example (LangChain):
    >>> from spicedb_rag_auth import SpiceDBAuthFilter
    >>>
    >>> auth = SpiceDBAuthFilter(
    ...     spicedb_endpoint="localhost:50051",
    ...     spicedb_token="sometoken",
    ...     resource_type="article",
    ... )
    >>>
    >>> chain = retriever | auth.with_config(subject_id="alice") | prompt | llm

Example (LangGraph):
    >>> from spicedb_rag_auth import create_auth_node
    >>>
    >>> graph = StateGraph(MyState)
    >>> graph.add_node("authorize", create_auth_node(
    ...     spicedb_endpoint="localhost:50051",
    ...     spicedb_token="sometoken",
    ...     resource_type="article",
    ... ))
"""

__version__ = "0.1.0"

from .core import SpiceDBAuthorizer, AuthorizationResult

try:
    from .langchain_runnable import SpiceDBAuthFilter, SpiceDBAuthLambda
    _has_langchain = True
except ImportError:
    _has_langchain = False

try:
    from .langgraph_node import create_auth_node, AuthorizationNode, RAGAuthState
    _has_langgraph = True
except ImportError:
    _has_langgraph = False


__all__ = [
    "SpiceDBAuthorizer",
    "AuthorizationResult",
]

if _has_langchain:
    __all__.extend(["SpiceDBAuthFilter", "SpiceDBAuthLambda"])

if _has_langgraph:
    __all__.extend(["create_auth_node", "AuthorizationNode", "RAGAuthState"])
