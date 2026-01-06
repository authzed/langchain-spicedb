# SpiceDB Setup Guide for Examples

This guide walks you through setting up SpiceDB and configuring it to run the langchain-spicedb examples.

## Quick Start

### 1. Start SpiceDB with Docker

```bash
docker run --rm -p 50051:50051 \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-no-tls
```

Keep this running in a terminal window.

### 2. Install zed CLI (Optional but Recommended)

The `zed` CLI makes it easy to interact with SpiceDB:

```bash
# macOS
brew install authzed/tap/zed

# Linux
curl -L https://github.com/authzed/zed/releases/latest/download/zed-linux-amd64 -o zed
chmod +x zed
sudo mv zed /usr/local/bin/

# Windows
# Download from https://github.com/authzed/zed/releases
```

Configure zed to connect to your local SpiceDB:

```bash
zed context set local localhost:50051 somerandomkeyhere --insecure
```

### 3. Create the Schema

Create a file called `example_schema.zed`:

```zed
/**
 * User represents a person in the system
 */
definition user {}

/**
 * Article represents a document or content item
 */
definition article {
    // viewer can see the article
    relation viewer: user

    // editor can modify the article
    relation editor: user

    // owner has full control
    relation owner: user

    // Permissions computed from relations
    permission view = viewer + editor + owner
    permission edit = editor + owner
    permission delete = owner
}
```

Apply the schema:

```bash
zed schema write example_schema.zed
```

Or without zed:

```bash
curl -X POST http://localhost:50051/v1/schema/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -H "Content-Type: application/json" \
  -d '{
    "schema": "definition user {}\n\ndefinition article {\n  relation viewer: user\n  relation editor: user\n  relation owner: user\n\n  permission view = viewer + editor + owner\n  permission edit = editor + owner\n  permission delete = owner\n}"
  }'
```

### 4. Create Test Relationships

Create relationships for the test users and articles referenced in the examples:

```bash
# Tim can view articles 123 and 456
zed relationship create article:123 viewer user:tim
zed relationship create article:456 viewer user:tim

# Alice can view article 789 and edit article 123
zed relationship create article:789 viewer user:alice
zed relationship create article:123 editor user:alice

# Bob is owner of article 101
zed relationship create article:101 owner user:bob
```

Or without zed:

```bash
curl -X POST http://localhost:50051/v1/relationships/write \
  -H "Authorization: Bearer somerandomkeyhere" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "123"},
          "relation": "viewer",
          "subject": {"object": {"objectType": "user", "objectId": "tim"}}
        }
      },
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "456"},
          "relation": "viewer",
          "subject": {"object": {"objectType": "user", "objectId": "tim"}}
        }
      },
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "789"},
          "relation": "viewer",
          "subject": {"object": {"objectType": "user", "objectId": "alice"}}
        }
      },
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "123"},
          "relation": "editor",
          "subject": {"object": {"objectType": "user", "objectId": "alice"}}
        }
      },
      {
        "operation": "CREATE",
        "relationship": {
          "resource": {"objectType": "article", "objectId": "101"},
          "relation": "owner",
          "subject": {"object": {"objectType": "user", "objectId": "bob"}}
        }
      }
    ]
  }'
```

### 5. Verify Setup

Test that permissions are working correctly:

```bash
# Tim can view article 123 (should return true)
zed permission check article:123 view user:tim

# Tim cannot edit article 123 (should return false)
zed permission check article:123 edit user:tim

# Alice can edit article 123 (should return true)
zed permission check article:123 edit user:alice

# Tim cannot view article 789 (should return false)
zed permission check article:789 view user:tim
```

### 6. Set Environment Variables

Create a `.env` file in the examples directory:

```bash
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_TOKEN=somerandomkeyhere

# Optional: Set for LLM examples
OPENAI_API_KEY=sk-your-key-here

# Optional: Change which user to test
SUBJECT_ID=tim
```

### 7. Run Examples

You're ready! Run the examples:

```bash
# Basic retriever demo (no OpenAI needed)
python examples/retriever_example.py

# Basic tool demo (no OpenAI needed)
python examples/tool_example.py

# With OpenAI API key
export OPENAI_API_KEY=sk-...
python examples/retriever_example.py
python examples/tool_example.py
```

## Expected Results

With the test relationships created above, here's what you should see:

### User: tim
- ✓ Can **view** article 123
- ✓ Can **view** article 456
- ✗ Cannot **view** article 789
- ✗ Cannot **view** article 101
- ✗ Cannot **edit** any articles
- ✗ Cannot **delete** any articles

