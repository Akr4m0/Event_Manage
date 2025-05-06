# tickets/ticket_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from .models import Ticket, TicketType
from .utils import generate_ticket_pdf, generate_qr_code
from events.models import Event
import uuid
from io import BytesIO
import base64


@login_required
def my_tickets(request):
    """View for displaying all tickets owned by the current user"""
    tickets = Ticket.objects.filter(user=request.user).select_related(
        'ticket_type', 'ticket_type__event'
    ).order_by('-purchase_date')
    
    # Group tickets by event
    tickets_by_event = {}
    for ticket in tickets:
        event = ticket.ticket_type.event
        if event.id not in tickets_by_event:
            tickets_by_event[event.id] = {
                'event': event,
                'tickets': []
            }
        tickets_by_event[event.id]['tickets'].append(ticket)
    
    return render(request, 'tickets/my_tickets.html', {
        'tickets_by_event': tickets_by_event.values(),
    })


@login_required
def ticket_detail(request, ticket_id):
    """View for displaying the details of a specific ticket"""
    try:
        ticket = get_object_or_404(Ticket, ticket_code=ticket_id)
        
        # Check permission: only ticket owner or staff can view
        if ticket.user != request.user and not request.user.is_staff:
            messages.error(request, "You don't have permission to view this ticket.")
            return redirect('my_tickets')
        
        # Generate QR code for the ticket
        qr_image = generate_qr_code(str(ticket.ticket_code))
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer)
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')
        
        return render(request, 'tickets/ticket_detail.html', {
            'ticket': ticket,
            'qr_code': qr_base64,
        })
    except Exception as e:
        messages.error(request, f"Error retrieving ticket: {str(e)}")
        return redirect('my_tickets')


@login_required
def download_ticket(request, ticket_id):
    """View for downloading a ticket as PDF"""
    try:
        ticket = get_object_or_404(Ticket, ticket_code=ticket_id)
        
        # Check permission: only ticket owner or staff can download
        if ticket.user != request.user and not request.user.is_staff:
            messages.error(request, "You don't have permission to download this ticket.")
            return redirect('my_tickets')
        
        # Generate PDF
        pdf_file = generate_ticket_pdf(ticket)
        
        # Determine content type based on whether we got a PDF or text
        content_type = 'application/pdf'
        if pdf_file.getvalue().startswith(b'PDF generation is not available'):
            content_type = 'text/plain'
        
        # Create response
        response = HttpResponse(pdf_file, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_code}.pdf"'
        
        return response
    except Exception as e:
        messages.error(request, f"Failed to generate ticket: {str(e)}")
        return redirect('ticket_detail', ticket_id=ticket_id)


@login_required
def transfer_ticket(request, ticket_id):
    """View for transferring a ticket to another user"""
    try:
        ticket = get_object_or_404(Ticket, ticket_code=ticket_id)
        
        # Check permission: only ticket owner can transfer
        if ticket.user != request.user:
            messages.error(request, "You don't have permission to transfer this ticket.")
            return redirect('my_tickets')
        
        # Check if ticket can be transferred (status should be confirmed, not used)
        if ticket.status != 'confirmed' or ticket.checked_in:
            messages.error(request, "This ticket cannot be transferred.")
            return redirect('ticket_detail', ticket_id=ticket_id)
        
        if request.method == 'POST':
            recipient_username = request.POST.get('recipient_username')
            
            if not recipient_username:
                messages.error(request, "Please enter a username.")
                return render(request, 'tickets/transfer_ticket.html', {'ticket': ticket})
            
            try:
                recipient = User.objects.get(username=recipient_username)
                
                # Prevent transferring to self
                if recipient == request.user:
                    messages.error(request, "You cannot transfer a ticket to yourself.")
                    return render(request, 'tickets/transfer_ticket.html', {'ticket': ticket})
                
                # Update ticket owner
                ticket.user = recipient
                ticket.save()
                
                messages.success(request, f"Ticket successfully transferred to {recipient_username}.")
                return redirect('my_tickets')
                
            except User.DoesNotExist:
                messages.error(request, f"User {recipient_username} does not exist.")
        
        return render(request, 'tickets/transfer_ticket.html', {
            'ticket': ticket,
        })
    except Exception as e:
        messages.error(request, f"Error transferring ticket: {str(e)}")
        return redirect('my_tickets')


