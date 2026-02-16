# apps/notifications/middleware.py
from django.http import HttpResponse  # Add this import at the top
import traceback
from datetime import datetime

class DebugAuthMiddleware:
    """
    Debug middleware to trace what's happening with notification endpoint requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Process request before it goes to the view
        if request.path == '/userdashboard/overview/notifications/count/':
            print(f"\n=== NOTIFICATION ENDPOINT HIT ===")
            print(f"Time: {datetime.now().strftime('%H:%M:%S.%f')}")
            print(f"Method: {request.method}")
            # Check if user attribute exists before accessing it
            if hasattr(request, 'user'):
                print(f"User: {request.user}")
                print(f"Is authenticated: {request.user.is_authenticated}")
            else:
                print(f"User: Not yet attached (AuthenticationMiddleware hasn't run)")
            print(f"Session key: {getattr(request, 'session', None).session_key if hasattr(request, 'session') else 'No session'}")
            print(f"Headers: {dict(request.headers)}")
            
        # Get response from view or next middleware
        response = self.get_response(request)
        
        # Process response after view
        if request.path == '/userdashboard/overview/notifications/count/':
            print(f"Response status: {response.status_code}")
            if response.status_code == 302:
                print(f"REDIRECT TO: {response.url}")
                traceback.print_stack()
            print("=== END NOTIFICATION REQUEST ===\n")
            
        return response


# class ExemptNotificationEndpointMiddleware:
#     """
#     Middleware to prevent authentication redirects for the notification count endpoint.
#     This allows the view to handle anonymous users appropriately.
#     """
    
#     def __init__(self, get_response):
#         self.get_response = get_response
        
#     def __call__(self, request):
#         # Mark notification endpoint as exempt from auth BEFORE AuthenticationMiddleware runs
#         if request.path == '/userdashboard/overview/notifications/count/':
#             request._auth_exempt = True
#             # Don't try to access request.user here - it doesn't exist yet!
#             print(f"🔓 Exempting notification endpoint")
            
#         response = self.get_response(request)
#         return response

# apps/notifications/middleware.py

from django.http import HttpResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
import traceback
from datetime import datetime

class ExemptNotificationEndpointMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path == '/userdashboard/overview/notifications/count/':
            # Ensure session exists BEFORE any processing
            if not request.session.session_key:
                request.session.create()
                print(f"🆕 Created session: {request.session.session_key}")
            
            # Mark as exempt
            request._auth_exempt = True
            
        response = self.get_response(request)
        
        # FINAL DEFENSE: If we get a 302 for our endpoint, render the view instead
        if request.path == '/userdashboard/overview/notifications/count/' and response.status_code == 302:
            print(f"🚫 BLOCKING 302 REDIRECT to {response.url}")
            print(f"🔄 Rendering view directly instead...")
            
            try:
                # Get the view function
                from importlib import import_module
                from django.conf import settings
                
                # Resolve the URL to get the view
                resolver_match = resolve(request.path)
                view_func = resolver_match.func
                
                # Call the view with the request
                if hasattr(view_func, 'view_class'):
                    # It's a class-based view
                    view = view_func.view_class()
                    new_response = view.dispatch(request, *resolver_match.args, **resolver_match.kwargs)
                else:
                    # It's a function-based view
                    new_response = view_func(request, *resolver_match.args, **resolver_match.kwargs)
                
                print(f"✅ Successfully rendered view, status: {new_response.status_code}")
                return new_response
                
            except Exception as e:
                print(f"❌ Error rendering view: {e}")
                traceback.print_exc()
                # Return a minimal response
                return HttpResponse(
                    '<span class="notification-badge-container"></span>', 
                    status=200, 
                    content_type='text/html'
                )
            
        return response