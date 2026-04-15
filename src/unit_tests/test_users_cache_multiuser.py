"""
Unit tests for multi-user cache isolation.

Tested Scenarios:
- Cache entries are isolated per user with identical requests
- Cache clear only affects the user's own entries
- Cache stats only show the user's own entries
- Cache settings are isolated per user

Untested Scenarios / Gaps:
- Concurrent cache access from multiple users
- Cache isolation with thousands of users
- Memory usage with many simultaneous users
- Cache invalidation across users
- Race conditions in multi-user scenarios
- Cache performance degradation with many users

Test Strategy:
- Database-backed tests with @pytest.mark.django_db
- Test cache isolation between two users
- Verify user-specific operations don't affect other users
- Test settings, data, and stats isolation
"""
import pytest
from users.models import APIResponseCache
from users.cache import get_cache


@pytest.mark.django_db
class TestCacheMultiUserIsolation:
    """Test that cache is properly isolated between users."""
    
    def test_cache_entries_isolated_per_user(self, user, another_user):
        """Test that two users with identical requests get separate cache entries."""
        # Enable cache for both users
        cache1 = get_cache(user)
        cache2 = get_cache(another_user)
        
        cache1.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        cache2.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Same request parameters for both users
        provider_type = 'bitbucket_server'
        provider_id = 'git.example.com'
        endpoint = '/repos'
        params = {'project': 'TEST', 'repo': 'myrepo'}
        response_data_user1 = {'data': 'user1_data'}
        response_data_user2 = {'data': 'user2_data'}
        
        # User 1 caches a response
        cache1.set(
            provider_type=provider_type,
            provider_id=provider_id,
            endpoint=endpoint,
            params=params,
            response_data=response_data_user1
        )
        
        # User 2 caches a response with same parameters but different data
        cache2.set(
            provider_type=provider_type,
            provider_id=provider_id,
            endpoint=endpoint,
            params=params,
            response_data=response_data_user2
        )
        
        # Verify both cache entries exist
        assert APIResponseCache.objects.filter(user=user).count() == 1
        assert APIResponseCache.objects.filter(user=another_user).count() == 1
        
        # Verify user1 gets their own cached data
        cached1 = cache1.get(provider_type, provider_id, endpoint, params)
        assert cached1 is not None
        assert cached1['data'] == response_data_user1
        
        # Verify user2 gets their own cached data
        cached2 = cache2.get(provider_type, provider_id, endpoint, params)
        assert cached2 is not None
        assert cached2['data'] == response_data_user2
        
        # Verify the data is different
        assert cached1['data'] != cached2['data']
    
    def test_cache_clear_only_affects_own_entries(self, user, another_user):
        """Test that clearing cache only affects the user's own entries."""
        cache1 = get_cache(user)
        cache2 = get_cache(another_user)
        
        cache1.update_settings(cache_enabled=True)
        cache2.update_settings(cache_enabled=True)
        
        # Both users cache some data
        cache1.set('github', 'github.com', '/repos', {}, {'user1': 'data'})
        cache2.set('github', 'github.com', '/repos', {}, {'user2': 'data'})
        
        # Verify both have cache entries
        assert APIResponseCache.objects.filter(user=user).count() == 1
        assert APIResponseCache.objects.filter(user=another_user).count() == 1
        
        # User1 clears their cache
        count = cache1.clear()
        assert count == 1
        
        # Verify user1's cache is cleared but user2's is not
        assert APIResponseCache.objects.filter(user=user).count() == 0
        assert APIResponseCache.objects.filter(user=another_user).count() == 1
    
    def test_cache_stats_only_show_own_entries(self, user, another_user):
        """Test that stats only show the user's own cache entries."""
        cache1 = get_cache(user)
        cache2 = get_cache(another_user)
        
        cache1.update_settings(cache_enabled=True)
        cache2.update_settings(cache_enabled=True)
        
        # User1 caches 2 entries
        cache1.set('github', 'github.com', '/repos', {}, {'data': '1'})
        cache1.set('github', 'github.com', '/branches', {}, {'data': '2'})
        
        # User2 caches 3 entries
        cache2.set('bitbucket', 'bitbucket.org', '/repos', {}, {'data': '1'})
        cache2.set('bitbucket', 'bitbucket.org', '/branches', {}, {'data': '2'})
        cache2.set('bitbucket', 'bitbucket.org', '/commits', {}, {'data': '3'})
        
        # Get stats for each user
        stats1 = cache1.stats()
        stats2 = cache2.stats()
        
        # Verify each user only sees their own entries
        assert stats1['total_entries'] == 2
        assert stats2['total_entries'] == 3
        
        # Verify provider breakdown is correct
        assert 'github' in stats1['by_provider']
        assert 'bitbucket' not in stats1['by_provider']
        
        assert 'bitbucket' in stats2['by_provider']
        assert 'github' not in stats2['by_provider']
    
    def test_settings_isolated_per_user(self, user, another_user):
        """Test that cache settings are isolated per user."""
        cache1 = get_cache(user)
        cache2 = get_cache(another_user)
        
        # User1 enables cache with 60 min TTL
        cache1.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # User2 disables cache with 5 min TTL
        cache2.update_settings(cache_enabled=False, cache_ttl_minutes=5)
        
        # Verify settings are independent
        settings1 = cache1.get_settings()
        settings2 = cache2.get_settings()
        
        assert settings1['cache_enabled'] is True
        assert settings1['cache_ttl_minutes'] == 60
        
        assert settings2['cache_enabled'] is False
        assert settings2['cache_ttl_minutes'] == 5
        
        # Verify user1 can cache but user2 cannot
        cache1.set('github', 'github.com', '/test', {}, {'data': 'test'})
        cache2.set('github', 'github.com', '/test', {}, {'data': 'test'})
        
        # User1 should have cache entry, user2 should not (cache disabled)
        assert APIResponseCache.objects.filter(user=user).count() == 1
        assert APIResponseCache.objects.filter(user=another_user).count() == 0
