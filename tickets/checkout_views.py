# tickets/checkout_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.conf import settings
from django.urls import reverse
from django.db import transaction

from events.models import Event
from .models import TicketType, Ticket
from payments.models import Payment
import uuid

# Import the create_checkout_session function if it exists
try:
    from payments.stripe_utils import create_checkout_session
except ImportError:
    # Mock implementation if the real one doesn't exist yet
    def create_checkout_session(payment, success_url, cancel_url):
        # Just redirect to success URL since we can't process a real payment
        return success_url

@login_required
def checkout(request):
    """View for handling the checkout process"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")
    
    # Get event and ticket quantities
    event_id = request.POST.get('event_id')
    event = get_object_or_404(Event, id=event_id, status='published')
    
    # Parse ticket selections from form
    ticket_selections = {}
    for key, value in request.POST.items():
        if key.startswith('ticket_quantities[') and value and int(value) > 0:
            # Extract ticket_type_id from the key format: ticket_quantities[id]
            ticket_type_id = key.split('[')[1].split(']')[0]
            ticket_selections[ticket_type_id] = int(value)
    
    if not ticket_selections:
        messages.error(request, "Please select at least one ticket")
        return redirect('event_detail', event_id=event_id)
    
    # Determine payment method
    payment_method = request.POST.get('payment_method', 'credit_card')
    
    try:
        # Process the ticket purchase
        with transaction.atomic():
            # Calculate total amount
            total_amount = 0
            for ticket_type_id, quantity in ticket_selections.items():
                ticket_type = TicketType.objects.get(id=ticket_type_id)
                
                # Verify availability
                if ticket_type.quantity_available > 0:
                    sold_tickets = ticket_type.tickets.count()
                    remaining = ticket_type.quantity_available - sold_tickets
                    
                    if quantity > remaining:
                        raise ValueError(f"Only {remaining} tickets available for {ticket_type.name}")
                
                total_amount += ticket_type.price * quantity
            
            # Create payment
            payment = Payment.objects.create(
                user=request.user,
                amount=total_amount,
                payment_method=payment_method,
                payment_status='pending'
            )
            
            # Create tickets
            for ticket_type_id, quantity in ticket_selections.items():
                ticket_type = TicketType.objects.get(id=ticket_type_id)
                for _ in range(quantity):
                    ticket = Ticket.objects.create(
                        ticket_type=ticket_type,
                        user=request.user,
                        status='pending',
                        ticket_code=uuid.uuid4()
                    )
                    payment.tickets.add(ticket)
        
        if payment_method == 'offline':
            # For offline payments, redirect to confirmation page
            messages.success(
                request, 
                "Your ticket purchase is being processed. Once your offline payment is approved, your tickets will be confirmed."
            )
            return redirect('payment_confirmation', payment_id=payment.id)
        
        elif payment_method in ['credit_card', 'paypal']:
            # For online payments, create a checkout session
            success_url = request.build_absolute_uri(
                reverse('payment_success', args=[payment.id])
            )
            cancel_url = request.build_absolute_uri(
                reverse('payment_cancel', args=[payment.id])
            )
            
            # Create checkout session
            checkout_url = create_checkout_session(payment, success_url, cancel_url)
            
            # Redirect to payment processor
            return redirect(checkout_url)
        
        else:
            messages.error(request, "Invalid payment method")
            return redirect('event_detail', event_id=event_id)
            
    except Exception as e:
        messages.error(request, str(e))
        return redirect('event_detail', event_id=event_id)

@login_required
def payment_confirmation(request, payment_id):
    """View for displaying payment confirmation"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    return render(request, 'tickets/payment_confirmation.html', {
        'payment': payment,
        'tickets': payment.tickets.all(),
    })

@login_required
def payment_success(request, payment_id):
    """View for handling successful payments"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Update payment status if it's still pending
    if payment.payment_status == 'pending':
        payment.payment_status = 'completed'
        payment.save()
        
        # Update ticket status
        payment.tickets.update(status='confirmed')
        
        # Send email notification
        # (Implementation would go here)
    
    return render(request, 'tickets/payment_success.html', {
        'payment': payment,
        'tickets': payment.tickets.all(),
    })

@login_required
def payment_cancel(request, payment_id):
    """View for handling cancelled payments"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Optionally, you might want to cancel the payment and tickets here
    # payment.payment_status = 'cancelled'
    # payment.save()
    # payment.tickets.update(status='cancelled')
    
    return render(request, 'tickets/payment_cancel.html', {
        'payment': payment,
    })