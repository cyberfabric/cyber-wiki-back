"""
Middleware to store current user in thread-local storage.
This allows Git providers to access the current user for caching.
"""
from threading import current_thread


class ThreadLocalUserMiddleware:
    """Store current user in thread-local storage."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store user on current thread
        current_thread().user = getattr(request, 'user', None)
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up thread-local storage
            if hasattr(current_thread(), 'user'):
                delattr(current_thread(), 'user')
