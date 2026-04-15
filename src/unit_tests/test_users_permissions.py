"""
Unit tests for user permissions.

Tested Scenarios:
- IsAdmin permission with admin user
- IsAdmin permission with non-admin user
- IsAdmin permission with unauthenticated user
- IsEditorOrAbove permission with admin and editor
- IsEditorOrAbove permission with commenter and viewer
- IsCommenterOrAbove permission with various roles
- IsViewerOrAbove permission (all authenticated users)
- Permission handling when user has no profile

Untested Scenarios / Gaps:
- Object-level permissions
- Custom permission combinations
- Permission caching
- Group-based permissions
- Dynamic role changes

Test Strategy:
- Database tests with @pytest.mark.django_db
- Test each permission class independently
- Test with different user roles
- Test unauthenticated users
- Test edge cases (no profile)
"""
import pytest
from unittest.mock import Mock
from users.permissions import IsAdmin, IsEditorOrAbove, IsCommenterOrAbove, IsViewerOrAbove


@pytest.mark.django_db
class TestIsAdminPermission:
    """Tests for IsAdmin permission class."""
    
    def test_admin_user_has_permission(self, admin_user):
        """Test that admin user has permission."""
        permission = IsAdmin()
        request = Mock(user=admin_user)
        
        assert permission.has_permission(request, None) is True
    
    def test_non_admin_user_no_permission(self, user):
        """Test that non-admin user does not have permission."""
        permission = IsAdmin()
        request = Mock(user=user)
        
        # Default user role is 'viewer'
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        """Test that unauthenticated user does not have permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = Mock(is_authenticated=False)
        
        assert permission.has_permission(request, None) is False
    
    def test_user_without_profile_no_permission(self):
        """Test that user without profile does not have permission."""
        permission = IsAdmin()
        request = Mock()
        user_without_profile = Mock(is_authenticated=True)
        user_without_profile.userprofile = Mock(side_effect=AttributeError)
        request.user = user_without_profile
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsEditorOrAbovePermission:
    """Tests for IsEditorOrAbove permission class."""
    
    def test_admin_user_has_permission(self, admin_user):
        """Test that admin user has permission."""
        permission = IsEditorOrAbove()
        request = Mock(user=admin_user)
        
        assert permission.has_permission(request, None) is True
    
    def test_editor_user_has_permission(self, user):
        """Test that editor user has permission."""
        # Change user role to editor
        user.userprofile.role = 'editor'
        user.userprofile.save()
        
        permission = IsEditorOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_commenter_user_no_permission(self, user):
        """Test that commenter user does not have permission."""
        user.userprofile.role = 'commenter'
        user.userprofile.save()
        
        permission = IsEditorOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is False
    
    def test_viewer_user_no_permission(self, user):
        """Test that viewer user does not have permission."""
        # Default role is viewer
        permission = IsEditorOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        """Test that unauthenticated user does not have permission."""
        permission = IsEditorOrAbove()
        request = Mock()
        request.user = Mock(is_authenticated=False)
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsCommenterOrAbovePermission:
    """Tests for IsCommenterOrAbove permission class."""
    
    def test_admin_user_has_permission(self, admin_user):
        """Test that admin user has permission."""
        permission = IsCommenterOrAbove()
        request = Mock(user=admin_user)
        
        assert permission.has_permission(request, None) is True
    
    def test_editor_user_has_permission(self, user):
        """Test that editor user has permission."""
        user.userprofile.role = 'editor'
        user.userprofile.save()
        
        permission = IsCommenterOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_commenter_user_has_permission(self, user):
        """Test that commenter user has permission."""
        user.userprofile.role = 'commenter'
        user.userprofile.save()
        
        permission = IsCommenterOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_viewer_user_no_permission(self, user):
        """Test that viewer user does not have permission."""
        # Default role is viewer
        permission = IsCommenterOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        """Test that unauthenticated user does not have permission."""
        permission = IsCommenterOrAbove()
        request = Mock()
        request.user = Mock(is_authenticated=False)
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsViewerOrAbovePermission:
    """Tests for IsViewerOrAbove permission class."""
    
    def test_admin_user_has_permission(self, admin_user):
        """Test that admin user has permission."""
        permission = IsViewerOrAbove()
        request = Mock(user=admin_user)
        
        assert permission.has_permission(request, None) is True
    
    def test_editor_user_has_permission(self, user):
        """Test that editor user has permission."""
        user.userprofile.role = 'editor'
        user.userprofile.save()
        
        permission = IsViewerOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_commenter_user_has_permission(self, user):
        """Test that commenter user has permission."""
        user.userprofile.role = 'commenter'
        user.userprofile.save()
        
        permission = IsViewerOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_viewer_user_has_permission(self, user):
        """Test that viewer user has permission."""
        # Default role is viewer
        permission = IsViewerOrAbove()
        request = Mock(user=user)
        
        assert permission.has_permission(request, None) is True
    
    def test_unauthenticated_user_no_permission(self):
        """Test that unauthenticated user does not have permission."""
        permission = IsViewerOrAbove()
        request = Mock()
        request.user = Mock(is_authenticated=False)
        
        assert permission.has_permission(request, None) is False
    
    def test_any_authenticated_user_has_permission(self, user):
        """Test that any authenticated user has permission regardless of role."""
        permission = IsViewerOrAbove()
        request = Mock(user=user)
        
        # Test with different roles
        for role in ['admin', 'editor', 'commenter', 'viewer']:
            user.userprofile.role = role
            user.userprofile.save()
            assert permission.has_permission(request, None) is True
