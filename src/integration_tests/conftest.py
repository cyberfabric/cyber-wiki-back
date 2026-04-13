"""
Pytest fixtures and configuration for integration tests.

Configuration is loaded from .env.dev (same as run-local.sh) or .env.test
"""
import os
import pytest
import requests
from pathlib import Path
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient
from users.models import ApiToken, UserProfile


def load_env_file(filepath):
    """Load environment variables from a file."""
    if not os.path.exists(filepath):
        return False
    
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Only set if not already set
                if key not in os.environ:
                    os.environ[key] = value
    return True


# Load configuration matching run-local.sh pattern
# Priority: .env.dev > .env > .env.test > defaults
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
env_dev_path = repo_root / '.env.dev'
env_path = repo_root / '.env'
env_test_path = Path(__file__).parent / '.env.test'

if load_env_file(env_dev_path):
    print(f"✓ Loaded configuration from {env_dev_path}")
elif load_env_file(env_path):
    print(f"✓ Loaded configuration from {env_path}")
elif load_env_file(env_test_path):
    print(f"✓ Loaded configuration from {env_test_path}")
else:
    print("⚠ No .env.dev, .env, or .env.test found, using defaults")

# Set defaults matching run-local.sh
if 'DJANGO_SECRET_KEY' not in os.environ:
    os.environ['DJANGO_SECRET_KEY'] = 'dev-local-secret-key-change-in-staging'


@pytest.fixture(scope="session")
def base_url():
    """
    Base URL for API requests.
    Points to already running server (e.g. started by run-local.sh).
    """
    url = os.environ.get("API_URL", "http://localhost:8000")
    print(f"Using API URL: {url}")
    return url


@pytest.fixture(scope="session")
def api_token():
    """
    Get API token from environment variable.
    This token should be created via the running server's UI or Django shell.
    """
    token = os.environ.get("API_TOKEN")
    if not token or token == "your-api-token-here":
        pytest.fail(
            "API_TOKEN not configured. "
            "Create a token via the web UI (Profile → API Tokens) "
            "and add it to .env.dev or .env.test"
        )
    print(f"Using API token: {token[:10]}...")
    return token


@pytest.fixture(scope="session")
def api_session(api_token, base_url):
    """
    Create a requests session with authentication headers.
    This is the primary fixture for making authenticated API calls.
    Session-scoped to allow use in module-scoped fixtures.
    """
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    })
    session.base_url = base_url
    return session


@pytest.fixture(scope="session")
def session(base_url):
    """
    Create an unauthenticated requests session.
    Use this for testing login endpoints and unauthenticated access.
    Session-scoped to allow use in module-scoped fixtures.
    """
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.base_url = base_url
    return session


@pytest.fixture
def git_provider_config():
    """
    Git provider configuration for testing.
    Should be set via environment variables.
    """
    return {
        "provider": os.environ.get("TEST_GIT_PROVIDER", "bitbucket_server"),
        "base_url": os.environ.get("TEST_GIT_BASE_URL"),
        "username": os.environ.get("TEST_GIT_USERNAME"),
        "token": os.environ.get("TEST_GIT_TOKEN"),
    }


@pytest.fixture
def skip_if_no_git_config(git_provider_config):
    """Skip test if git provider is not configured."""
    if not all([
        git_provider_config["base_url"],
        git_provider_config["username"],
        git_provider_config["token"]
    ]):
        pytest.skip("Git provider not configured. Set TEST_GIT_* environment variables.")
