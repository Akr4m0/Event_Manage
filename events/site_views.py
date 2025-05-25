# events/site_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from datetime import timedelta

from .models import Event, EventCategory
from .forms import EventForm
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
    
    # Get trending events (most tickets sold in last 7 days)
    trending_events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).annotate(
        ticket_count=Count('ticket_types__tickets')
    ).order_by('-ticket_count')[:3]
    
    # Get categories for filtering
    categories = EventCategory.objects.all()
    
    return render(request, 'home.html', {
        'featured_events': featured_events,
        'trending_events': trending_events,
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
    location_filter = request.GET.get('location')
    
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
        elif date_filter == 'weekend':
            # Find upcoming Saturday and Sunday
            days_until_saturday = (5 - today.weekday()) % 7
            saturday = today + timezone.timedelta(days=days_until_saturday)
            sunday = saturday + timezone.timedelta(days=1)
            events = events.filter(
                Q(start_date__date=saturday.date()) |
                Q(start_date__date=sunday.date())
            )
    
    if location_filter:
        events = events.filter(location__icontains=location_filter)
    
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
        'location_filter': location_filter,
    })

def event_detail(request, event_id):
    """
    View for showing event details and available tickets
    """
    event = get_object_or_404(Event, id=event_id)
    
    # If event is a draft, only allow organizer to view it
    if event.status == 'draft' and (not request.user.is_authenticated or request.user != event.organizer):
        messages.error(request, "This event is not yet published.")
        return redirect('event_list')
    
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
    
    # Calculate the percentage of capacity filled
    if event.max_attendees > 0:
        attendee_count = Ticket.objects.filter(
            ticket_type__event=event, 
            status__in=['confirmed', 'used']
        ).count()
        capacity_percentage = min(int((attendee_count / event.max_attendees) * 100), 100)
    else:
        capacity_percentage = 0
    
    # Get similar events
    similar_events = Event.objects.filter(
        status='published',
        category=event.category,
        start_date__gte=timezone.now()
    ).exclude(id=event.id).order_by('start_date')[:3]
    
    return render(request, 'events/event_detail.html', {
        'event': event,
        'ticket_types': ticket_types,
        'is_organizer': is_organizer,
        'has_tickets': has_tickets,
        'user_tickets': user_tickets,
        'capacity_percentage': capacity_percentage,
        'similar_events': similar_events,
    })

@login_required
def my_events(request):
    """
    View for showing events organized by the current user
    """
    # Get filter parameter
    filter_status = request.GET.get('status', 'all')
    
    # Base queryset
    organized_events = Event.objects.filter(organizer=request.user)
    
    # Apply status filter if provided
    if filter_status and filter_status != 'all':
        organized_events = organized_events.filter(status=filter_status)
    
    # Order by created date
    organized_events = organized_events.order_by('-created_at')
    
    # Get tickets purchased by the user
    tickets = Ticket.objects.filter(user=request.user).select_related(
        'ticket_type__event'
    ).order_by('ticket_type__event__start_date')
    
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
        'filter_status': filter_status,
    })

