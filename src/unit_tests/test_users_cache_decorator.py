"""
Unit tests for cache decorator.

Tested Scenarios:
- Decorator caches JSON responses
- Decorator respects cache disabled setting
- Custom endpoint functions work correctly
- Query parameters are included in cache key
- Error responses are not cached
- Unauthenticated users skip caching
- Provider parameters are handled correctly

Untested Scenarios / Gaps:
- Cache expiration and TTL
- Cache invalidation strategies
- Cache size limits
- Concurrent cache access
- Cache warming strategies
- Cache statistics and monitoring
- Different response types (not just JSON)
- Streaming responses
- Large response caching

Test Strategy:
- Database-backed tests with @pytest.mark.django_db
- Test decorator behavior with mocked views
- Verify cache entries in database
"""
import pytest
from django.http import JsonResponse

from users.decorators import cached_api_response
from users.cache import get_cache
from users.models import APIResponseCache


@pytest.mark.django_db
class TestCacheDecorator:
    """Test the cached_api_response decorator."""
    
    def test_decorator_caches_json_response(self, user, request_factory):
        """Test that decorator caches JsonResponse."""
        # Enable cache
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Create a simple view
        call_count = {'count': 0}
        
        @cached_api_response()
        def test_view(request):
            call_count['count'] += 1
            return JsonResponse({'data': 'test', 'call': call_count['count']})
        
        # First request - should call view and cache
        request = request_factory.get('/test/')
        request.user = user
        response1 = test_view(request)
        
        assert response1.status_code == 200
        assert response1['X-Cache'] == 'MISS'
        assert call_count['count'] == 1
        
        # Second request - should return cached response
        request = request_factory.get('/test/')
        request.user = user
        response2 = test_view(request)
        
        assert response2.status_code == 200
        assert response2['X-Cache'] == 'HIT'
        assert call_count['count'] == 1  # View not called again
        
        # Verify cache entry exists
        assert APIResponseCache.objects.filter(user=user).count() == 1
    
    def test_decorator_respects_cache_disabled(self, user, request_factory):
        """Test that decorator doesn't cache when disabled."""
        # Disable cache
        cache = get_cache(user)
        cache.update_settings(cache_enabled=False)
        
        call_count = {'count': 0}
        
        @cached_api_response()
        def test_view(request):
            call_count['count'] += 1
            return JsonResponse({'data': 'test'})
        
        # First request
        request = request_factory.get('/test/')
        request.user = user
        response1 = test_view(request)
        
        assert response1.status_code == 200
        assert call_count['count'] == 1
        
        # Second request - should call view again (no caching)
        request = request_factory.get('/test/')
        request.user = user
        response2 = test_view(request)
        
        assert response2.status_code == 200
        assert call_count['count'] == 2  # View called again
        
        # No cache entries
        assert APIResponseCache.objects.filter(user=user).count() == 0
    
    def test_decorator_with_custom_endpoint(self, user, request_factory):
        """Test decorator with custom endpoint function."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True)
        
        @cached_api_response(
            endpoint_func=lambda view, **kwargs: f"/repos/{kwargs['repo_slug']}"
        )
        def repo_view(request, repo_slug):
            return JsonResponse({'repo': repo_slug})
        
        # Request for repo1
        request = request_factory.get('/api/repos/repo1/')
        request.user = user
        response = repo_view(request, repo_slug='repo1')
        
        assert response.status_code == 200
        
        # Verify cache entry has custom endpoint
        cache_entry = APIResponseCache.objects.get(user=user)
        assert cache_entry.endpoint == '/repos/repo1'
    
    def test_decorator_with_query_params(self, user, request_factory):
        """Test that query parameters are included in cache key."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True)
        
        @cached_api_response()
        def test_view(request):
            page = request.GET.get('page', '1')
            return JsonResponse({'page': page})
        
        # Request with page=1
        request1 = request_factory.get('/test/?page=1')
        request1.user = user
        response1 = test_view(request1)
        assert response1['X-Cache'] == 'MISS'
        
        # Request with page=2 - different cache entry
        request2 = request_factory.get('/test/?page=2')
        request2.user = user
        response2 = test_view(request2)
        assert response2['X-Cache'] == 'MISS'
        
        # Request with page=1 again - cache hit
        request3 = request_factory.get('/test/?page=1')
        request3.user = user
        response3 = test_view(request3)
        assert response3['X-Cache'] == 'HIT'
        
        # Should have 2 cache entries (page=1 and page=2)
        assert APIResponseCache.objects.filter(user=user).count() == 2
    
    def test_decorator_doesnt_cache_errors(self, user, request_factory):
        """Test that error responses are not cached."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True)
        
        call_count = {'count': 0}
        
        @cached_api_response()
        def test_view(request):
            call_count['count'] += 1
            return JsonResponse({'error': 'Not found'}, status=404)
        
        # First request - error response
        request = request_factory.get('/test/')
        request.user = user
        response1 = test_view(request)
        
        assert response1.status_code == 404
        assert call_count['count'] == 1
        
        # Second request - should call view again (errors not cached)
        request = request_factory.get('/test/')
        request.user = user
        response2 = test_view(request)
        
        assert response2.status_code == 404
        assert call_count['count'] == 2
        
        # No cache entries
        assert APIResponseCache.objects.filter(user=user).count() == 0
    
    def test_decorator_with_unauthenticated_user(self, request_factory):
        """Test that decorator skips caching for unauthenticated users."""
        from django.contrib.auth.models import AnonymousUser
        
        call_count = {'count': 0}
        
        @cached_api_response()
        def test_view(request):
            call_count['count'] += 1
            return JsonResponse({'data': 'test'})
        
        # Request with anonymous user
        request = request_factory.get('/test/')
        request.user = AnonymousUser()
        response = test_view(request)
        
        assert response.status_code == 200
        assert call_count['count'] == 1
        
        # No cache entries
        assert APIResponseCache.objects.count() == 0
    
    def test_decorator_with_provider_params(self, user, request_factory):
        """Test decorator with provider type and ID parameters."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True)
        
        @cached_api_response(
            provider_type_param='provider',
            provider_id_param='base_url'
        )
        def provider_view(request, provider, base_url):
            return JsonResponse({'provider': provider, 'base_url': base_url})
        
        # Request
        request = request_factory.get('/api/provider/')
        request.user = user
        response = provider_view(request, provider='github', base_url='github.com')
        
        assert response.status_code == 200
        assert response['X-Cache'] == 'MISS'
        
        # Verify cache entry
        cache_entry = APIResponseCache.objects.get(user=user)
        assert cache_entry.provider_type == 'github'
        assert cache_entry.provider_id == 'github.com'
        
        # Provider params should not be in params_json
        assert 'provider' not in cache_entry.params_json
        assert 'base_url' not in cache_entry.params_json
