# events/permissions.py
from rest_framework import permissions

class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow organizers of an event to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
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
            
        # Check if user is the organizer
        return obj.organizer == request.user