# users/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User, Group
from .models import UserRole

@login_required
@permission_required('auth.change_user', raise_exception=True)
def manage_user_roles(request):
    """
    Admin view for managing user roles
    """
    # Get all users with their roles
    users = User.objects.all().select_related('role').order_by('username')
    
    # Get all possible roles from UserRole.ROLE_CHOICES
    role_choices = UserRole.ROLE_CHOICES
    
    # Handle role updates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_role':
            user_id = request.POST.get('user_id')
            new_role = request.POST.get('role')
            approval_status = request.POST.get('is_approved') == 'on'
            
            user = get_object_or_404(User, id=user_id)
            user_role, created = UserRole.objects.get_or_create(user=user)
            
            # Update role
            user_role.role = new_role
            
            # Update approval status
            if approval_status and not user_role.is_approved:
                user_role.is_approved = True
                user_role.approved_by = request.user
                user_role.approval_date = timezone.now()
            elif not approval_status:
                user_role.is_approved = False
                user_role.approved_by = None
                user_role.approval_date = None
                
            user_role.save()
            
            messages.success(request, f"Role for {user.username} updated to {user_role.get_role_display()}")
            return redirect('manage_user_roles')
            
        elif action == 'bulk_approve':
            role_to_approve = request.POST.get('role_to_approve')
            user_ids = request.POST.getlist('selected_users')
            
            if user_ids:
                roles = UserRole.objects.filter(user_id__in=user_ids, role=role_to_approve, is_approved=False)
                count = roles.count()
                
                # Update approval status
                roles.update(
                    is_approved=True,
                    approved_by=request.user,
                    approval_date=timezone.now()
                )
                
                messages.success(request, f"Approved {count} users with {dict(UserRole.ROLE_CHOICES).get(role_to_approve)} role")
                return redirect('manage_user_roles')
            else:
                messages.error(request, "No users selected for approval")
                
    # Get pending approvals by role
    pending_approvals = {
        role[0]: UserRole.objects.filter(role=role[0], is_approved=False).count()
        for role in role_choices
    }
    
    return render(request, 'users/manage_roles.html', {
        'users': users,
        'role_choices': role_choices,
        'pending_approvals': pending_approvals,
    })

@login_required
def request_role_upgrade(request):
    """
    View for users to request a role upgrade
    """
    # Get current user role
    try:
        user_role = request.user.role
    except:
        # Create role if it doesn't exist
        user_role = UserRole.objects.create(user=request.user, role='buyer')
    
    current_role = user_role.get_role_display()
    is_approved = user_role.is_approved
    
    # Handle role upgrade request
    if request.method == 'POST':
        requested_role = request.POST.get('requested_role')
        reason = request.POST.get('reason', '')
        
        if requested_role in dict(UserRole.ROLE_CHOICES):
            # Update role but set approval to False
            user_role.role = requested_role
            user_role.is_approved = False
            user_role.save()
            
            # Here you could send notification to admins about the request
            # You could also store the reason in a separate model
            
            messages.success(request, f"Your request to upgrade to {dict(UserRole.ROLE_CHOICES).get(requested_role)} has been submitted and is pending approval.")
            return redirect('profile')
        else:
            messages.error(request, "Invalid role selected")
    
    # Filter available roles based on current role
    # (buyer can request host, host can request event_manager, etc.)
    available_roles = []
    if user_role.role == 'buyer':
        available_roles = [('host', 'Event Host')]
    elif user_role.role == 'host':
        available_roles = [('event_manager', 'Event Manager')]
    
    return render(request, 'users/request_role_upgrade.html', {
        'current_role': current_role,
        'is_approved': is_approved,
        'available_roles': available_roles,
    })