@login_required
def check_in_ticket(request, ticket_id):
    """Admin view for checking in a ticket"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to check in tickets.")
        return redirect('home')
    
    try:
        ticket = get_object_or_404(Ticket, ticket_code=ticket_id)
        
        # Check if ticket is already checked in
        if ticket.checked_in:
            messages.warning(request, "This ticket has already been checked in.")
            return redirect(request.META.get('HTTP_REFERER', 'scan_ticket'))
        
        # Check if ticket status allows check-in
        if ticket.status != 'confirmed':
            messages.error(request, f"Cannot check in ticket with status: {ticket.get_status_display()}")
            return redirect(request.META.get('HTTP_REFERER', 'scan_ticket'))
        
        # Perform check-in
        ticket.checked_in = True
        ticket.checked_in_time = timezone.now()
        ticket.status = 'used'
        ticket.save()
        
        messages.success(request, "Ticket successfully checked in.")
        
        # Redirect back to referring page or to admin page
        if 'scan_ticket' in request.META.get('HTTP_REFERER', ''):
            return redirect('scan_ticket')
        return redirect('admin:tickets_ticket_change', ticket.id)
    
    except Exception as e:
        messages.error(request, f"Error checking in ticket: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def scan_ticket(request):
    """View for scanning and validating tickets (staff only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to check in tickets.")
        return redirect('home')
    
    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code')
        
        if not ticket_code:
            return JsonResponse({
                'status': 'error',
                'message': 'No ticket code provided.'
            })
        
        try:
            ticket = Ticket.objects.get(ticket_code=ticket_code)
            
            # Check if already checked in
            if ticket.checked_in:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This ticket has already been checked in.',
                    'ticket': {
                        'event': ticket.ticket_type.event.title,
                        'type': ticket.ticket_type.name,
                        'user': ticket.user.username,
                        'checked_in_time': ticket.checked_in_time.strftime('%Y-%m-%d %H:%M')
                    }
                })
            
            # Check ticket status
            if ticket.status != 'confirmed':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Cannot check in ticket with status: {ticket.get_status_display()}',
                    'ticket': {
                        'event': ticket.ticket_type.event.title,
                        'type': ticket.ticket_type.name,
                        'user': ticket.user.username,
                        'status': ticket.get_status_display()
                    }
                })
            
            # Check in the ticket
            ticket.checked_in = True
            ticket.checked_in_time = timezone.now()
            ticket.status = 'used'
            ticket.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ticket successfully checked in!',
                'ticket': {
                    'event': ticket.ticket_type.event.title,
                    'type': ticket.ticket_type.name,
                    'user': ticket.user.username,
                    'checked_in_time': ticket.checked_in_time.strftime('%Y-%m-%d %H:%M')
                }
            })
            
        except Ticket.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid ticket code. No ticket found.'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error processing ticket: {str(e)}'
            })
    
    # Get recent scan history for display
    recent_scans = Ticket.objects.filter(
        checked_in=True
    ).order_by('-checked_in_time')[:10]
    
    return render(request, 'tickets/scan_ticket.html', {
        'recent_scans': recent_scans
    })


@login_required
def ticket_stats(request, event_id):
    """View for displaying ticket statistics for an event (staff only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view ticket statistics.")
        return redirect('home')
    
    event = get_object_or_404(Event, id=event_id)
    
    # Get ticket types for this event
    ticket_types = TicketType.objects.filter(event=event)
    
    # Calculate stats for each ticket type
    ticket_stats = []
    for ticket_type in ticket_types:
        total_tickets = ticket_type.tickets.count()
        checked_in_tickets = ticket_type.tickets.filter(checked_in=True).count()
        available = ticket_type.quantity_available - total_tickets if ticket_type.quantity_available > 0 else "Unlimited"
        
        ticket_stats.append({
            'type': ticket_type,
            'total': total_tickets,
            'checked_in': checked_in_tickets,
            'checked_in_percent': (checked_in_tickets / total_tickets * 100) if total_tickets > 0 else 0,
            'available': available
        })
    
    # Calculate overall stats
    total_tickets = sum(stat['total'] for stat in ticket_stats)
    total_checked_in = sum(stat['checked_in'] for stat in ticket_stats)
    overall_checked_in_percent = (total_checked_in / total_tickets * 100) if total_tickets > 0 else 0
    
    return render(request, 'tickets/ticket_stats.html', {
        'event': event,
        'ticket_stats': ticket_stats,
        'total_tickets': total_tickets,
        'total_checked_in': total_checked_in,
        'overall_checked_in_percent': overall_checked_in_percent
    })