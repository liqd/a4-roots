from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import UpdateView
from django.views.generic import View
from guest_user.mixins import AllowGuestUserMixin

from apps.userdashboard.views import UserDashboardNotificationsBaseView

from .forms import NotificationSettingsForm
from .models import Notification
from .models import NotificationSettings
from .tasks import send_recently_completed_project_notifications
from .tasks import send_recently_started_project_notifications
from .tasks import send_upcoming_event_notifications
from .utils import get_notifications_by_section


def is_safe_url(url):
    parsed = urlparse(url)
    return not parsed.netloc or parsed.netloc in settings.ALLOWED_HOSTS


class NotificationSettingsView(LoginRequiredMixin, UpdateView):
    model = NotificationSettings
    form_class = NotificationSettingsForm
    template_name = "a4_candy_notifications/settings.html"

    def get_object(self):
        """Get or create notification settings for the current user."""
        return NotificationSettings.get_for_user(self.request.user)

    def get_success_url(self):
        return reverse("account_notification_settings")


class TriggerAllNotificationTasksView(LoginRequiredMixin, View):
    """View to trigger all notification tasks (staff only)"""

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request):
        # Run all tasks
        send_recently_started_project_notifications.delay()
        send_recently_completed_project_notifications.delay()
        send_upcoming_event_notifications.delay()

        messages.success(request, "All notification tasks have been queued")
        return redirect("account_notification_settings")


class MarkAllNotificationsAsReadView(UserDashboardNotificationsBaseView):
    """Mark all notifications as read with HTMX support"""

    def post(self, request, *args, **kwargs):
        section = request.POST.get("section", "")
        notifications = Notification.objects.filter(recipient=request.user, read=False)

        if section:
            notifications = get_notifications_by_section(notifications, section)
            notifications.update(read=True, read_at=timezone.now())

        if request.headers.get("HX-Request"):
            context = self._get_notifications_context()
            response = render(
                request, "a4_candy_notifications/_notifications_partial.html", context
            )
            response["HX-Trigger"] = "updateNotificationCount"
            return response
        else:
            return redirect("userdashboard-notifications")


class MarkNotificationAsReadView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, id=kwargs["pk"], recipient=request.user
        )
        notification.mark_as_read()

        redirect_to = request.GET.get("redirect_to")
        if redirect_to and is_safe_url(redirect_to):
            return redirect(redirect_to)

        messages.success(request, "Notification marked as read")
        return redirect(request.META.get("HTTP_REFERER", "home"))


class NotificationCountPartialView(UserDashboardNotificationsBaseView):
    """HTMX partial for just the notification badge"""

    def get(self, request, *args, **kwargs):
        unread_count = 0
        if request.user.is_authenticated:
            unread_count = Notification.objects.unread_count_for_user(request.user)

        return render(
            request,
            "a4_candy_notifications/_notifications_button_partial.html",
            {"user": request.user, "unread_count": unread_count},
        )


# class NotificationCountPartialView(UserDashboardNotificationsBaseView, AllowGuestUserMixin):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         # Add debugging to see user state
#         print(f"User: {request.user}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
#         print(f"Session key: {request.session.session_key}")
        
#         unread_count = 0
#         print('got to get')
        
#         # Check both authenticated and guest
#         if request.user.is_authenticated or getattr(request.user, 'is_guest_user', False):
#             print('got to auth/guest')
#             unread_count = Notification.objects.unread_count_for_user(request.user)
#         else:
#             print('User is neither authenticated nor guest')
            
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {"user": request.user, "unread_count": unread_count},
#         )

# class NotificationCountPartialView(UserDashboardNotificationsBaseView):  # Remove AllowGuestUserMixin
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         unread_count = 0
#         print('got to get')
        
#         # Check if user can have notifications (authenticated or guest)
#         if request.user.is_authenticated or getattr(request.user, 'is_guest_user', False):
#             print('got to auth/guest')
#             unread_count = Notification.objects.unread_count_for_user(request.user)
#         else:
#             # For completely unauthenticated users, just return empty state
#             # This prevents the redirect middleware from kicking in
#             return render(
#                 request,
#                 "a4_candy_notifications/_notifications_button_partial.html",
#                 {"user": request.user, "unread_count": 0},
#             )

#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {"user": request.user, "unread_count": unread_count},
#         )


# class NotificationCountPartialView(UserDashboardNotificationsBaseView):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         # First, check if user is completely anonymous (not even guest)
#         if not request.user.is_authenticated and not getattr(request.user, 'is_guest_user', False):
#             # Return empty response - this prevents the redirect
#             return render(
#                 request,
#                 "a4_candy_notifications/_notifications_button_partial.html",
#                 {"user": request.user, "unread_count": 0, "empty": True}
#             )
        
#         # For authenticated or guest users, proceed normally
#         unread_count = 0
#         print('got to get')
        
#         if request.user.is_authenticated or getattr(request.user, 'is_guest_user', False):
#             print('got to auth/guest')
#             unread_count = Notification.objects.unread_count_for_user(request.user)
            
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {"user": request.user, "unread_count": unread_count, "empty": False}
#         )

