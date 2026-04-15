# Unit Test Guidelines

**Location:** `src/backend/src/unit_tests/`  
**Run Tests:** `./scripts/run-unit-tests.sh`

All unit tests must be centralized in `src/unit_tests/` for consistency and maintainability.

---

## Test Categories

### 1. Pure Unit Tests (No Database)
- Fast (< 1 second), no `@pytest.mark.django_db`
- Use mocks for external dependencies
- Example: `test_git_provider_bitbucket.py`

### 2. Model Tests (Database Required)
- Use `@pytest.mark.django_db` decorator
- Test model methods, properties, validation
- Use shared fixtures from `conftest.py`
- Example: `test_wiki_file_mapping.py`

### 3. Business Logic Tests (Database Required)
- Use `@pytest.mark.django_db` decorator
- Test multi-step workflows
- May involve multiple models
- Example: `test_users_cache_decorator.py`

---

## File Naming

**Pattern:** `test_<app>_<feature>.py`

**Examples:**
- `test_git_provider_bitbucket.py`
- `test_wiki_file_mapping.py`
- `test_users_cache_decorator.py`

## Required Header

```python
"""
Unit tests for <feature description>.

Tested Scenarios:
- Scenario 1
- Scenario 2

Untested Scenarios / Gaps:
- Gap 1
- Gap 2

Test Strategy:
- [Pure unit tests with mocks | Model tests with database | Business logic tests]
"""
```

---

## Best Practices

1. **Use shared fixtures** from `conftest.py` (user, space, admin_user, another_user, request_factory)
2. **Use shared helpers** from `test_helpers.py` - ALWAYS use `create_mock_response()` instead of `Mock()`
3. **Descriptive test names** - `test_nested_paths_are_collapsed_to_top_level` not `test_paths`
4. **Mock external dependencies** - Use `unittest.mock.patch` for API calls, external services
5. **Keep tests fast** - Pure: <1s, Model: <2s, Business logic: <5s
6. **Test edge cases** - Empty input, None, large datasets, boundary conditions
7. **One test per concept** - Each test should verify one specific behavior

---

## Common Patterns

**Model Tests:**
```python
@pytest.mark.django_db
class TestSpaceModel:
    def test_get_full_path(self, space):
        path = space.get_full_path('docs/readme.md')
        assert path == '/tmp/test-repo/docs/readme.md'
```

**Mock Tests:**
```python
from unittest.mock import patch
from unit_tests.test_helpers import create_mock_response

class TestProviderLogic:
    def test_request_handling(self, provider):
        # Use helper instead of Mock()
        mock_response = create_mock_response(200, {'key': 'value'})
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_data()
        
        assert result == {'key': 'value'}
```

**Decorator Tests:**
```python
@pytest.mark.django_db
class TestCacheDecorator:
    def test_decorator_caches_response(self, user, request_factory):
        call_count = {'count': 0}
        
        @cached_api_response()
        def test_view(request):
            call_count['count'] += 1
            return JsonResponse({'data': 'test'})
        
        request = request_factory.get('/test/')
        request.user = user
        
        response1 = test_view(request)
        assert response1['X-Cache'] == 'MISS'
        
        response2 = test_view(request)
        assert response2['X-Cache'] == 'HIT'
        assert call_count['count'] == 1  # Cached
```

---

## Running Tests

```bash
# Run all unit tests (recommended)
./scripts/run-unit-tests.sh

# Or use pytest directly
pytest src/unit_tests/ -v

# Run specific file
pytest src/unit_tests/test_wiki_file_mapping.py -v

# Run specific test
pytest src/unit_tests/test_wiki_file_mapping.py::TestFileMappingInheritance::test_file_inherits_from_space_default -v

# With coverage
pytest src/unit_tests/ --cov=src --cov-report=term-missing
```

---

## Available Fixtures (`conftest.py`)

- `user` - Standard test user (username: 'testuser')
- `admin_user` - Admin/superuser
- `another_user` - Second user for multi-user tests
- `space` - Test space owned by `user`
- `request_factory` - Django RequestFactory

## Available Helpers (`test_helpers.py`)

- `create_mock_response(status_code, json_data, text)` - Mock HTTP response
- `create_test_user(username, **kwargs)` - Create user with defaults
- `create_test_space(owner, slug, **kwargs)` - Create space with defaults
- `assert_mock_called_with_params(mock_obj, **params)` - Assert mock calls

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: cannot import name 'SomeModel'` | Ensure `pythonpath = src` in `pytest.ini` |
| `OperationalError: no such table` | Add `@pytest.mark.django_db` decorator |
| `fixture 'user' not found` | Ensure `conftest.py` is in `src/unit_tests/` |
| Tests taking too long | Use `--reuse-db --nomigrations` flags |

---

## Quality Checklist

Before committing:
- [ ] Comprehensive header (Tested/Untested scenarios, Strategy)
- [ ] Uses shared fixtures from `conftest.py`
- [ ] Descriptive test names
- [ ] Correct use of `@pytest.mark.django_db`
- [ ] Mocks for external dependencies
- [ ] Tests are fast (< 5s each)
- [ ] All tests pass: `./scripts/run-unit-tests.sh`

---

## Examples

- `test_git_provider_bitbucket.py` - Pure unit tests with mocks
- `test_wiki_file_mapping.py` - Model tests with database
- `test_users_cache_decorator.py` - Decorator tests
