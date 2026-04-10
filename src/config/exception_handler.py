"""
Custom exception handler for standardized error responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.utils import timezone


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized error responses.
    
    Format:
    {
        "error": "Human-readable message",
        "code": "MACHINE_READABLE_CODE",
        "details": {},
        "timestamp": "2026-04-07T10:53:00Z"
    }
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        error_code = exc.__class__.__name__.upper()
        
        # Map common exceptions to readable codes
        code_mapping = {
            'VALIDATIONERROR': 'VALIDATION_ERROR',
            'NOTAUTHENTICATED': 'AUTH_REQUIRED',
            'PERMISSIONDENIED': 'FORBIDDEN',
            'NOTFOUND': 'NOT_FOUND',
            'METHODNOTALLOWED': 'METHOD_NOT_ALLOWED',
            'THROTTLED': 'RATE_LIMIT_EXCEEDED',
        }
        
        error_code = code_mapping.get(error_code, error_code)
        
        custom_response = {
            'error': str(exc),
            'code': error_code,
            'details': response.data if isinstance(response.data, dict) else {},
            'timestamp': timezone.now().isoformat(),
        }
        
        response.data = custom_response
    
    return response
