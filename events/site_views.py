# events/site_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from .models import Event, EventCategory
from tickets.models import TicketType, Ticket
from payments.models import Payment

def home(request):
    """
    View for the home page showing featured events
    """
    # Get upcoming published events (next 30 days)
    today = timezone.now()
    upcoming_date = today + timezone.timedelta(days=30)
    
    featured_events = Event.objects.filter(
        status='published',
        start_date__gte=today,
        start_date__lte=upcoming_date
    ).order_by('start_date')[:6]
    
    # Get categories for filtering
    categories = EventCategory.objects.all()
    
    return render(request, 'home.html', {
        'featured_events': featured_events,
        'categories': categories,
    })

def event_list(request):
    """
    View for listing all events with filters
    """
    # Base queryset
    events = Event.objects.filter(status='published').order_by('start_date')
    
    # Apply filters if provided
    category_id = request.GET.get('category')
    search_query = request.GET.get('q')
    date_filter = request.GET.get('date')
    
    if category_id:
        events = events.filter(category_id=category_id)
    
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    if date_filter:
        today = timezone.now()
        if date_filter == 'today':
            events = events.filter(
                start_date__date=today.date()
            )
        elif date_filter == 'tomorrow':
            tomorrow = today + timezone.timedelta(days=1)
            events = events.filter(
                start_date__date=tomorrow.date()
            )
        elif date_filter == 'this-week':
            end_of_week = today + timezone.timedelta(days=7)
            events = events.filter(
                start_date__gte=today,
                start_date__lte=end_of_week
            )
        elif date_filter == 'this-month':
            end_of_month = today + timezone.timedelta(days=30)
            events = events.filter(
                start_date__gte=today,
                start_date__lte=end_of_month
            )
    
    # Pagination
    paginator = Paginator(events, 9)  # 9 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filtering
    categories = EventCategory.objects.all()
    
    return render(request, 'events/event_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'category_id': category_id,
        'search_query': search_query,
        'date_filter': date_filter,
    })

def event_detail(request, event_id):
    """
    View for showing event details and available tickets
    """
    event = get_object_or_404(Event, id=event_id, status='published')
    ticket_types = TicketType.objects.filter(event=event)
    
    # Check if the user is the organizer
    is_organizer = request.user.is_authenticated and request.user == event.organizer
    
    # For attendees, check if they have tickets to this event
    has_tickets = False
    user_tickets = []
    
    if request.user.is_authenticated:
        user_tickets = Ticket.objects.filter(
            user=request.user,
            ticket_type__event=event
        ).select_related('ticket_type')
        
        has_tickets = user_tickets.exists()
    
    return render(request, 'events/event_detail.html', {
        'event': event,
        'ticket_types': ticket_types,
        'is_organizer': is_organizer,
        'has_tickets': has_tickets,
        'user_tickets': user_tickets,
    })

@login_required
def my_events(request):
    """
    View for showing events organized by the current user
    """
    organized_events = Event.objects.filter(organizer=request.user).order_by('-created_at')
    
    # Get tickets purchased by the user
    tickets = Ticket.objects.filter(user=request.user).select_related('ticket_type__event')
    
    # Group tickets by event
    attended_events = {}
    for ticket in tickets:
        event = ticket.ticket_type.event
        if event.id not in attended_events:
            attended_events[event.id] = {
                'event': event,
                'tickets': []
            }
        attended_events[event.id]['tickets'].append(ticket)
    
    return render(request, 'events/my_events.html', {
        'organized_events': organized_events,
        'attended_events': attended_events.values(),
    })

@login_required
def create_event(request):
    """
    View for creating a new event
    """
    if request.method == 'POST':
        # Form processing would go here
        # For now, we'll just redirect to my_events
        return redirect('my_events')
    
    categories = EventCategory.objects.all()
    
    return render(request, 'events/create_event.html', {
        'categories': categories,
    })

@login_required
def edit_event(request, event_id):
    """
    View for editing an existing event
    """
    event = get_object_or_404(Event, id=event_id, organizer=request.user)
    
    if request.method == 'POST':
        # Form processing would go here
        # For now, we'll just redirect to event_detail
        return redirect('event_detail', event_id=event.id)
    
    categories = EventCategory.objects.all()
    
    return render(request, 'events/edit_event.html', {
        'event': event,
        'categories': categories,
    })