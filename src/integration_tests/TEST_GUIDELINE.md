# Integration Test Guidelines

## Core Principles

1. **Real Backend Testing**: Use actual HTTP requests, real database, real authentication (no mocking)
2. **Test Isolation**: Each test is self-contained, creates own data, cleans up in `finally` blocks
3. **Idempotency**: Tests can run multiple times; use unique IDs (`get_unique_id()`) and `test_` prefix
4. **Comprehensive Logging**: Print test steps with ✓/✗/⚠️ indicators for debugging

## Test File Structure

**Required Header**:
```python
"""
Integration tests for [Feature] API.

Tested Scenarios:
- [List what is tested]

Untested Scenarios / Gaps:
- [List what is NOT tested and why]

Test Strategy:
- Independent tests, real backend, cleanup in finally blocks
"""
```

**Test Pattern**:
```python
class TestFeature:
    def test_scenario(self, api_session):
        """Test [specific scenario]."""
        print("\n" + "="*80)
        print("🧪 TEST: [Name]")
        print("="*80)
        
        # Setup: Use helpers from test_helpers.py for prerequisites
        space = create_space(api_session)
        
        try:
            # Test logic
            response = requests.post(...)
            assert response.status_code == 201
            print("   ✓ Test passed")
        finally:
            # Cleanup
            delete_space(api_session, space['slug'])
            print("   ✓ Cleanup completed")
```

## Helper Functions

**Golden Rule**: Use helpers from `test_helpers.py` for prerequisite objects (already tested elsewhere).

**Available Helpers**:
- **Spaces**: `create_space()`, `delete_space()`, `cleanup_all_test_spaces()`
- **Comments**: `create_comment()`, `delete_comment()`, `cleanup_test_comments()`
- **User Changes**: `create_user_change()`, `approve_user_change()`, `delete_user_change()`, `cleanup_test_user_changes()`
- **Service Tokens**: `create_service_token()`, `delete_service_token()`
- **API Tokens**: `create_api_token()`, `delete_api_token()`
- **Favorites**: `add_favorite()`, `remove_favorite()`, `cleanup_test_favorites()`

**When Adding New Helpers**:
1. Name: `create_*()`, `delete_*()`, `cleanup_*()`
2. Return: Dict on success, None on failure
3. Error handling: Catch exceptions, log warnings, don't raise
4. Defaults: Provide sensible defaults, accept `**kwargs`
5. Add to `test_helpers.py`, not individual test files

## Best Practices

**✅ DO**:
- Use helpers from `test_helpers.py` for prerequisites
- Clean up in `finally` blocks
- Test both happy paths AND error cases
- Use `get_unique_id()` for unique IDs
- Log each step with ✓/✗/⚠️
- Skip gracefully when prerequisites missing (`pytest.skip()`)

**❌ DON'T**:
- Mock the backend (use real HTTP calls)
- Share state between tests
- Hard-code IDs or leave artifacts
- Create inline prerequisites (use helpers)
- Duplicate helpers across files

## Fixtures (from conftest.py)

- **`api_session`**: Authenticated session with `base_url` and `headers` (includes Bearer token)
- **`base_url`**: API base URL (e.g., `http://localhost:8000`)
- **`api_token`**: Raw API token string

## Running Tests

```bash
./scripts/run-backend-tests.sh                    # All integration tests
./scripts/run-backend-tests.sh --wiki-only        # Specific module
pytest src/integration_tests/test_file.py -v -s   # Single file
pytest src/integration_tests/ -k "auth" -v        # Pattern match
```

## Writing New Tests

1. **Choose file**: Use existing for same API area, or create `test_[feature]_api.py`
2. **Write header**: Include "Tested Scenarios" and "Untested Scenarios / Gaps"
3. **Add helpers**: To `test_helpers.py` if reusable, otherwise in test file
4. **Write tests**: Follow pattern above (Setup → Test → Cleanup)
5. **Verify**: Run twice to ensure idempotency

## Quick Reference

**Environment**: Set `API_URL` and `API_TOKEN` in `.env` or `.env.dev`

**Common Issues**:
- Artifacts not cleaned up → Check `finally` blocks
- Tests fail together → Check for shared state
- Tests fail on re-run → Check idempotency and cleanup