@login_required
def create_event(request):
    """
    View for creating a new event
    """
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the event with current user as organizer
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            
            # Process ticket types
            ticket_names = request.POST.getlist('ticket_name[]')
            ticket_prices = request.POST.getlist('ticket_price[]')
            ticket_quantities = request.POST.getlist('ticket_quantity[]')
            ticket_descriptions = request.POST.getlist('ticket_description[]')
            
            # Validate at least one ticket type
            if not ticket_names or not any(name.strip() for name in ticket_names):
                messages.error(request, "Please add at least one ticket type.")
                event.delete()  # Delete the event if no ticket types
                return render(request, 'events/create_event.html', {
                    'form': form,
                    'categories': EventCategory.objects.all(),
                })
            
            # Create ticket types
            ticket_types_created = False
            for i in range(len(ticket_names)):
                if ticket_names[i].strip():  # Only create if name provided
                    try:
                        price = float(ticket_prices[i])
                        quantity = int(ticket_quantities[i])
                        description = ticket_descriptions[i] if i < len(ticket_descriptions) else ''
                        
                        # Add validation for price and quantity
                        if price < 0:
                            messages.error(request, f"Price for '{ticket_names[i]}' must be non-negative.")
                            continue
                            
                        if quantity < 0:
                            messages.error(request, f"Quantity for '{ticket_names[i]}' must be non-negative.")
                            continue
                        
                        TicketType.objects.create(
                            event=event,
                            name=ticket_names[i],
                            price=price,
                            quantity_available=quantity,
                            description=description
                        )
                        ticket_types_created = True
                    except (ValueError, IndexError) as e:
                        # Handle invalid input
                        messages.error(request, f"Invalid data for '{ticket_names[i]}' ticket type: {str(e)}")
                        continue
            
            # If no valid ticket types were created, delete the event and redirect back
            if not ticket_types_created:
                event.delete()
                messages.error(request, "No valid ticket types were created. Please fix the errors and try again.")
                return render(request, 'events/create_event.html', {
                    'form': form,
                    'categories': EventCategory.objects.all(),
                })
            
            messages.success(request, "Event created successfully!")
            
            # Redirect based on status
            if event.status == 'published':
                return redirect('event_detail', event_id=event.id)
            else:
                return redirect('my_events')
        else:
            # Form validation failed
            messages.error(request, "Please correct the errors below.")
    else:
        # GET request: create new form
        form = EventForm()
    
    categories = EventCategory.objects.all()
    
    return render(request, 'events/create_event.html', {
        'form': form,
        'categories': categories,
    })

@login_required
def edit_event(request, event_id):
    """
    View for editing an existing event
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            
            # Handle existing ticket types update
            ticket_types = TicketType.objects.filter(event=event)
            
            # Process updated ticket types
            for ticket_type in ticket_types:
                ticket_id = f"ticket_id_{ticket_type.id}"
                if ticket_id in request.POST:
                    # Update existing ticket type
                    ticket_name = request.POST.get(f"ticket_name_{ticket_type.id}")
                    ticket_price = request.POST.get(f"ticket_price_{ticket_type.id}")
                    ticket_quantity = request.POST.get(f"ticket_quantity_{ticket_type.id}")
                    ticket_description = request.POST.get(f"ticket_description_{ticket_type.id}")
                    
                    # Handle deletion
                    delete_ticket = request.POST.get(f"delete_ticket_{ticket_type.id}")
                    if delete_ticket == "1":
                        # Check if tickets have been sold
                        if not Ticket.objects.filter(ticket_type=ticket_type).exists():
                            ticket_type.delete()
                        else:
                            messages.error(request, f"Cannot delete '{ticket_type.name}' - tickets have already been sold.")
                    else:
                        # Update ticket type
                        try:
                            ticket_type.name = ticket_name
                            ticket_type.price = float(ticket_price)
                            ticket_type.quantity_available = int(ticket_quantity)
                            ticket_type.description = ticket_description
                            ticket_type.save()
                        except ValueError:
                            messages.error(request, f"Invalid data for '{ticket_name}' ticket type.")
            
            # Process new ticket types
            new_ticket_names = request.POST.getlist('new_ticket_name[]')
            new_ticket_prices = request.POST.getlist('new_ticket_price[]')
            new_ticket_quantities = request.POST.getlist('new_ticket_quantity[]')
            new_ticket_descriptions = request.POST.getlist('new_ticket_description[]')
            
            # Create new ticket types
            for i in range(len(new_ticket_names)):
                if new_ticket_names[i]:  # Only create if name provided
                    try:
                        price = float(new_ticket_prices[i])
                        quantity = int(new_ticket_quantities[i])
                        description = new_ticket_descriptions[i] if i < len(new_ticket_descriptions) else ''
                        
                        TicketType.objects.create(
                            event=event,
                            name=new_ticket_names[i],
                            price=price,
                            quantity_available=quantity,
                            description=description
                        )
                    except (ValueError, IndexError):
                        # Handle invalid input
                        continue
            
            messages.success(request, "Event updated successfully!")
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
    
    categories = EventCategory.objects.all()
    ticket_types = TicketType.objects.filter(event=event)
    
    # Check if tickets sold for each ticket type - collect IDs for direct comparison
    tickets_sold_ids = []
    tickets_sold_count = 0
    
    for ticket_type in ticket_types:
        sales_count = Ticket.objects.filter(ticket_type=ticket_type).count()
        if sales_count > 0:
            tickets_sold_ids.append(ticket_type.id)
            tickets_sold_count += sales_count
    
    return render(request, 'events/edit_event.html', {
        'form': form,
        'event': event,
        'categories': categories,
        'ticket_types': ticket_types,
        'tickets_sold_ids': tickets_sold_ids,
        'tickets_sold_count': tickets_sold_count,
    })

@login_required
def cancel_event(request, event_id):
    """
    View for cancelling an event
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, "You don't have permission to cancel this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        # Update event status to cancelled
        event.status = 'cancelled'
        event.save()
        
        # Get all tickets for this event
        tickets = Ticket.objects.filter(
            ticket_type__event=event,
            status__in=['pending', 'confirmed']
        )
        
        # Update ticket status to cancelled
        tickets.update(status='cancelled')
        
        # Notify users - in a real system, you would send emails here
        
        messages.success(request, f"'{event.title}' has been cancelled.")
        return redirect('my_events')
    
    return redirect('event_detail', event_id=event.id)

