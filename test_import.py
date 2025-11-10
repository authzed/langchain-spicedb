"""
Quick test to verify the package is correctly installed and importable.
Run this to make sure everything works before integrating into your notebook.
"""

print("Testing spicedb-rag-auth package...")
print("=" * 80)
print()

# Test 1: Core module
print("1. Testing core module import...")
try:
    from spicedb_rag_auth import SpiceDBAuthorizer, AuthorizationResult
    print("   ✅ SpiceDBAuthorizer imported successfully")
    print("   ✅ AuthorizationResult imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import core module: {e}")
    exit(1)

# Test 2: LangChain wrapper
print()
print("2. Testing LangChain wrapper import...")
try:
    from spicedb_rag_auth import SpiceDBAuthFilter, SpiceDBAuthLambda
    print("   ✅ SpiceDBAuthFilter imported successfully")
    print("   ✅ SpiceDBAuthLambda imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import LangChain wrapper: {e}")
    exit(1)

# Test 3: LangGraph wrapper
print()
print("3. Testing LangGraph wrapper import...")
try:
    from spicedb_rag_auth import create_auth_node, AuthorizationNode
    print("   ✅ create_auth_node imported successfully")
    print("   ✅ AuthorizationNode imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import LangGraph wrapper: {e}")
    exit(1)

# Test 4: Create instances
print()
print("4. Testing object instantiation...")
try:
    # Test core authorizer
    authorizer = SpiceDBAuthorizer(
        spicedb_endpoint="localhost:50051",
        spicedb_token="sometoken",
        resource_type="article",
    )
    print("   ✅ SpiceDBAuthorizer instantiated successfully")
    print(f"      - Endpoint: {authorizer.spicedb_endpoint}")
    print(f"      - Resource type: {authorizer.resource_type}")
    print(f"      - Subject type: {authorizer.subject_type}")
    print(f"      - Permission: {authorizer.permission}")
    print(f"      - Batch size: {authorizer.batch_size}")
except Exception as e:
    print(f"   ❌ Failed to instantiate SpiceDBAuthorizer: {e}")
    exit(1)

try:
    # Test LangChain wrapper
    auth_filter = SpiceDBAuthLambda(
        spicedb_endpoint="localhost:50051",
        spicedb_token="sometoken",
        resource_type="article",
        subject_id="alice",
    )
    print("   ✅ SpiceDBAuthLambda instantiated successfully")
except Exception as e:
    print(f"   ❌ Failed to instantiate SpiceDBAuthLambda: {e}")
    exit(1)

# Test 5: Check version
print()
print("5. Checking package version...")
try:
    from spicedb_rag_auth import __version__
    print(f"   ✅ Package version: {__version__}")
except ImportError:
    print("   ⚠️  Version not found (not critical)")

# Summary
print()
print("=" * 80)
print("✅ All tests passed! The package is ready to use.")
print()
print("Next steps:")
print("1. Make sure SpiceDB is running on localhost:50051")
print("2. Check out INTEGRATION_GUIDE.md for Jupyter notebook integration")
print("3. Run examples/standalone_example.py to see it in action")
print()
print("To test in your Jupyter notebook:")
print("  from spicedb_rag_auth import SpiceDBAuthorizer")
print()
