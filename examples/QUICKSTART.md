# Quick Start Guide

Get up and running with langchain-spicedb examples in 5 minutes.

## 1. Start SpiceDB (30 seconds)

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

## 2. Create Schema (1 minute)

Save as `schema.zed`:

```zed
definition user {}

definition article {
    relation viewer: user
    relation editor: user
    permission view = viewer + editor
    permission edit = editor
}
```

Apply it:

```bash
# If you have zed CLI
zed context set local localhost:50051 somerandomkeyhere --insecure
zed schema write schema.zed

# Or use curl
curl -X POST http://localhost:50051/v1/schema/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -H "Content-Type: application/json" \
  -d '{"schema": "definition user {}\n\ndefinition article {\n  relation viewer: user\n  relation editor: user\n  permission view = viewer + editor\n  permission edit = editor\n}"}'
```

## 3. Create Test Data (1 minute)

```bash
# With zed
zed relationship create article:123 viewer user:tim
zed relationship create article:456 viewer user:tim

# Or with curl
curl -X POST http://localhost:50051/v1/relationships/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {"operation": "CREATE", "relationship": {"resource": {"objectType": "article", "objectId": "123"}, "relation": "viewer", "subject": {"object": {"objectType": "user", "objectId": "tim"}}}},
      {"operation": "CREATE", "relationship": {"resource": {"objectType": "article", "objectId": "456"}, "relation": "viewer", "subject": {"object": {"objectType": "user", "objectId": "tim"}}}}
    ]
  }'
```

## 4. Set Environment (30 seconds)

Create `.env` file:

```bash
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_TOKEN=somerandomkeyhere
SUBJECT_ID=tim
```

## 5. Run Examples (2 minutes)

```bash
# Install package
pip install -e ".[all]"

# Run retriever example (no OpenAI key needed)
python examples/retriever_example.py

# Run tool example (no OpenAI key needed)
python examples/tool_example.py

# With OpenAI (optional)
export OPENAI_API_KEY=sk-...
python examples/retriever_example.py
```

## Expected Output

### Retriever Example

```
Documents from base retriever (before authorization):
  - Python Basics (ID: 123)
  - JavaScript Guide (ID: 456)
  - ML Introduction (ID: 789)
  - SpiceDB Overview (ID: 101)

Documents after SpiceDB authorization filter (user: tim):
  ✓ Python Basics (ID: 123)
  ✓ JavaScript Guide (ID: 456)

SpiceDB filtered out 2 unauthorized document(s)
```

### Tool Example

```
1. Synchronous check - Can tim view article 123?
   Result: true

2. Async check - Can alice view article 456?
   Result: false

3. Bulk check - Which articles can tim view?
   Result: tim can access: 123, 456
```

## What's Happening?

1. **SpiceDB** stores permission relationships (who can do what)
2. **SpiceDBRetriever** filters documents based on these permissions
3. **SpiceDBPermissionTool** checks permissions before actions
4. **Your LLM** only sees authorized data

## Common Issues

**"Connection refused"**
- Make sure SpiceDB is running: `docker ps | grep spicedb`

**"No documents returned"**
- Check relationships exist: `zed relationship read article:123`
- Verify subject_id: Should be "tim" for test data

**"Import error"**
- Install package: `pip install -e ".[all]"`

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed setup
- Check [README.md](README.md) for example descriptions
- See [examples/](.) for all available examples
- Learn more at https://authzed.com/docs

## One-Liner Test

Verify everything works:

```bash
docker run -d -p 50051:50051 authzed/spicedb serve --grpc-preshared-key "test" --grpc-no-tls && \
  sleep 2 && \
  echo 'SPICEDB_ENDPOINT=localhost:50051\nSPICEDB_TOKEN=test' > .env && \
  python -c "from langchain_spicedb import SpiceDBPermissionTool; print('✓ langchain-spicedb is ready!')"
```

If you see "✓ langchain-spicedb is ready!" you're all set!