# from .models import Notification  # adjust import as needed

# class NotificationCountPartialView(UserDashboardNotificationsBaseView):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         # This now runs for ALL requests because middleware exempts it from auth
#         # Log what's happening for debugging
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id if request.user.id else 'None'}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
#         print(f"Session key: {request.session.session_key}")
        
#         unread_count = 0
        
#         # CASE 1: Authenticated user - show real notification count
#         if request.user.is_authenticated and not getattr(request.user, 'is_guest_user', False):
#             print("✅ Authenticated user - showing notifications")
#             unread_count = Notification.objects.unread_count_for_user(request.user)
#             show_badge = True
            
#         # CASE 2: Guest user - show notifications (same as authenticated)
#         elif getattr(request.user, 'is_guest_user', False):
#             print("✅ Guest user - showing notifications")
#             unread_count = Notification.objects.unread_count_for_user(request.user)
#             show_badge = True
            
#         # CASE 3: Anonymous user - show nothing
#         else:
#             print("❌ Anonymous user - showing empty badge")
#             unread_count = 0
#             show_badge = False
            
#         # Render the template with appropriate context
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {
#                 "user": request.user,
#                 "unread_count": unread_count,
#                 "show_badge": show_badge,
#                 "is_guest": getattr(request.user, 'is_guest_user', False)
#             }
#         )
    

# # apps/notifications/views.py
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class NotificationCountPartialView(UserDashboardNotificationsBaseView):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"Session key: {request.session.session_key}")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id if request.user.id else 'None'}")
#         print(f"User type: {type(request.user).__name__}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
#         print(f"Is anonymous: {request.user.is_anonymous}")
        
#         # Check if this user actually exists in the database
#         if request.user.id:
#             try:
#                 db_user = User.objects.get(id=request.user.id)
#                 print(f"DB user: {db_user.username}, Is guest: {getattr(db_user, 'is_guest_user', False)}")
#             except User.DoesNotExist:
#                 print(f"⚠️ User ID {request.user.id} does NOT exist in database!")
#         else:
#             print("No user ID - anonymous")
        
#         # If this is a guest user with ID 1, that's wrong
#         if getattr(request.user, 'is_guest_user', False) and request.user.id == 1:
#             print("🚨 CRITICAL: Guest user has admin ID! This should never happen.")
#             # Check if this is actually the admin user
#             try:
#                 admin = User.objects.get(id=1)
#                 print(f"Admin user in DB: {admin.username}, Is staff: {admin.is_staff}")
#                 if admin.username == request.user.username:
#                     print("❗ The guest user IS the admin user - they're the same object!")
#             except:
#                 pass
        
#         # Normal logic
#         can_have_notifications = (
#             request.user.is_authenticated or 
#             getattr(request.user, 'is_guest_user', False)
#         )
        
#         unread_count = 0
#         if can_have_notifications and request.user.id:
#             try:
#                 unread_count = Notification.objects.unread_count_for_user(request.user)
#             except Exception as e:
#                 print(f"Error getting notifications: {e}")
        
#         return render(...)



# class NotificationCountPartialView(UserDashboardNotificationsBaseView, AllowGuestUserMixin):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"Session key: {request.session.session_key}")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id if request.user.id else 'None'}")
#         print(f"User type: {type(request.user).__name__}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
        
#         # Check if this is actually a guest user
#         is_guest = getattr(request.user, 'is_guest_user', False)
        
#         # If user is authenticated but NOT a guest, and we're expecting a guest,
#         # there's a serious problem with the guest authentication
#         if request.user.is_authenticated and not is_guest:
#             print("🚨 WARNING: Authenticated non-guest user in guest-only context!")
#             # For now, treat them as guest? Or return empty?
#             # Let's return empty to be safe
#             return render(
#                 request,
#                 "a4_candy_notifications/_notifications_button_partial.html",
#                 {
#                     "user": request.user,
#                     "unread_count": 0,
#                     "show_badge": False
#                 }
#             )
        
