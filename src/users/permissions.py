"""
Role-based permissions for CyberWiki.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Permission class that allows only admin users.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            return request.user.userprofile.role == 'admin'
        except AttributeError:
            return False


class IsEditorOrAbove(BasePermission):
    """
    Permission class that allows admin and editor users.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            role = request.user.userprofile.role
            return role in ['admin', 'editor']
        except AttributeError:
            return False


class IsCommenterOrAbove(BasePermission):
    """
    Permission class that allows admin, editor, and commenter users.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            role = request.user.userprofile.role
            return role in ['admin', 'editor', 'commenter']
        except AttributeError:
            return False


class IsViewerOrAbove(BasePermission):
    """
    Permission class that allows all authenticated users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
