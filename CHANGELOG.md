# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-19

### Breaking Changes

| Symbol | Change | Migration |
|--------|--------|-----------|
| `SpiceDBRetriever` | Removed | Use `base_retriever \| SpiceDBAuthFilter` and pass `subject_id` via `config={"configurable": {"subject_id": "alice"}}` |
| `SpiceDBAuthLambda` | Removed | Use `SpiceDBAuthFilter` directly in chains: `RunnableLambda(retriever) \| auth_filter` |
| `create_auth_node` | Renamed to `create_check_permissions_node` | Update imports and call sites |
| `fail_open` parameter | Removed from all components | Remove the argument — errors now propagate instead of silently granting access |

### Added

- `SpiceDBPreFilterRetriever` — LangChain `BaseRetriever` using SpiceDB's `LookupResources` API. Fetches authorized resource IDs first, then runs a filtered vector store search. Use when users have access to a small fraction of a large corpus.
- `create_check_permissions_node` — LangGraph node factory (renamed from `create_auth_node`). Post-filter: checks permissions on already-retrieved documents.
- `create_lookup_resources_node` — LangGraph node factory for pre-filter authorization. Calls `LookupResources`, runs a filtered vector search, and writes `authorized_documents` to state. No separate retrieval node needed.
- `SpiceDBAuthorizer.lookup_resources()` — underlying method wrapping SpiceDB's `LookupResources` streaming gRPC API.

### Removed

- `SpiceDBRetriever` — superseded by `SpiceDBAuthFilter` (more composable, supports runtime user injection).
- `SpiceDBAuthLambda` — superseded by `SpiceDBAuthFilter`.
- `fail_open` parameter — was silently granting full access on SpiceDB failures; errors now always propagate.

## [0.1.0] - 2026-04-01

Initial release.

- `SpiceDBAuthFilter` — post-filter authorization as a LangChain `Runnable`
- `SpiceDBPermissionTool` — single permission check for LangChain agents
- `SpiceDBBulkPermissionTool` — bulk permission checks for LangChain agents
- `create_auth_node` / `AuthorizationNode` — post-filter LangGraph nodes
- `RAGAuthState` — typed state for LangGraph RAG workflows
