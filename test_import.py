"""
Quick test to verify the package is correctly installed and importable.
Run this to make sure everything works before integrating into your notebook.
"""

print("Testing langchain-spicedb package...")
print("=" * 80)
print()

# Test 1: Core module
print("1. Testing core module import...")
try:
    from langchain_spicedb.core import SpiceDBAuthorizer, AuthorizationResult
    print("   ✅ SpiceDBAuthorizer imported successfully")
    print("   ✅ AuthorizationResult imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import core module: {e}")
    exit(1)

# Test 2: LangChain wrapper
print()
print("2. Testing LangChain wrapper import...")
try:
    from langchain_spicedb import SpiceDBAuthFilter, SpiceDBAuthLambda
    print("   ✅ SpiceDBAuthFilter imported successfully")
    print("   ✅ SpiceDBAuthLambda imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import LangChain wrapper: {e}")
    exit(1)

# Test 3: LangGraph wrapper
print()
print("3. Testing LangGraph wrapper import...")
try:
    from langchain_spicedb import create_auth_node, AuthorizationNode
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
    from langchain_spicedb import __version__
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
print("2. Check out examples/langchain_example.py to see it in action")
print("3. Run examples/langgraph_visualization_example.py for LangGraph")
print()
print("To use in your code:")
print("  from langchain_spicedb import SpiceDBRetriever, SpiceDBPermissionTool")
print()
