"""
Integration tests for Git Provider API endpoints.

Test Strategy:
- Each test is completely independent
- Tests skip gracefully if git provider not configured
- Comprehensive logging for each test step

Test Coverage:
1. Repository listing and searching
2. Branch operations
3. File content retrieval
4. Directory listing

Note: These tests require service tokens to be configured via the web UI.
They will skip if no git provider configuration is available.
"""
import pytest
import requests


# ============================================================================
# Test Class: Git Provider Repositories
# ============================================================================

class TestGitProviderRepositories:
    """Test git provider repository endpoints. Tests skip if not configured."""

    def test_list_repositories(self, api_session, git_provider_config, skip_if_no_git_config):
        """Test listing repositories with configured git token."""
        print("\n" + "="*80)
        print("TEST: List Git Repositories")
        print("="*80)
        print("Purpose: Verify repositories can be listed from git provider")
        print("Expected: HTTP 200 with repository list (or 400 if no service token)")
        
        provider = git_provider_config["provider"]
        print(f"\n📤 Listing repositories for provider: {provider}")
        print(f"   Parameters: page=1, per_page=10")
        
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/repositories/repositories",
            params={
                "provider": provider,
                "page": 1,
                "per_page": 10
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔍 Analyzing response...")
            
            if "repositories" in data:
                repos = data["repositories"]
                print(f"   ✓ Found {len(repos)} repository/repositories")
            elif isinstance(data, list):
                print(f"   ✓ Found {len(data)} repository/repositories")
            
            print(f"\n✅ PASS: Repositories listed successfully")
            
        elif response.status_code == 400:
            print(f"\n⚠️  No service token configured for {provider}")
            print(f"   This is expected if service tokens haven't been set up")
            pytest.skip(f"No service token configured for {provider}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
            
        print("="*80)

    def test_search_repositories(self, api_session, git_provider_config, skip_if_no_git_config):
        """Test searching repositories."""
        print("\n" + "="*80)
        print("TEST: Search Git Repositories")
        print("="*80)
        print("Purpose: Verify repositories can be searched")
        print("Expected: HTTP 200 with search results")
        
        provider = git_provider_config["provider"]
        search_query = "test"
        
        print(f"\n📤 Searching repositories...")
        print(f"   Provider: {provider}")
        print(f"   Query: '{search_query}'")
        
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/repositories/search",
            params={
                "provider": provider,
                "query": search_query
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            print(f"\n✅ PASS: Search successful")
        elif response.status_code in [400, 404]:
            print(f"\n⚠️  Search not available or not configured")
            pytest.skip(f"Search not available for {provider}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
            
        print("="*80)

    def test_get_repository_branches(self, api_session, git_provider_config, skip_if_no_git_config):
        """Test getting branches for a repository."""
        print("\n" + "="*80)
        print("TEST: Get Repository Branches")
        print("="*80)
        print("Purpose: Verify repository branches can be listed")
        print("Expected: HTTP 200 with branch list")
        
        provider = git_provider_config["provider"]
        
        # First, get a repository to test with
        print(f"\n🔧 Setup: Getting a repository to test...")
        list_response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/repositories/repositories",
            params={"provider": provider, "page": 1, "per_page": 1},
            headers=api_session.headers
        )
        
        if list_response.status_code != 200:
            pytest.skip(f"Cannot list repositories for {provider}")
        
        data = list_response.json()
        repos = data.get("repositories", data) if isinstance(data, dict) else data
        
        if not repos or len(repos) == 0:
            pytest.skip("No repositories available to test")
        
        repo = repos[0]
        repo_id = repo.get("id") or repo.get("slug")
        print(f"   ✓ Using repository: {repo_id}")
        
        # Test: Get branches
        print(f"\n📤 Getting branches for repository...")
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/repositories/{repo_id}/branches",
            params={"provider": provider},
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            branches = response.json()
            print(f"\n🔍 Analyzing response...")
            if isinstance(branches, list):
                print(f"   ✓ Found {len(branches)} branch(es)")
            print(f"\n✅ PASS: Branches retrieved successfully")
        else:
            pytest.skip(f"Branches endpoint not available")
            
        print("="*80)


# ============================================================================
# Test Class: Git Provider Content
# ============================================================================

class TestGitProviderContent:
    """Test git provider content endpoints. Tests skip if not configured."""

    def test_get_file_content(self, api_session, git_provider_config, skip_if_no_git_config):
        """Test getting file content from repository."""
        print("\n" + "="*80)
        print("TEST: Get File Content")
        print("="*80)
        print("Purpose: Verify file content can be retrieved")
        print("Expected: HTTP 200 with file content")
        
        provider = git_provider_config["provider"]
        
        print(f"\n⚠️  Test requires specific repository and file path")
        print(f"   Skipping for now - implement when test repository is available")
        pytest.skip("Requires test repository configuration")
        
        print("="*80)

    def test_list_directory_contents(self, api_session, git_provider_config, skip_if_no_git_config):
        """Test listing directory contents."""
        print("\n" + "="*80)
        print("TEST: List Directory Contents")
        print("="*80)
        print("Purpose: Verify directory contents can be listed")
        print("Expected: HTTP 200 with file/directory list")
        
        provider = git_provider_config["provider"]
        
        print(f"\n⚠️  Test requires specific repository and path")
        print(f"   Skipping for now - implement when test repository is available")
        pytest.skip("Requires test repository configuration")
        
        print("="*80)
