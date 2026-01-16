# LangChain Documentation Files

This directory contains the MDX documentation files for submitting to the [langchain-ai/docs](https://github.com/langchain-ai/docs) repository.

## Files

### 1. `spicedb.mdx` - Provider Overview Page
**Target location**: `src/oss/python/integrations/providers/spicedb.mdx`

This is the main landing page for the SpiceDB integration. It provides:
- Overview of what SpiceDB is
- Key features of the integration
- Installation instructions
- Quick start examples
- Links to detailed component documentation

### 2. `langchain-spicedb-tools.mdx` - Tools Documentation
**Target location**: `src/oss/python/integrations/tools/langchain-spicedb.mdx`

Detailed documentation for the SpiceDB permission checking tools:
- SpiceDBPermissionTool (single permission checks)
- SpiceDBBulkPermissionTool (bulk permission checks)
- Usage with agents
- How agents decide to call these tools
- Complete examples

### 3. `langchain-spicedb-retriever.mdx` - Retriever Documentation
**Target location**: `src/oss/python/integrations/retrievers/langchain-spicedb.mdx`

Detailed documentation for the SpiceDB retriever:
- SpiceDBRetriever (BaseRetriever wrapper)
- Usage in RAG pipelines
- Vector store compatibility examples (FAISS, Chroma, Pinecone, Weaviate)
- Post-filter vs pre-filter comparison
- Performance considerations
- Complete examples

## Submission Steps

### 1. Fork the Repository
```bash
git clone https://github.com/langchain-ai/docs.git
cd docs
git checkout -b feat/langchain-spicedb-integration
```

### 2. Copy Files to Correct Locations
```bash
# Provider overview
cp spicedb.mdx src/oss/python/integrations/providers/

# Tools documentation
cp langchain-spicedb-tools.mdx src/oss/python/integrations/tools/langchain-spicedb.mdx

# Retriever documentation
cp langchain-spicedb-retriever.mdx src/oss/python/integrations/retrievers/langchain-spicedb.mdx
```

### 3. Test Locally (Optional)
Follow the langchain-ai/docs repository instructions for running the docs locally to verify formatting.

### 4. Commit and Push
```bash
git add .
git commit -m "docs: Add SpiceDB integration documentation

- Add provider overview page for SpiceDB
- Add tools documentation for SpiceDBPermissionTool and SpiceDBBulkPermissionTool
- Add retriever documentation for SpiceDBRetriever
- Include installation, setup, usage examples, and API reference"

git push origin feat/langchain-spicedb-integration
```

### 5. Create Pull Request
Go to https://github.com/langchain-ai/docs and create a PR with:

**Title**: `docs: Add SpiceDB integration documentation`

**Description**:
```markdown
## Summary
Adds documentation for the `langchain-spicedb` package, which provides SpiceDB authorization components for LangChain applications.

## Changes
- **Provider page** (`providers/spicedb.mdx`): Overview of SpiceDB integration with features, installation, and examples
- **Tools page** (`tools/langchain-spicedb.mdx`): Documentation for SpiceDBPermissionTool and SpiceDBBulkPermissionTool
- **Retriever page** (`retrievers/langchain-spicedb.mdx`): Documentation for SpiceDBRetriever with vector store examples

## Package Info
- **Package name**: `langchain-spicedb`
- **PyPI**: https://pypi.org/project/langchain-spicedb/ (published)
- **GitHub**: https://github.com/authzed/langchain-spicedb
- **Integration type**: Authorization/Retriever/Tools

## Checklist
- [x] All code examples tested and work correctly
- [x] Followed MDX template structure
- [x] Included proper frontmatter
- [x] Used Mintlify components appropriately
- [x] Follows LangChain documentation quality standards
- [x] No grammatical errors or typos
- [x] Package is published to PyPI
```

## Before Submitting

### Verify Package is Published
Make sure `langchain-spicedb` is published to PyPI **before** submitting the docs PR, so the installation commands work:

```bash
pip install langchain-spicedb
```

### Code Examples
All code examples in the docs have been tested and should work. They assume:
- SpiceDB is running locally on `localhost:50051`
- You have set up the schema and relationships
- OpenAI API key is set for LLM examples

### Quality Checklist
- [x] All code examples are syntactically correct
- [x] Installation commands reference published PyPI package
- [x] Links between pages work correctly
- [x] Mintlify components (Tip, Warning, etc.) used appropriately
- [x] Frontmatter includes title and sidebar_label
- [x] Examples are practical and educational
- [x] API reference sections included

## Notes for Reviewers

### Why This Integration?
SpiceDB provides fine-grained, relationship-based authorization - critical for RAG applications that serve multiple users with different access rights. This integration enables:
- Post-retrieval document filtering based on user permissions
- Agent tools for permission checking before actions
- Vector store agnostic implementation
- Enterprise-grade security for LLM applications

### Integration Components
- **BaseRetriever**: SpiceDBRetriever wraps any retriever with authorization
- **BaseTool**: SpiceDBPermissionTool and SpiceDBBulkPermissionTool for agents
- **Runnables**: SpiceDBAuthFilter for LCEL chains
- **LangGraph**: Authorization nodes for stateful workflows

### Performance
Uses SpiceDB's native `CheckBulkPermissionsRequest` API for efficient bulk permission checking (single API call vs N individual calls).
