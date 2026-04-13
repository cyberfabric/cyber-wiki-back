# Integration Tests Structure

## Overview

The integration tests are organized into modular, reusable components with clear separation of concerns.

## File Structure

```
src/integration_tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest fixtures (api_session, base_url, etc.)
├── test_helpers.py            # Common helper functions (NEW)
├── test_wiki_api.py           # Space API test scenarios
├── test_auth_api.py           # Authentication API tests
├── test_git_provider_api.py   # Git provider API tests
├── test_service_tokens_api.py # Service tokens API tests
├── README.md                   # Documentation
└── pytest.ini                  # Pytest configuration
```

## Module Responsibilities

### `test_helpers.py` (Common Utilities)
**Purpose**: Centralized location for all reusable helper functions

**Contents**:
- **Constants**: `TEST_PREFIX`, `TEST_SPACE_BASE_NAME`, `TEST_SPACE_DESCRIPTION`
- **Utility Functions**: `get_unique_id()`
- **Space Helpers**: `create_space()`, `delete_space()`, `cleanup_all_test_spaces()`
- **Favorites Helpers**: `cleanup_test_favorites()` (for future use)

**Benefits**:
- Single source of truth for helper functions
- Easy to maintain and update
- Reusable across all test files
- Clear separation from test logic

### `test_wiki_api.py` (Test Scenarios)
**Purpose**: Contains only test scenarios and assertions

**Contents**:
- Test classes organized by feature area
- Clear test methods with comprehensive logging
- Setup and teardown using helpers
- No implementation details, only test logic

**Structure**:
```python
from .test_helpers import create_space, delete_space, ...

class TestSpaceCRUD:
    def test_create_space_with_all_fields(self, api_session):
        # Test logic only - uses helpers for setup/teardown
        ...
```

### `conftest.py` (Pytest Fixtures)
**Purpose**: Pytest configuration and fixtures

**Contents**:
- `api_session`: Authenticated session with Bearer token
- `session`: Unauthenticated session
- `base_url`: API base URL from environment
- `api_token`: API token from environment
- Configuration loading logic

## Design Principles

### 1. **Independence**
Each test is completely independent:
- Creates its own test data
- Runs assertions
- Cleans up after itself

### 2. **Idempotency**
Tests can be run multiple times:
- Global cleanup removes leftover artifacts
- Unique IDs prevent conflicts
- Test prefix (`test_`) for easy identification

### 3. **Comprehensive Logging**
Every test includes:
- Test purpose and expected outcome
- Step-by-step execution logging
- Clear pass/fail indicators
- Cleanup confirmation

### 4. **Modularity**
- Helpers in `test_helpers.py`
- Tests in `test_*.py` files
- Fixtures in `conftest.py`
- Clear separation of concerns

## Usage Examples

### Using Helpers in Tests

```python
from .test_helpers import create_space, delete_space

def test_my_scenario(api_session):
    # Setup
    space = create_space(api_session, name_suffix="_my_test")
    assert space is not None
    
    try:
        # Test logic
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/spaces/{space['slug']}/",
            headers=api_session.headers
        )
        assert response.status_code == 200
        
    finally:
        # Cleanup
        delete_space(api_session, space['slug'])
```

### Adding New Helpers

When adding new helper functions:

1. **Add to `test_helpers.py`**:
   ```python
   def create_document(api_session, space_slug, **kwargs):
       """Create a test document in a space."""
       # Implementation
       ...
   ```

2. **Import in test file**:
   ```python
   from .test_helpers import create_document
   ```

3. **Use in tests**:
   ```python
   def test_document_creation(api_session):
       space = create_space(api_session)
       doc = create_document(api_session, space['slug'])
       # Test logic...
   ```

## Best Practices

### ✅ DO
- Put all helper functions in `test_helpers.py`
- Keep test files focused on test scenarios
- Use descriptive helper function names
- Add docstrings to all helpers
- Clean up test artifacts in `finally` blocks
- Use unique IDs for all test data

### ❌ DON'T
- Mix helper implementation with test logic
- Duplicate helper functions across test files
- Leave test artifacts in the database
- Hard-code test data (use helpers)
- Skip cleanup steps

## Running Tests

```bash
# Run all wiki tests
./scripts/run-backend-tests.sh --wiki-only

# Run all integration tests
./scripts/run-backend-tests.sh

# Run specific test
pytest src/integration_tests/test_wiki_api.py::TestSpaceCRUD::test_create_space_with_all_fields -v
```

## Future Enhancements

As more test scenarios are added:

1. **Expand `test_helpers.py`** with new helper functions:
   - Document helpers
   - Comment helpers
   - Tag helpers
   - Permission helpers

2. **Create specialized helper modules** if needed:
   - `test_helpers_spaces.py`
   - `test_helpers_documents.py`
   - `test_helpers_auth.py`

3. **Add more test files**:
   - `test_document_api.py`
   - `test_comment_api.py`
   - `test_permissions_api.py`

All new helpers should go in `test_helpers.py` (or specialized modules) to maintain clean separation.
