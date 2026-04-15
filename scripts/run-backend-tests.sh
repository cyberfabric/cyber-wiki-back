#!/bin/bash
# Run all backend tests (integration + unit)

cd "$(dirname "$0")/.."

echo "=== Backend Tests (Integration + Unit) ==="
echo ""

# Parse arguments
SKIP_INTEGRATION=false
SKIP_UNIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        --skip-unit)
            SKIP_UNIT=true
            shift
            ;;
        --unit-only)
            SKIP_INTEGRATION=true
            shift
            ;;
        --integration-only)
            SKIP_UNIT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-integration  Skip integration tests"
            echo "  --skip-unit         Skip unit tests"
            echo "  --unit-only         Run only unit tests"
            echo "  --integration-only  Run only integration tests"
            echo "  -h, --help          Show this help"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

integration_exit=0
unit_exit=0

# Run integration tests
if [ "$SKIP_INTEGRATION" = false ]; then
    echo "📋 Running integration tests..."
    if ./scripts/run-integration-tests.sh; then
        integration_exit=0
    else
        integration_exit=$?
        echo ""
        echo "⚠️  Integration tests failed or skipped (exit code: $integration_exit)"
        echo "💡 Tip: Run unit tests only with: $0 --unit-only"
    fi
else
    echo "⏭️  Skipping integration tests"
fi

# Run unit tests
if [ "$SKIP_UNIT" = false ]; then
    echo ""
    echo "📋 Running unit tests..."
    if ./scripts/run-unit-tests.sh; then
        unit_exit=0
    else
        unit_exit=$?
    fi
else
    echo "⏭️  Skipping unit tests"
fi

# Summary
echo ""
echo "=== Test Summary ==="

if [ "$SKIP_INTEGRATION" = false ]; then
    if [ $integration_exit -eq 0 ]; then
        echo "✅ Integration tests: PASSED"
    else
        echo "❌ Integration tests: FAILED (exit code: $integration_exit)"
    fi
else
    echo "⏭️  Integration tests: SKIPPED"
fi

if [ "$SKIP_UNIT" = false ]; then
    if [ $unit_exit -eq 0 ]; then
        echo "✅ Unit tests: PASSED"
    else
        echo "❌ Unit tests: FAILED"
    fi
else
    echo "⏭️  Unit tests: SKIPPED"
fi

# Exit with failure if any test suite failed
if [ $integration_exit -ne 0 ] || [ $unit_exit -ne 0 ]; then
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi

echo ""
echo "✅ All tests passed!"
exit 0
