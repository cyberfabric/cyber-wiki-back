#!/bin/bash
# Script to run integration tests with proper setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

echo "=== CyberWiki Backend Integration Tests ==="
echo ""

# Load configuration (matches run-local.sh pattern)
# Load all files and merge them (later files override earlier ones)
# Priority: .env.test (lowest) < .env < .env.dev (highest)
REPO_ROOT="$(cd "$BACKEND_DIR/../.." && pwd)"
ENV_DEV="$REPO_ROOT/.env.dev"
ENV="$REPO_ROOT/.env"
ENV_TEST="src/integration_tests/.env.test"

echo "📋 Loading configuration..."
CONFIG_LOADED=false

# Temporarily disable exit on error for config loading
set +e

# Load .env.test first (lowest priority)
if [ -f "$ENV_TEST" ]; then
    set -a
    source "$ENV_TEST" 2>/dev/null
    set +a
    echo "   ✓ Loaded from .env.test"
    CONFIG_LOADED=true
fi

# Load .env (medium priority)
if [ -f "$ENV" ]; then
    set -a
    source "$ENV" 2>/dev/null
    set +a
    echo "   ✓ Loaded from .env"
    CONFIG_LOADED=true
fi

# Load .env.dev last (highest priority)
if [ -f "$ENV_DEV" ]; then
    set -a
    source "$ENV_DEV" 2>/dev/null
    set +a
    echo "   ✓ Loaded from .env.dev"
    CONFIG_LOADED=true
fi

# Re-enable exit on error
set -e

if [ "$CONFIG_LOADED" = false ]; then
    echo "⚠️  No configuration file found (.env.dev, .env, or .env.test)"
    echo "Creating .env.test from example..."
    cp src/integration_tests/.env.test.example src/integration_tests/.env.test
    echo "✅ Created .env.test - please configure it"
    echo ""
    echo "Recommended: Use .env.dev or .env (same as run-local.sh)"
    echo "  1. Set API_TOKEN (create via web UI or Django shell)"
    echo "  2. Optionally set TEST_GIT_* variables for git provider tests"
    echo ""
    exit 1
fi

# Set defaults matching run-local.sh
if [ -z "$DJANGO_SECRET_KEY" ]; then
    export DJANGO_SECRET_KEY="dev-local-secret-key-change-in-staging"
fi

# Check if API_TOKEN is set
if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "your-api-token-here" ]; then
    echo ""
    echo "⚠️  API_TOKEN not configured"
    echo ""
    echo "To create an API token:"
    echo "  1. Start server: make run"
    echo "  2. Login at http://localhost:8000/admin (admin/admin)"
    echo "  3. Go to Profile → API Tokens"
    echo "  4. Create token and add to .env or .env.dev:"
    echo "     echo 'API_TOKEN=your-token-here' >> .env"
    echo ""
    echo "Or use Django shell:"
    echo "  python manage.py shell"
    echo "  >>> from django.contrib.auth.models import User"
    echo "  >>> from users.models import ApiToken"
    echo "  >>> user = User.objects.get(username='admin')"
    echo "  >>> token = ApiToken.objects.create(user=user, name='Integration Tests')"
    echo "  >>> print(f'API Token: {token.token}')"
    echo ""
    exit 1
fi

echo "   ✓ API URL: ${API_URL:-http://localhost:8000}"
echo "   ✓ API Token: ${API_TOKEN:0:10}..."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if migrations are up to date
echo "🔍 Checking migrations..."
python manage.py migrate --check --noinput || {
    echo "⚠️  Migrations need to be applied"
    echo "Running migrations..."
    python manage.py migrate --noinput
}

# Parse command line arguments
TEST_PATH="src/integration_tests/"
PYTEST_ARGS="-v"

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            PYTEST_ARGS="$PYTEST_ARGS -n auto"
            shift
            ;;
        --coverage)
            PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=html --cov-report=term-missing"
            shift
            ;;
        --no-git)
            PYTEST_ARGS="$PYTEST_ARGS -m 'not git_provider'"
            shift
            ;;
        --live-server)
            PYTEST_ARGS="$PYTEST_ARGS -m live_server"
            shift
            ;;
        --auth-only)
            TEST_PATH="src/integration_tests/test_auth_api.py"
            shift
            ;;
        --git-only)
            TEST_PATH="src/integration_tests/test_git_provider_api.py"
            shift
            ;;
        --wiki-only)
            TEST_PATH="src/integration_tests/test_wiki_api.py"
            shift
            ;;
        --tokens-only)
            TEST_PATH="src/integration_tests/test_service_tokens_api.py"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fast              Run tests in parallel"
            echo "  --coverage          Generate coverage report"
            echo "  --no-git            Skip git provider tests"
            echo "  --live-server       Run only live server tests"
            echo "  --auth-only         Run only authentication tests"
            echo "  --git-only          Run only git provider tests"
            echo "  --wiki-only         Run only wiki/space tests"
            echo "  --tokens-only       Run only service token tests"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                  # Run all integration tests"
            echo "  $0 --fast           # Run tests in parallel"
            echo "  $0 --coverage       # Run with coverage report"
            echo "  $0 --no-git         # Skip git provider tests"
            echo "  $0 --auth-only      # Run only auth tests"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display configuration
echo "✅ Configuration loaded"
echo "   API URL: $API_URL"
echo "   API Token: ${API_TOKEN:0:10}..."
if [ -n "$TEST_GIT_BASE_URL" ]; then
    echo "   Git Provider: $TEST_GIT_PROVIDER"
    echo "   Git URL: $TEST_GIT_BASE_URL"
fi
echo ""

# Run tests
echo "🧪 Running integration tests..."
echo "   Test path: $TEST_PATH"
echo "   Pytest args: $PYTEST_ARGS"
echo ""

pytest $TEST_PATH $PYTEST_ARGS

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All integration tests passed!"
else
    echo ""
    echo "❌ Some integration tests failed"
    exit 1
fi
