"""
Middleware for additional security headers and logging.
"""

import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add additional security headers to all responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection in older browsers
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self';"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )
        
        return response
