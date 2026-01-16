# Publishing langchain-spicedb to PyPI

This guide explains how to publish `langchain-spicedb` to PyPI under the `authzed` organization using Trusted Publisher authentication.

## What is Trusted Publisher Authentication?

Trusted Publisher is PyPI's recommended authentication method. It uses OpenID Connect (OIDC) to allow GitHub Actions to publish packages without needing API tokens. Benefits:
- ✅ No manual token management
- ✅ More secure (short-lived credentials)
- ✅ Automatic and seamless
- ✅ No secrets to rotate or leak

## Prerequisites

1. **GitHub Repository**: Code must be in a repository under the `authzed` GitHub organization
   - Example: `https://github.com/authzed/langchain-spicedb`

2. **PyPI Account Access**: Someone with admin access to the `authzed` PyPI account

3. **GitHub Environment** (optional but recommended): Create a `release` environment in GitHub repo settings for manual approval step

## Step 1: Configure PyPI Trusted Publisher

An admin of the `authzed` PyPI account needs to:

1. Go to https://pypi.org/manage/account/publishing/

2. Click "Add a new pending publisher"

3. Fill in the form:
   - **PyPI Project Name**: `langchain-spicedb`
   - **Owner**: `authzed`
   - **Repository name**: `langchain-spicedb` (or whatever the repo is named)
   - **Workflow name**: `publish.yml`
   - **Environment name**: `release` (optional - leave blank if not using GitHub environments)

4. Click "Add"

**Note**: The project doesn't need to exist on PyPI yet. The first publish will create it automatically.

## Step 2: Push Code to GitHub

Push your code to the `authzed/langchain-spicedb` repository:

```bash
# Add the authzed remote
git remote add authzed git@github.com:authzed/langchain-spicedb.git

# Push the langchain branch
git push authzed langchain:main
```

## Step 3: Create a GitHub Release

### Option A: Using GitHub UI

1. Go to https://github.com/authzed/langchain-spicedb/releases/new

2. Fill in:
   - **Tag**: `v0.1.0` (must match version in pyproject.toml)
   - **Release title**: `v0.1.0 - Initial Release`
   - **Description**: Add release notes

3. Click "Publish release"

The GitHub Action will automatically trigger and publish to PyPI.

### Option B: Using GitHub CLI

```bash
# Create a release
gh release create v0.1.0 \
  --title "v0.1.0 - Initial Release" \
  --notes "Initial release of langchain-spicedb integration"
```

### Option C: Manual Workflow Trigger

If you want to test without creating a release:

```bash
gh workflow run publish.yml
```

Or via GitHub UI: Actions → Publish to PyPI → Run workflow

## Step 4: Verify Publication

1. **Check GitHub Actions**: Go to the Actions tab to see the workflow run
   - URL: https://github.com/authzed/langchain-spicedb/actions

2. **Check PyPI**: Once successful, the package will be available at:
   - https://pypi.org/project/langchain-spicedb/

3. **Test installation**:
   ```bash
   pip install langchain-spicedb
   ```

## Workflow Details

The `.github/workflows/publish.yml` workflow:

1. **Triggers on**:
   - New GitHub release is published
   - Manual workflow dispatch

2. **Permissions**:
   - `id-token: write` - Required for OIDC authentication
   - `contents: read` - To checkout code

3. **Steps**:
   - Checkout code
   - Set up Python
   - Install build tools
   - Build distribution (wheel + sdist)
   - Validate distribution with twine
   - Publish to PyPI (automatic authentication via OIDC)

## Publishing New Versions

To publish a new version:

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. **Commit and push**:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.2.0"
   git push authzed main
   ```

3. **Create new release**:
   ```bash
   gh release create v0.2.0 \
     --title "v0.2.0 - New Features" \
     --notes "Release notes here"
   ```

The workflow will automatically publish the new version.

## Troubleshooting

### "Trusted publisher mismatch" error

**Problem**: PyPI rejects the publish with "Trusted publisher configuration mismatch"

**Solution**: Verify that PyPI trusted publisher config matches:
- Repository owner: `authzed`
- Repository name: exact match
- Workflow file: `publish.yml`
- Environment: `release` (or leave blank if not used)

### "Permission denied" error

**Problem**: Workflow fails with permission error

**Solution**: Ensure workflow has `id-token: write` permission:
```yaml
permissions:
  id-token: write
  contents: read
```

### Package already exists

**Problem**: First publish fails because project already exists on PyPI

**Solution**: If the project was manually created on PyPI, you need to:
1. Add the trusted publisher configuration to the existing project
2. Go to https://pypi.org/manage/project/langchain-spicedb/settings/publishing/
3. Add the trusted publisher (same details as above)

## Security Notes

- ✅ No API tokens are stored in GitHub secrets
- ✅ OIDC tokens are short-lived (minutes)
- ✅ Only works from the specified repository and workflow
- ✅ Optional: Use GitHub environments for manual approval before publish
- ✅ All publishes are auditable in GitHub Actions logs

## GitHub Environment Setup (Optional)

For extra security, require manual approval before publishing:

1. Go to repository Settings → Environments
2. Create environment named `release`
3. Add protection rules:
   - ✅ Required reviewers (add team/individuals who can approve)
   - ✅ Wait timer (optional delay before publish)

When configured, the workflow will pause and wait for approval before publishing to PyPI.

## References

- [PyPI Trusted Publishers Guide](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