### User: alice
- ✓ Can **view** article 123 (via editor relation)
- ✓ Can **view** article 789
- ✓ Can **edit** article 123
- ✗ Cannot **view** articles 456 or 101
- ✗ Cannot **delete** any articles

### User: bob
- ✓ Can **view** article 101
- ✓ Can **edit** article 101
- ✓ Can **delete** article 101
- ✗ Cannot access articles 123, 456, or 789

## Alternative: SpiceDB Cloud

Instead of running SpiceDB locally, you can use SpiceDB Cloud:

### 1. Sign Up

Go to https://app.authzed.com and create an account.

### 2. Create Permission System

1. Click "Create Permission System"
2. Give it a name (e.g., "langchain-examples")
3. Note your endpoint and token

### 3. Update Environment Variables

```bash
SPICEDB_ENDPOINT=grpc.authzed.com:443
SPICEDB_TOKEN=tc_your_token_here
```

### 4. Configure zed for Cloud

```bash
zed context set cloud grpc.authzed.com:443 tc_your_token_here
```

### 5. Follow Steps 3-7 Above

The schema and relationship setup is the same, but you'll connect to SpiceDB Cloud instead of localhost.

## Advanced Configuration

### Custom Schema for Your Use Case

Modify the schema to match your application:

```zed
definition user {}

definition organization {
    relation member: user
}

definition document {
    relation parent: organization
    relation owner: user

    permission view = owner + parent->member
    permission edit = owner
}
```

This allows organizational access control where members of an organization can view documents.

### Using TLS

For production, enable TLS:

```python
retriever = SpiceDBRetriever(
    ...,
    use_tls=True,  # Enable TLS
)
```

And start SpiceDB with TLS:

```bash
docker run --rm -p 50051:50051 \
  -v $(pwd)/tls:/tls \
  authzed/spicedb serve \
  --grpc-preshared-key "somerandomkeyhere" \
  --grpc-tls-cert-path /tls/server.crt \
  --grpc-tls-key-path /tls/server.key
```

### Performance Tuning

Adjust batch size for permission checks:

```python
retriever = SpiceDBRetriever(
    ...,
    batch_size=50,  # Check up to 50 resources at once (default: 10)
)
```

### Fail-Open Mode

For high availability, enable fail-open mode (use cautiously):

```python
retriever = SpiceDBRetriever(
    ...,
    fail_open=True,  # Allow access if SpiceDB is unavailable
)
```

## Troubleshooting

### Port Already in Use

```
Error: bind: address already in use
```

**Solution**: Stop existing SpiceDB or use a different port:

```bash
docker run --rm -p 50052:50051 ...
# Then set SPICEDB_ENDPOINT=localhost:50052
```

### Connection Refused

```
Error: connection refused
```

**Solution**:
1. Verify SpiceDB is running: `docker ps | grep spicedb`
2. Check port forwarding: `curl http://localhost:50051`
3. Check firewall settings

### Invalid Token

```
Error: unauthenticated
```

**Solution**:
- Verify token matches: The token in `SPICEDB_TOKEN` must match `--grpc-preshared-key`
- Check for extra spaces or quotes in environment variable

### Schema Already Exists

```
Error: schema already exists
```

**Solution**: SpiceDB schemas are immutable. To change, you need to:
1. Stop SpiceDB container
2. Start fresh container (data is ephemeral without persistence)
3. Reapply new schema

Or use schema versioning (see SpiceDB docs).

### Relationships Not Found

```
No documents returned after authorization
```

**Solution**:
1. Verify relationships exist:
   ```bash
   zed relationship read article:123
   ```
2. Check for typos in subject_id, resource_id
3. Verify schema allows the relation

## Cleaning Up

### Stop SpiceDB

```bash
# Find the container
docker ps | grep spicedb

# Stop it
docker stop <container_id>
```

### Clear All Data

Since we're running without persistence, just restart the container to clear all data:

```bash
docker stop <container_id>
docker run --rm -p 50051:50051 ...
```

## Next Steps

- Read the [examples README](README.md) for example descriptions
- Check out [SpiceDB Playground](https://play.authzed.com) for interactive schema design
- Review [SpiceDB documentation](https://authzed.com/docs) for advanced features
- Explore [schema design patterns](https://authzed.com/docs/guides/schema)

## Getting Help

- **SpiceDB Issues**: https://github.com/authzed/spicedb/issues
- **langchain-spicedb Issues**: https://github.com/yourusername/langchain-spicedb/issues
- **SpiceDB Discord**: https://discord.gg/spicedb
- **LangChain Discord**: https://discord.gg/langchain
