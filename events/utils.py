# events/utils.py
from django.utils import timezone
from datetime import timedelta
from .models import Event

def get_upcoming_events(days=30, limit=None):
    """
    Get upcoming events within specified number of days
    """
    today = timezone.now()
    upcoming_date = today + timedelta(days=days)
    
    events = Event.objects.filter(
        status='published',
        start_date__gte=today,
        start_date__lte=upcoming_date
    ).order_by('start_date')
    
    if limit:
        events = events[:limit]
    
    return events

def get_trending_events(days=7, min_tickets=5):
    """
    Get trending events based on ticket sales
    """
    from django.db.models import Count
    
    today = timezone.now()
    recent_date = today - timedelta(days=days)
    
    trending_events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).annotate(
        ticket_count=Count('ticket_types__tickets')
    ).filter(
        ticket_count__gte=min_tickets,
        tickets__purchase_date__gte=recent_date
    ).order_by('-ticket_count')
    
    return trending_events

def get_events_by_location(location_query, limit=None):
    """
    Search events by location
    """
    events = Event.objects.filter(
        status='published',
        location__icontains=location_query,
        start_date__gte=timezone.now()
    ).order_by('start_date')
    
    if limit:
        events = events[:limit]
    
    return events