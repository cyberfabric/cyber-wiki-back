"""
Custom middleware for debugging and development.
"""
import logging

logger = logging.getLogger(__name__)


class SessionCookieDebugMiddleware:
    """
    Middleware to debug session cookie settings.
    Logs the Set-Cookie header to help diagnose session persistence issues.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log all cookies being set for debugging
        cookies = response.cookies
        if 'sessionid' in cookies:
            cookie = cookies['sessionid']
            logger.warning(f"🍪 Session cookie being set:")
            logger.warning(f"   Value: {cookie.value}")
            logger.warning(f"   Max-Age: {cookie.get('max-age', 'NOT SET')}")
            logger.warning(f"   Expires: {cookie.get('expires', 'NOT SET')}")
            logger.warning(f"   Path: {cookie.get('path', 'NOT SET')}")
            logger.warning(f"   Domain: {cookie.get('domain', 'NOT SET')}")
            logger.warning(f"   SameSite: {cookie.get('samesite', 'NOT SET')}")
            logger.warning(f"   HttpOnly: {cookie.get('httponly', 'NOT SET')}")
            logger.warning(f"   Secure: {cookie.get('secure', 'NOT SET')}")
        
        return response
