"""
Unit tests for cache decorator edge cases and DRF support.

Tested Scenarios:
- Decorator detects ViewSets (hasattr check for request.request)
- Unauthenticated users skip caching in ViewSets
- Cache disabled setting respected in ViewSets  
- Unknown response type handling (HttpResponse)
- Exception handling during cache operations

Untested Scenarios / Gaps:
- Full DRF Response caching (complex integration)
- ViewSet with pagination
- ViewSet with custom renderers
- Streaming responses

Test Strategy:
- Database-backed tests with @pytest.mark.django_db
- Focus on code path coverage rather than full integration
- Test ViewSet detection logic
- Test error handling paths
"""
import pytest
from django.http import HttpResponse, JsonResponse
from rest_framework.request import Request
from unittest.mock import Mock, patch

from users.decorators import cached_api_response
from users.cache import get_cache
from users.models import APIResponseCache


@pytest.mark.django_db
class TestCacheDecoratorDRF:
    """Test the cached_api_response decorator with DRF ViewSets."""
    
    def test_decorator_with_drf_viewset(self, user, request_factory):
        """Test that decorator works with DRF ViewSets."""
        # Enable cache
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Create a mock ViewSet
        call_count = {'count': 0}
        
        class MockViewSet:
            @cached_api_response()
            def list(self, provider='github', provider_id='github.com'):
                call_count['count'] += 1
                from rest_framework.response import Response
                return Response({'items': ['item1', 'item2']}, status=200)
        
        # Create request
        django_request = request_factory.get('/api/items/')
        django_request.user = user
        
        # Wrap in DRF Request
        # DRF Request wraps Django request but user needs to be set
        drf_request = Request(django_request)
        drf_request._user = user  # Set user on DRF request
        
        # Create viewset instance
        viewset = MockViewSet()
        viewset.request = drf_request
        
        # First call - should execute and cache
        response1 = viewset.list(provider='github', provider_id='github.com')
        assert response1.status_code == 200
        assert response1.data == {'items': ['item1', 'item2']}
        assert call_count['count'] == 1
        
        # Second call - should return cached response
        response2 = viewset.list(provider='github', provider_id='github.com')
        assert response2.status_code == 200
        assert response2.data == {'items': ['item1', 'item2']}
        assert call_count['count'] == 1  # Not incremented
        
        # Verify cache entry exists
        assert APIResponseCache.objects.filter(user=user).count() == 1
    
    def test_decorator_with_drf_response_caches_data_not_headers(self, user, request_factory):
        """Test that decorator caches response data but not custom headers."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        class MockViewSet:
            @cached_api_response()
            def retrieve(self, provider='github', provider_id='github.com'):
                from rest_framework.response import Response
                response = Response({'id': 1, 'name': 'Test'}, status=200)
                response['X-Custom-Header'] = 'custom-value'
                response['X-Request-ID'] = '12345'
                return response
        
        django_request = request_factory.get('/api/items/1/')
        django_request.user = user
        drf_request = Request(django_request)
        drf_request._user = user
        
        viewset = MockViewSet()
        viewset.request = drf_request
        
        # First call - has custom headers and X-Cache: MISS
        response1 = viewset.retrieve(provider='github', provider_id='github.com')
        assert response1.data == {'id': 1, 'name': 'Test'}
        assert response1['X-Custom-Header'] == 'custom-value'
        assert response1['X-Request-ID'] == '12345'
        assert response1['X-Cache'] == 'MISS'
        
        # Second call - cached response has data but NOT custom headers
        # Only X-Cache and X-Cache-Date headers are added
        response2 = viewset.retrieve(provider='github', provider_id='github.com')
        assert response2.data == {'id': 1, 'name': 'Test'}  # Data is cached
        assert response2['X-Cache'] == 'HIT'  # Cache header added
        assert 'X-Cache-Date' in response2  # Cache date added
        # Custom headers are NOT preserved in cached response
        assert 'X-Custom-Header' not in response2
        assert 'X-Request-ID' not in response2
    
    def test_decorator_with_unauthenticated_user_viewset(self, request_factory):
        """Test that decorator skips caching for unauthenticated users in ViewSets."""
        call_count = {'count': 0}
        
        class MockViewSet:
            @cached_api_response()
            def list(self, provider='github', provider_id='github.com'):
                call_count['count'] += 1
                from rest_framework.response import Response
                return Response({'items': []}, status=200)
        
        # Create unauthenticated request
        django_request = request_factory.get('/api/items/')
        unauthenticated_user = Mock(is_authenticated=False)
        django_request.user = unauthenticated_user
        drf_request = Request(django_request)
        drf_request._user = unauthenticated_user
        
        viewset = MockViewSet()
        viewset.request = drf_request
        
        # Multiple calls should all execute (no caching)
        viewset.list(provider='github', provider_id='github.com')
        viewset.list(provider='github', provider_id='github.com')
        
        assert call_count['count'] == 2
        assert APIResponseCache.objects.count() == 0
    
    def test_decorator_with_cache_disabled_viewset(self, user, request_factory):
        """Test that decorator respects cache disabled setting in ViewSets."""
        # Disable cache
        cache = get_cache(user)
        cache.update_settings(cache_enabled=False)
        
        call_count = {'count': 0}
        
        class MockViewSet:
            @cached_api_response()
            def list(self, provider='github', provider_id='github.com'):
                call_count['count'] += 1
                from rest_framework.response import Response
                return Response({'items': []}, status=200)
        
        django_request = request_factory.get('/api/items/')
        django_request.user = user
        drf_request = Request(django_request)
        drf_request._user = user
        
        viewset = MockViewSet()
        viewset.request = drf_request
        
        # Multiple calls should all execute (caching disabled)
        viewset.list(provider='github', provider_id='github.com')
        viewset.list(provider='github', provider_id='github.com')
        
        assert call_count['count'] == 2
        assert APIResponseCache.objects.filter(user=user).count() == 0


@pytest.mark.django_db
class TestCacheDecoratorEdgeCases:
    """Test edge cases and error handling in cache decorator."""
    
    def test_decorator_with_unknown_response_type(self, user, request_factory):
        """Test that decorator handles unknown response types gracefully."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        @cached_api_response()
        def view_func(request):
            # Return HttpResponse instead of JsonResponse or DRF Response
            return HttpResponse('Plain text response', status=200)
        
        django_request = request_factory.get('/api/test/')
        django_request.user = user
        
        # Should not raise exception, just skip caching
        response = view_func(django_request)
        assert response.status_code == 200
        assert response.content == b'Plain text response'
        
        # No cache entry should be created
        assert APIResponseCache.objects.filter(user=user).count() == 0
    
    def test_decorator_handles_cache_set_exception(self, user, request_factory):
        """Test that decorator handles exceptions during cache.set() gracefully."""
        from users.cache import get_cache
        
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        @cached_api_response()
        def view_func(request):
            from django.http import JsonResponse
            return JsonResponse({'data': 'test'}, status=200)
        
        django_request = request_factory.get('/api/test/')
        django_request.user = user
        
        # Mock cache.set to raise an exception
        with patch('users.cache.APICache.set', side_effect=Exception("Cache error")):
            # Should not raise exception, just return response
            response = view_func(django_request)
            assert response.status_code == 200