#         # Normal logic for guests
#         unread_count = 0
#         if request.user.is_authenticated or is_guest:
#             try:
#                 unread_count = Notification.objects.unread_count_for_user(request.user)
#             except Exception as e:
#                 print(f"Error: {e}")
        
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {
#                 "user": request.user,
#                 "unread_count": unread_count,
#                 "show_badge": True
#             }
#         )


# from guest_user.mixins import AllowGuestUserMixin

# class NotificationCountPartialView(AllowGuestUserMixin, UserDashboardNotificationsBaseView):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         # The AllowGuestUserMixin should already handle guest access
#         # Now you can just write your view logic
        
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Has guest attribute: {hasattr(request.user, 'guest')}")
        
#         unread_count = 0
#         if request.user.is_authenticated:
#             # This includes both regular users and guests (thanks to the mixin)
#             try:
#                 unread_count = Notification.objects.unread_count_for_user(request.user)
#             except Exception as e:
#                 print(f"Error: {e}")
        
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {
#                 "user": request.user,
#                 "unread_count": unread_count,
#                 "show_badge": request.user.is_authenticated
#             }
#         )
    





#     # apps/notifications/decorators.py
# from functools import wraps
# from django.http import HttpResponse

# def prevent_redirect_for_notification_endpoint(view_func):
#     """Prevent authentication redirects for the notification endpoint"""
#     @wraps(view_func)
#     def wrapper(request, *args, **kwargs):
#         if request.path == '/userdashboard/overview/notifications/count/':
#             # If session doesn't exist, create one immediately
#             if not request.session.session_key:
#                 request.session.create()
#                 print(f"🆕 Created session early: {request.session.session_key}")
            
#             # Force session save
#             request.session.modified = True
#             request.session.save()
            
#             # Now execute the view
#             return view_func(request, *args, **kwargs)
#         return view_func(request, *args, **kwargs)
#     return wrapper




# @method_decorator(prevent_redirect_for_notification_endpoint, name='dispatch')
# class NotificationCountPartialView(AllowGuestUserMixin, UserDashboardNotificationsBaseView):
#     def get(self, request, *args, **kwargs):
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id}")
#         print(f"Session key: {request.session.session_key}")
#         print(f"Session exists: {request.session.exists(request.session.session_key)}")
        
#         # Double-check session
#         if not request.session.session_key:
#             request.session.create()
#             print(f"🆕 Created session in view: {request.session.session_key}")
        
#         unread_count = 0
#         if request.user.is_authenticated:
#             try:
#                 unread_count = Notification.objects.unread_count_for_user(request.user)
#             except Exception as e:
#                 print(f"Error: {e}")
        
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {
#                 "user": request.user,
#                 "unread_count": unread_count,
#                 "show_badge": request.user.is_authenticated
#             }
#         )
    


# from django.shortcuts import render
# from django.views.generic import View
# from guest_user.mixins import AllowGuestUserMixin

# class NotificationCountPartialView(AllowGuestUserMixin, UserDashboardNotificationsBaseView):
#     """HTMX partial for just the notification badge"""
    
#     def get(self, request, *args, **kwargs):
#         # CRITICAL DEBUG - ADD THIS BACK
#         print(f"\n=== CURRENT SESSION DEBUG ===")
#         print(f"Session key: {request.session.session_key}")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
#         print(f"Session exists: {request.session.exists(request.session.session_key) if request.session.session_key else False}")
        
#         # Ensure session exists
#         if not request.session.session_key:
#             request.session.create()
#             print(f"🆕 View created session: {request.session.session_key}")
        
#         print(f"\n=== NOTIFICATION VIEW EXECUTING ===")
#         print(f"User: {request.user}")
#         print(f"User ID: {request.user.id}")
#         print(f"Session key: {request.session.session_key}")
#         print(f"Is authenticated: {request.user.is_authenticated}")
        
#         unread_count = 0
#         if request.user.is_authenticated:
#             try:
#                 # Use your notification model here
#                 unread_count = Notification.objects.unread_count_for_user(request.user)
#                 print(f"Unread count: {unread_count}")
#             except Exception as e:
#                 print(f"Error getting notifications: {e}")
        
#         # Always return the template
#         return render(
#             request,
#             "a4_candy_notifications/_notifications_button_partial.html",
#             {
#                 "user": request.user,
#                 "unread_count": unread_count,
#                 "show_badge": request.user.is_authenticated
#             }
#         )
    


# # apps/notifications/views.py
# from django.shortcuts import render
# from django.views.generic import View
# from django.http import HttpResponse

# class NotificationCountPartialView(View):
#     """Simple view for notification badge - works for ALL users"""
    
#     def get(self, request, *args, **kwargs):
#         print(f"\n=== SIMPLE VIEW ===")
#         print(f"User ID: {request.user.id}")
#         print(f"Is guest: {getattr(request.user, 'is_guest_user', False)}")
        
#         unread_count = 0
#         show_badge = False
        
#         # Show badge for ANY authenticated user (including guests)
#         if request.user.is_authenticated:
#             show_badge = True
#             try:
#                 # Try to get notification count
#                 if hasattr(request.user, 'notifications'):
#                     unread_count = request.user.notifications.filter(read=False).count()
#                 else:
#                     # Use your notification model
#                     from .models import Notification
#                     unread_count = Notification.objects.filter(
#                         recipient=request.user,
#                         read=False
#                     ).count()
#             except Exception as e:
#                 print(f"Error: {e}")
#                 unread_count = 0
        
#         # Simple HTML response
#         html = f'''
#         <span class="notification-badge-container">
#             {"<span class='position-absolute top-0 end-0 p-1 bg-danger border border-white rounded-circle notification-badge'><span class='visually-hidden'>" + str(unread_count) + " unread notifications</span></span>" if show_badge and unread_count > 0 else ""}
#         </span>
#         '''
        
#         return HttpResponse(html)