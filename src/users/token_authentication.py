"""
Bearer token authentication for API access.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import ApiToken


class BearerTokenAuthentication(BaseAuthentication):
    """
    Custom authentication class for Bearer token authentication.
    
    Clients should authenticate by passing the token in the Authorization header:
    Authorization: Bearer <token>
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            api_token = ApiToken.objects.select_related('user').get(token=token)
            
            # Update last used timestamp
            api_token.last_used_at = timezone.now()
            api_token.save(update_fields=['last_used_at'])
            
            return (api_token.user, None)
        except ApiToken.DoesNotExist:
            raise AuthenticationFailed('Invalid token')
    
    def authenticate_header(self, request):
        return 'Bearer'
