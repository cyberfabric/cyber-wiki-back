#!/bin/bash
# Run backend unit tests

set -e

cd "$(dirname "$0")/.."

echo "=== Backend Unit Tests ==="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Run unit tests
echo "🧪 Running unit tests..."
echo "   Test path: src/unit_tests/"
echo "   Pytest args: -v -rs --reuse-db --nomigrations"
echo ""

pytest src/unit_tests/ -v -rs --reuse-db --nomigrations

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "� To run with coverage, use:"
    echo "   ./scripts/pre-commit-tests.sh"
else
    echo ""
    echo "❌ Some tests failed!"
fi

exit $exit_code
