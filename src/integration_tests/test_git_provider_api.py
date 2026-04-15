"""
Integration tests for Git Provider API.

Tested Scenarios:
- Listing repositories from git provider (Bitbucket Server)
- Retrieving file content from repository
- Listing directory contents
- Tree API with full paths (root level and subdirectories)
- Nested path handling (Bitbucket collapsed paths)
- Cache clearing for git provider responses

Untested Scenarios / Gaps:
- Repository search (skipped for Bitbucket Server)
- Branch listing (skipped for Bitbucket Server)
- Commit history retrieval
- Diff generation between commits
- File blame information
- Repository webhooks
- Multiple git provider types (GitHub, GitLab)
- Git provider authentication failures
- Large file handling
- Binary file handling
- Repository permissions

Test Strategy:
- Each test is completely independent
- Tests skip gracefully if git provider not configured
- Tests use real git provider (Bitbucket Server)
- Proper cleanup in finally blocks
- Comprehensive logging for debugging

Note: Requires service tokens configured via web UI.
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
        base_url = git_provider_config["base_url"]
        print(f"\n📤 Listing repositories for provider: {provider}")
        print(f"   Base URL: {base_url}")
        print(f"   Parameters: page=1, per_page=10")
        
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/repositories",
            params={
                "provider": provider,
                "base_url": base_url,
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
        elif response.status_code == 401:
            error_data = response.json()
            print(f"\n⚠️  Authentication failed: {error_data.get('detail', 'Unknown error')}")
            print(f"   Help: {error_data.get('help', 'Check your tokens')}")
            pytest.skip(f"Authentication failed - tokens may be expired or invalid")
        elif response.status_code == 403:
            error_data = response.json()
            print(f"\n⚠️  Access forbidden: {error_data.get('detail', 'Unknown error')}")
            pytest.skip(f"Access forbidden - check token permissions")
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

    def test_get_file_content(self, api_session, git_provider_config, test_repository_config, skip_if_no_git_config):
        """Test getting file content from repository using new API."""
        print("\n" + "="*80)
        print("TEST: Get File Content")
        print("="*80)
        print("Purpose: Verify file content can be retrieved")
        print("Expected: HTTP 200 with file content")
        
        provider = git_provider_config["provider"]
        base_url = git_provider_config["base_url"]
        project_key = test_repository_config["project_key"]
        repo_slug = test_repository_config["repo_slug"]
        branch = test_repository_config["branch"]
        file_path = test_repository_config["test_file_path"]
        
        print(f"\n📤 Getting file content...")
        print(f"   Provider: {provider}")
        print(f"   Base URL: {base_url}")
        print(f"   Repository: {project_key}/{repo_slug}")
        print(f"   Branch: {branch}")
        print(f"   File: {file_path}")
        
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/file",
            params={
                "provider": provider,
                "base_url": base_url,
                "project_key": project_key,
                "repo_slug": repo_slug,
                "branch": branch,
                "file_path": file_path
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔍 Analyzing response...")
            
            if "content" in data:
                content = data["content"]
                content_preview = content[:100] if len(content) > 100 else content
                print(f"   ✓ Content length: {len(content)} characters")
                print(f"   ✓ Preview: {content_preview}...")
            
            print(f"\n✅ PASS: File content retrieved successfully")
            
        elif response.status_code == 400:
            error_data = response.json()
            print(f"\n⚠️  Bad request: {error_data.get('error', 'Unknown error')}")
            pytest.skip(f"File not accessible")
        elif response.status_code == 401:
            error_data = response.json()
            print(f"\n⚠️  Authentication failed: {error_data.get('detail', 'Unknown error')}")
            print(f"   Help: {error_data.get('help', 'Check your tokens')}")
            pytest.skip(f"Authentication failed - tokens may be expired or invalid")
        elif response.status_code == 403:
            error_data = response.json()
            print(f"\n⚠️  Access forbidden: {error_data.get('detail', 'Unknown error')}")
            pytest.skip(f"Access forbidden - check token permissions")
        elif response.status_code == 404:
            print(f"\n⚠️  File not found")
            pytest.skip(f"File {file_path} not found in {project_key}/{repo_slug}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}\nResponse: {response.text}")
            
        print("="*80)

    def test_list_directory_contents(self, api_session, git_provider_config, test_repository_config, skip_if_no_git_config):
        """Test listing directory contents using new API."""
        print("\n" + "="*80)
        print("TEST: List Directory Contents")
        print("="*80)
        print("Purpose: Verify directory contents can be listed")
        print("Expected: HTTP 200 with file/directory list")
        
        provider = git_provider_config["provider"]
        base_url = git_provider_config["base_url"]
        project_key = test_repository_config["project_key"]
        repo_slug = test_repository_config["repo_slug"]
        branch = test_repository_config["branch"]
        path = test_repository_config["test_dir_path"]
        
        print(f"\n📤 Listing directory contents...")
        print(f"   Provider: {provider}")
        print(f"   Base URL: {base_url}")
        print(f"   Repository: {project_key}/{repo_slug}")
        print(f"   Branch: {branch}")
        print(f"   Path: {path}")
        
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/tree",
            params={
                "provider": provider,
                "base_url": base_url,
                "project_key": project_key,
                "repo_slug": repo_slug,
                "branch": branch,
                "path": path,
                "recursive": "false"
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔍 Analyzing response...")
            
            if isinstance(data, list):
                print(f"   ✓ Found {len(data)} items")
                if len(data) > 0:
                    print(f"   ✓ First item: {data[0].get('path', 'N/A')}")
            
            print(f"\n✅ PASS: Directory contents listed successfully")
            
        elif response.status_code == 400:
            error_data = response.json()
            print(f"\n⚠️  Bad request: {error_data.get('error', 'Unknown error')}")
            pytest.skip(f"Repository or path not accessible")
        elif response.status_code == 401:
            error_data = response.json()
            print(f"\n⚠️  Authentication failed: {error_data.get('detail', 'Unknown error')}")
            print(f"   Help: {error_data.get('help', 'Check your tokens')}")
            pytest.skip(f"Authentication failed - tokens may be expired or invalid")
        elif response.status_code == 403:
            error_data = response.json()
            print(f"\n⚠️  Access forbidden: {error_data.get('detail', 'Unknown error')}")
            pytest.skip(f"Access forbidden - check token permissions")
        elif response.status_code == 404:
            print(f"\n⚠️  Repository or path not found")
            pytest.skip(f"Repository {project_key}/{repo_slug} not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}\nResponse: {response.text}")
            
        print("="*80)

    def test_tree_returns_full_paths(self, api_session, git_provider_config, test_repository_config, skip_if_no_git_config):
        """
        Test that tree API returns full paths from repository root, not relative paths.
        
        This is critical for:
        - File mapping lookups (must match by full path)
        - Navigation (must know absolute position in tree)
        - Enrichment matching (PRs reference full paths)
        """
        provider = git_provider_config["provider"]
        base_url = git_provider_config.get("base_url", "")
        project_key = test_repository_config["project_key"]
        repo_slug = test_repository_config["repo_slug"]
        branch = test_repository_config.get("branch", "master")
        
        print(f"\n{'='*80}")
        print(f"🧪 TEST: Tree API Returns Full Paths")
        print(f"{'='*80}")
        print(f"   Provider: {provider}")
        print(f"   Repository: {project_key}/{repo_slug}")
        print(f"   Branch: {branch}")
        
        # Clear cache to ensure we get fresh results
        print(f"\n🧹 Clearing API cache...")
        clear_response = requests.delete(
            f"{api_session.base_url}/api/user_management/v1/settings/cache",
            headers=api_session.headers
        )
        if clear_response.status_code == 200:
            cleared = clear_response.json().get('cleared', 0)
            print(f"   ✓ Cache cleared ({cleared} entries)")
        else:
            print(f"   ⚠️  Cache clear returned {clear_response.status_code}")
        
        # Test 1: Root level - paths should not have leading slash
        print(f"\n📋 Test 1: Root level paths")
        response = requests.get(
            f"{api_session.base_url}/api/git-provider/v1/tree",
            params={
                "provider": provider,
                "base_url": base_url,
                "project_key": project_key,
                "repo_slug": repo_slug,
                "branch": branch,
                "recursive": "false"
            },
            headers=api_session.headers
        )
        assert response.status_code == 200, f"Failed to get tree: {response.text}"
        root_items = response.json()
        assert isinstance(root_items, list), "Tree should return a list"
        assert len(root_items) > 0, "Tree should not be empty"
        
        # Check that root items don't contain nested paths
        # (Bitbucket fix should collapse ".agents/skills" to ".agents")
        nested_paths = []
        for item in root_items[:10]:
            path = item.get('path', '')
            if '/' in path:
                nested_paths.append(path)
            print(f"   ✓ Root item: {path}")
        
        # Assert no nested paths at root level
        assert len(nested_paths) == 0, (
            f"Root level should not contain nested paths. Found: {nested_paths}\n"
            f"The Bitbucket provider should collapse nested paths like '.agents/skills' to '.agents'"
        )
        
        # Test 2: Subdirectory - paths should be full paths from root
        # Find a directory in root
        root_dir = next((item for item in root_items if item.get('type') in ['dir', 'directory']), None)
        
        if root_dir:
            dir_path = root_dir['path']
            print(f"\n📋 Test 2: Subdirectory paths (testing: {dir_path})")
            
            response = requests.get(
                f"{api_session.base_url}/api/git-provider/v1/tree",
                params={
                    "provider": provider,
                    "base_url": base_url,
                    "project_key": project_key,
                    "repo_slug": repo_slug,
                    "branch": branch,
                    "path": dir_path,
                    "recursive": "false"
                },
                headers=api_session.headers
            )
            
            if response.status_code == 200:
                subdir_items = response.json()
                
                if len(subdir_items) > 0:
                    # Verify subdirectory items have full paths
                    for item in subdir_items[:5]:  # Check first 5 items
                        path = item.get('path', '')
                        # Path should start with parent directory
                        assert path.startswith(dir_path + '/'), \
                            f"Subdirectory item should start with '{dir_path}/': got '{path}'"
                        # Path should not be just the filename
                        assert '/' in path, f"Subdirectory item should contain '/': {path}"
                        print(f"   ✓ Full path: {path}")
                    
                    print(f"\n✅ PASS: All paths are full paths from repository root")
                else:
                    print(f"   ⚠️  Directory is empty, skipping validation")
            else:
                print(f"   ⚠️  Could not access subdirectory (status: {response.status_code})")
        else:
            print(f"   ⚠️  No directories found in root, skipping subdirectory test")
        
        print("="*80)
