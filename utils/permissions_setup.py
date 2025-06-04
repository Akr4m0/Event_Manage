# utils/permissions_setup.py
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from events.models import Event, EventCategory
from tickets.models import Ticket, TicketType
from payments.models import Payment

def setup_permissions():
    """
    Set up groups and permissions for the application.
    Run this after migrations to ensure proper permissions setup.
    """
    # Create groups if they don't exist
    admin_group, _ = Group.objects.get_or_create(name='admin')
    event_manager_group, _ = Group.objects.get_or_create(name='event_manager')
    host_group, _ = Group.objects.get_or_create(name='host')
    buyer_group, _ = Group.objects.get_or_create(name='buyer')
    
    # Get content types for our models
    event_ct = ContentType.objects.get_for_model(Event)
    event_category_ct = ContentType.objects.get_for_model(EventCategory)
    ticket_ct = ContentType.objects.get_for_model(Ticket)
    ticket_type_ct = ContentType.objects.get_for_model(TicketType)
    payment_ct = ContentType.objects.get_for_model(Payment)
    
    # Create custom permissions
    create_event_perm, _ = Permission.objects.get_or_create(
        codename='can_create_event',
        name='Can create events',
        content_type=event_ct,
    )
    
    approve_event_perm, _ = Permission.objects.get_or_create(
        codename='can_approve_event',
        name='Can approve events',
        content_type=event_ct,
    )
    
    manage_categories_perm, _ = Permission.objects.get_or_create(
        codename='can_manage_categories',
        name='Can manage event categories',
        content_type=event_category_ct,
    )
    
    approve_payment_perm, _ = Permission.objects.get_or_create(
        codename='can_approve_payment',
        name='Can approve offline payments',
        content_type=payment_ct,
    )
    
    manage_all_events_perm, _ = Permission.objects.get_or_create(
        codename='can_manage_all_events',
        name='Can manage all events',
        content_type=event_ct,
    )
    
    # Clear existing permissions for groups to avoid duplicates
    admin_group.permissions.clear()
    event_manager_group.permissions.clear()
    host_group.permissions.clear()
    buyer_group.permissions.clear()
    
    # Admin group permissions (all permissions)
    admin_perms = Permission.objects.all()
    admin_group.permissions.add(*admin_perms)
    
    # Event Manager permissions
    event_manager_perms = [
        create_event_perm,
        approve_event_perm,
        manage_categories_perm,
        approve_payment_perm,
        manage_all_events_perm
    ]
    
    # Add standard CRUD permissions for event managers
    for model_ct in [event_ct, event_category_ct, ticket_type_ct]:
        for action in ['add', 'change', 'view', 'delete']:
            perm = Permission.objects.get(
                codename=f"{action}_{model_ct.model}",
                content_type=model_ct
            )
            event_manager_perms.append(perm)
    
    event_manager_group.permissions.add(*event_manager_perms)
    
    # Host permissions (can create and manage own events)
    host_perms = [create_event_perm]
    
    # Add view/change permissions for hosts
    for model_ct in [event_ct, ticket_type_ct]:
        for action in ['add', 'change', 'view']:
            perm = Permission.objects.get(
                codename=f"{action}_{model_ct.model}",
                content_type=model_ct
            )
            host_perms.append(perm)
    
    # View-only permissions
    for model_ct in [event_category_ct, ticket_ct, payment_ct]:
        perm = Permission.objects.get(
            codename=f"view_{model_ct.model}",
            content_type=model_ct
        )
        host_perms.append(perm)
    
    host_group.permissions.add(*host_perms)
    
    # Buyer permissions (view only)
    buyer_perms = []
    
    for model_ct in [event_ct, event_category_ct, ticket_type_ct]:
        perm = Permission.objects.get(
            codename=f"view_{model_ct.model}",
            content_type=model_ct
        )
        buyer_perms.append(perm)
    
    # Buyers can view/change their own tickets
    ticket_view_perm = Permission.objects.get(
        codename="view_ticket",
        content_type=ticket_ct
    )
    buyer_perms.append(ticket_view_perm)
    
    buyer_group.permissions.add(*buyer_perms)
    
    print("Permissions setup completed successfully!")