@login_required
def event_dashboard(request, event_id):
    """
    Dashboard view for event organizers
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, "You don't have permission to access this dashboard.")
        return redirect('event_detail', event_id=event.id)
    
    # Get ticket sales data
    ticket_types = TicketType.objects.filter(event=event)
    
    # Statistics
    total_tickets = Ticket.objects.filter(ticket_type__event=event).count()
    confirmed_tickets = Ticket.objects.filter(ticket_type__event=event, status='confirmed').count()
    pending_tickets = Ticket.objects.filter(ticket_type__event=event, status='pending').count()
    cancelled_tickets = Ticket.objects.filter(ticket_type__event=event, status='cancelled').count()
    used_tickets = Ticket.objects.filter(ticket_type__event=event, status='used').count()
    
    # Create data for pie chart
    ticket_status_data = {
        'labels': ['Confirmed', 'Pending', 'Cancelled', 'Used'],
        'data': [confirmed_tickets, pending_tickets, cancelled_tickets, used_tickets],
        'colors': ['#2ecc71', '#f39c12', '#e74c3c', '#3498db']
    }
    
    # Ticket sales by type
    ticket_sales_by_type = []
    for ticket_type in ticket_types:
        sold = Ticket.objects.filter(ticket_type=ticket_type).count()
        available = ticket_type.quantity_available - sold if ticket_type.quantity_available > 0 else 'Unlimited'
        
        ticket_sales_by_type.append({
            'name': ticket_type.name,
            'price': ticket_type.price,
            'sold': sold,
            'available': available,
            'revenue': sold * ticket_type.price
        })
    
    # Get recent attendees
    recent_attendees = Ticket.objects.filter(
        ticket_type__event=event
    ).select_related('user').order_by('-purchase_date')[:10]
    
    return render(request, 'events/event_dashboard.html', {
        'event': event,
        'ticket_types': ticket_types,
        'total_tickets': total_tickets,
        'confirmed_tickets': confirmed_tickets,
        'pending_tickets': pending_tickets,
        'cancelled_tickets': cancelled_tickets,
        'used_tickets': used_tickets,
        'ticket_status_data': ticket_status_data,
        'ticket_sales_by_type': ticket_sales_by_type,
        'recent_attendees': recent_attendees,
    })

@login_required
def check_in_attendee(request, event_id):
    """
    View for checking in attendees at event
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer
    if request.user != event.organizer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to check in attendees.")
    
    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code')
        
        try:
            # Look up ticket by code
            ticket = Ticket.objects.get(
                ticket_code=ticket_code,
                ticket_type__event=event
            )
            
            # Check if ticket is valid for check-in
            if ticket.status == 'confirmed':
                ticket.status = 'used'
                ticket.checked_in = True
                ticket.checked_in_time = timezone.now()
                ticket.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f"Successfully checked in: {ticket.user.username}",
                    'attendee_name': f"{ticket.user.first_name} {ticket.user.last_name}".strip() or ticket.user.username,
                    'ticket_type': ticket.ticket_type.name
                })
            elif ticket.status == 'used':
                return JsonResponse({
                    'success': False,
                    'message': "Ticket has already been used.",
                    'attendee_name': f"{ticket.user.first_name} {ticket.user.last_name}".strip() or ticket.user.username,
                    'ticket_type': ticket.ticket_type.name,
                    'checked_in_time': ticket.checked_in_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f"Invalid ticket status: {ticket.get_status_display()}"
                })
        except Ticket.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': "Invalid ticket code or ticket not for this event."
            })
    
    return render(request, 'events/check_in.html', {
        'event': event,
    })

