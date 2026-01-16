"""
SpiceDB RAG Authorization

Authorization library for RAG pipelines using SpiceDB.
Designed for LangChain and LangGraph integrations with support for any vector store
(Pinecone, FAISS, Weaviate, etc.).

Example (LangChain):
    >>> from langchain_spicedb import SpiceDBAuthFilter
    >>>
    >>> # ALL parameters are required for SpiceDB to make access decisions
    >>> auth = SpiceDBAuthFilter(
    ...     spicedb_endpoint="localhost:50051",
    ...     spicedb_token="sometoken",
    ...     subject_type="user",
    ...     resource_type="article",
    ...     resource_id_key="article_id",
    ...     permission="view",
    ... )
    >>>
    >>> chain = retriever | auth.with_config(subject_id="alice") | prompt | llm

Example (LangGraph):
    >>> from langchain_spicedb import create_auth_node
    >>>
    >>> graph = StateGraph(MyState)
    >>> graph.add_node("authorize", create_auth_node(
    ...     spicedb_endpoint="localhost:50051",
    ...     spicedb_token="sometoken",
    ...     subject_type="user",
    ...     resource_type="article",
    ...     resource_id_key="article_id",
    ...     permission="view",
    ... ))
"""

__version__ = "0.1.0"

# Import LangChain components (if available)
try:
    from .langchain_runnable import SpiceDBAuthFilter, SpiceDBAuthLambda  # noqa: F401

    _has_langchain = True
except ImportError:
    _has_langchain = False

# Import LangChain standard components (retrievers, tools)
try:
    from .retrievers import SpiceDBRetriever  # noqa: F401

    _has_retrievers = True
except ImportError:
    _has_retrievers = False

try:
    from .tools import SpiceDBPermissionTool, SpiceDBBulkPermissionTool  # noqa: F401

    _has_tools = True
except ImportError:
    _has_tools = False

# Import LangGraph components (if available)
try:
    from .langgraph_node import create_auth_node, AuthorizationNode, RAGAuthState  # noqa: F401

    _has_langgraph = True
except ImportError:
    _has_langgraph = False

# Define public API - only LangChain and LangGraph components
__all__ = []

if _has_langchain:
    __all__.extend(["SpiceDBAuthFilter", "SpiceDBAuthLambda"])

if _has_retrievers:
    __all__.extend(["SpiceDBRetriever"])

if _has_tools:
    __all__.extend(["SpiceDBPermissionTool", "SpiceDBBulkPermissionTool"])

if _has_langgraph:
    __all__.extend(["create_auth_node", "AuthorizationNode", "RAGAuthState"])
