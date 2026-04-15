#!/bin/bash

# Install git hooks for the backend workspace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$BACKEND_DIR/.git/hooks"

echo "🔧 Installing git hooks for backend workspace..."

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Running pre-commit checks..."

# Get the backend directory
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BACKEND_DIR"

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    source venv/bin/activate
fi

# Coverage baseline tracking
# The .coverage_baseline file stores the team's baseline coverage percentage
# It IS committed to git so all developers share the same baseline
# This prevents anyone from accidentally decreasing coverage
# The baseline is updated only when coverage increases or stays the same
COVERAGE_FILE=".coverage_baseline"
MIN_COVERAGE=20

echo ""
echo "📊 Running unit tests with coverage..."

# Run tests with coverage and capture the coverage percentage
COVERAGE_OUTPUT=$(pytest src/unit_tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=$MIN_COVERAGE \
    -v \
    --tb=short 2>&1)

TEST_EXIT_CODE=$?

# Extract coverage percentage from output
CURRENT_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -oP 'Total coverage: \K[0-9.]+' || echo "0")

# If we can't parse coverage, try alternative format
if [ "$CURRENT_COVERAGE" = "0" ]; then
    CURRENT_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep "TOTAL" | awk '{print $NF}' | sed 's/%//')
fi

echo "$COVERAGE_OUTPUT"

# Check if tests passed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    echo ""
    echo "To view detailed coverage report, open:"
    echo "  file://$BACKEND_DIR/htmlcov/index.html"
    exit 1
fi

# Check if coverage decreased
if [ -f "$COVERAGE_FILE" ]; then
    PREVIOUS_COVERAGE=$(cat "$COVERAGE_FILE")
    
    # Compare coverage (using bc for floating point comparison)
    if [ $(echo "$CURRENT_COVERAGE < $PREVIOUS_COVERAGE" | bc -l) -eq 1 ]; then
        echo ""
        echo -e "${RED}❌ Coverage decreased from ${PREVIOUS_COVERAGE}% to ${CURRENT_COVERAGE}%${NC}"
        echo ""
        echo "Please add tests to maintain or improve coverage."
        echo "To view detailed coverage report, open:"
        echo "  file://$BACKEND_DIR/htmlcov/index.html"
        echo ""
        echo "To bypass this check (not recommended), run:"
        echo "  git commit --no-verify"
        exit 1
    elif [ $(echo "$CURRENT_COVERAGE > $PREVIOUS_COVERAGE" | bc -l) -eq 1 ]; then
        echo ""
        echo -e "${GREEN}🎉 Coverage improved from ${PREVIOUS_COVERAGE}% to ${CURRENT_COVERAGE}%!${NC}"
    else
        echo ""
        echo -e "${GREEN}✅ Coverage maintained at ${CURRENT_COVERAGE}%${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}📝 Setting baseline coverage to ${CURRENT_COVERAGE}%${NC}"
fi

# Save current coverage as baseline
echo "$CURRENT_COVERAGE" > "$COVERAGE_FILE"

echo ""
echo -e "${GREEN}✅ All pre-commit checks passed!${NC}"
echo -e "${GREEN}✅ Coverage: ${CURRENT_COVERAGE}% (minimum: ${MIN_COVERAGE}%)${NC}"

exit 0
EOF

# Make the hook executable
chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "The hook will:"
echo "  - Run unit tests before each commit"
echo "  - Check coverage doesn't decrease"
echo "  - Fail if coverage drops below 20%"
echo ""
echo "To bypass the hook (not recommended):"
echo "  git commit --no-verify"