def event_category_list(request):
    """
    View for listing all event categories
    """
    categories = EventCategory.objects.all().order_by('name')
    
    # For each category, get the number of active events
    for category in categories:
        category.active_event_count = Event.objects.filter(
            category=category,
            status='published',
            start_date__gte=timezone.now()
        ).count()
    
    return render(request, 'events/category_list.html', {
        'categories': categories,
    })

def event_category_detail(request, category_id):
    """
    View for showing events in a specific category
    """
    category = get_object_or_404(EventCategory, id=category_id)
    
    # Get published events in this category
    events = Event.objects.filter(
        category=category,
        status='published',
        start_date__gte=timezone.now()
    ).order_by('start_date')
    
    # Pagination
    paginator = Paginator(events, 9)  # 9 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'events/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
    })

def events_by_date(request, year, month, day=None):
    """
    View for showing events on a specific date
    """
    # Build base queryset for events on this date
    events = Event.objects.filter(status='published')
    
    if day:  # Specific day
        date_str = f"{year}-{month:02d}-{day:02d}"
        events = events.filter(start_date__date=date_str)
        date_display = timezone.datetime(year, month, day).strftime("%B %d, %Y")
    else:  # Full month
        events = events.filter(start_date__year=year, start_date__month=month)
        date_display = timezone.datetime(year, month, 1).strftime("%B %Y")
    
    # Order by start time
    events = events.order_by('start_date')
    
    # Pagination
    paginator = Paginator(events, 9)  # 9 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'events/events_by_date.html', {
        'page_obj': page_obj,
        'date_display': date_display,
        'year': year,
        'month': month,
        'day': day,
    })

def events_calendar(request):
    """
    View for calendar of events
    """
    # Get the selected month/year from query parameters or use current date
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Get first and last day of the month
    first_day = timezone.datetime(year, month, 1)
    if month == 12:
        last_day = timezone.datetime(year + 1, 1, 1) - timezone.timedelta(days=1)
    else:
        last_day = timezone.datetime(year, month + 1, 1) - timezone.timedelta(days=1)
    
    # Get all events in this month
    events = Event.objects.filter(
        status='published',
        start_date__date__gte=first_day,
        start_date__date__lte=last_day
    ).order_by('start_date')
    
    # Create calendar data
    # (You would need to implement the calendar logic here)
    
    return render(request, 'events/calendar.html', {
        'events': events,
        'year': year,
        'month': month,
        'month_name': first_day.strftime("%B"),
    })

@login_required
def download_ticket(request, ticket_id):
    """
    View for downloading a ticket
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Check if user owns this ticket
    if request.user != ticket.user and request.user != ticket.ticket_type.event.organizer and not request.user.is_staff:
        messages.error(request, "You don't have permission to access this ticket.")
        return redirect('my_events')
    
    # In a real implementation, you would generate a PDF ticket here
    # For now, just redirect to event detail
    messages.info(request, "Ticket download functionality not implemented yet.")
    return redirect('event_detail', event_id=ticket.ticket_type.event.id)