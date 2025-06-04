# events/permissions.py - Update with role-based permissions
from rest_framework import permissions
from django.contrib.auth.models import Group

class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow organizers of an event to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if the user has permission to manage all events
        if request.user.has_perm('events.can_manage_all_events'):
            return True
            
        # Write permissions are only allowed to the organizer of the event
        return obj.organizer == request.user

class IsOrganizerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow organizers or staff to access object
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow staff access
        if request.user.is_staff:
            return True
            
        # Check if the user has permission to manage all events
        if request.user.has_perm('events.can_manage_all_events'):
            return True
            
        # Check if user is the organizer
        return obj.organizer == request.user

class CanCreateEvent(permissions.BasePermission):
    """
    Permission to check if user can create events
    """
    def has_permission(self, request, view):
        # Only allow authenticated users
        if not request.user.is_authenticated:
            return False
            
        # Check if user has the permission
        if request.user.has_perm('events.can_create_event'):
            # Additionally check if user's role is approved (for hosts)
            try:
                user_role = request.user.role
                
                # Admin and event managers can always create events
                if user_role.role in ['admin', 'event_manager']:
                    return True
                    
                # Hosts need approval
                if user_role.role == 'host':
                    return user_role.is_approved
                    
                # Buyers cannot create events
                return False
                
            except:
                # If user has no role assigned
                return False
                
        return False

class CanManageEventCategory(permissions.BasePermission):
    """
    Permission to check if user can manage event categories
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Check if user has the permission
        return request.user.has_perm('events.can_manage_categories')