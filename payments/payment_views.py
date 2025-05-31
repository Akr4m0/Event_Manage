# payments/payment_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from .models import Payment
from tickets.models import Ticket, TicketType
from events.models import Event
import uuid
import json

@login_required
def create_payment(request):
    """Handle payment creation when user clicks checkout"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")
    
    event_id = request.POST.get('event_id')
    event = get_object_or_404(Event, id=event_id, status='published')
    
    # Parse ticket quantities from the form
    ticket_selections = {}
    for key, value in request.POST.items():
        if key.startswith('ticket_quantities[') and value and int(value) > 0:
            ticket_type_id = key.split('[')[1].split(']')[0]
            ticket_selections[ticket_type_id] = int(value)
    
    if not ticket_selections:
        messages.error(request, "Please select at least one ticket.")
        return redirect('event_detail', event_id=event_id)
    
    try:
        with transaction.atomic():
            # Calculate total amount and validate availability
            total_amount = 0
            tickets_to_create = []
            
            for ticket_type_id, quantity in ticket_selections.items():
                ticket_type = get_object_or_404(TicketType, id=ticket_type_id)
                
                # Validate availability
                if ticket_type.quantity_available > 0:
                    sold_tickets = ticket_type.tickets.count()
                    remaining = ticket_type.quantity_available - sold_tickets
                    
                    if quantity > remaining:
                        messages.error(request, f"Only {remaining} tickets available for {ticket_type.name}.")
                        return redirect('event_detail', event_id=event_id)
                
                total_amount += ticket_type.price * quantity
                tickets_to_create.append((ticket_type, quantity))
            
            # Create payment
            payment = Payment.objects.create(
                user=request.user,
                amount=total_amount,
                payment_method='pending',  # Will be selected in checkout
                payment_status='pending'
            )
            
            # Create tickets and link to payment
            for ticket_type, quantity in tickets_to_create:
                for _ in range(quantity):
                    ticket = Ticket.objects.create(
                        ticket_type=ticket_type,
                        user=request.user,
                        status='pending',
                        ticket_code=uuid.uuid4()
                    )
                    payment.tickets.add(ticket)
            
            # Redirect to payment selection page
            return redirect('select_payment_method', payment_id=payment.id)
            
    except Exception as e:
        messages.error(request, f"Error creating payment: {str(e)}")
        return redirect('event_detail', event_id=event_id)

@login_required
def select_payment_method(request, payment_id):
    """Allow user to select payment method"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        payment.payment_method = payment_method
        payment.save()
        
        if payment_method == 'offline':
            return redirect('process_offline_payment', payment_id=payment.id)
        elif payment_method in ['credit_card', 'paypal']:
            return redirect('process_online_payment', payment_id=payment.id)
        else:
            messages.error(request, "Invalid payment method selected.")
            return redirect('select_payment_method', payment_id=payment.id)
    
    # Calculate order summary
    tickets_by_type = {}
    for ticket in payment.tickets.all():
        ticket_type = ticket.ticket_type
        if ticket_type.id not in tickets_by_type:
            tickets_by_type[ticket_type.id] = {
                'ticket_type': ticket_type,
                'quantity': 0,
                'subtotal': 0
            }
        tickets_by_type[ticket_type.id]['quantity'] += 1
        tickets_by_type[ticket_type.id]['subtotal'] += ticket_type.price
    
    return render(request, 'payments/select_payment_method.html', {
        'payment': payment,
        'tickets_summary': tickets_by_type.values(),
        'total_amount': payment.amount
    })

@login_required
def process_offline_payment(request, payment_id):
    """Process offline payment (bank transfer, cash)"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    if payment.payment_status != 'pending':
        messages.error(request, "This payment has already been processed.")
        return redirect('payment_status', payment_id=payment.id)
    
    # Update payment status to processing
    payment.payment_status = 'processing'
    payment.save()
    
    # Send notification to admin about offline payment
    # In real app, you would send an email notification here
    
    messages.success(request, 
        "Your offline payment has been recorded. "
        "Please follow the instructions to complete the payment. "
        "Your tickets will be confirmed once payment is received."
    )
    
    return render(request, 'payments/offline_payment_instructions.html', {
        'payment': payment,
        'bank_details': {
            'account_name': 'Event Management Platform',
            'account_number': '1234567890',
            'bank_name': 'Example Bank',
            'reference': f'PAY-{payment.transaction_id}'
        }
    })

# Update this function in payments/payment_views.py

@login_required
def process_online_payment(request, payment_id):
    """Process online payment (Stripe/PayPal integration)"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    if payment.payment_status != 'pending':
        messages.error(request, "This payment has already been processed.")
        return redirect('payment_status', payment_id=payment.id)
    
    # Create Stripe checkout session
    from .stripe_utils import create_checkout_session
    
    success_url = request.build_absolute_uri(
        reverse('payment_success', args=[payment.id])
    )
    cancel_url = request.build_absolute_uri(
        reverse('payment_cancel', args=[payment.id])
    )
    
    checkout_url = create_checkout_session(payment, success_url, cancel_url)
    
    if checkout_url:
        # Redirect to Stripe Checkout
        return redirect(checkout_url)
    else:
        # If Stripe session creation failed
        messages.error(request, "Failed to initialize payment. Please try again.")
        return redirect('select_payment_method', payment_id=payment.id)
    
@login_required
def payment_success(request, payment_id):
    """Handle successful payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Update payment status
    if payment.payment_status == 'pending':
        payment.payment_status = 'completed'
        payment.save()
        
        # Update all tickets to confirmed
        payment.tickets.update(status='confirmed')
        
        messages.success(request, "Payment successful! Your tickets have been confirmed.")
    
    return render(request, 'payments/payment_success.html', {
        'payment': payment,
        'tickets': payment.tickets.all()
    })

@login_required
def payment_cancel(request, payment_id):
    """Handle cancelled payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    if payment.payment_status == 'pending':
        payment.payment_status = 'cancelled'
        payment.save()
        
        # Update all tickets to cancelled
        payment.tickets.update(status='cancelled')
        
        messages.warning(request, "Payment was cancelled. Your tickets have been cancelled.")
    
    return render(request, 'payments/payment_cancel.html', {
        'payment': payment
    })

@login_required
def payment_status(request, payment_id):
    """View payment status and details"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    return render(request, 'payments/payment_status.html', {
        'payment': payment,
        'tickets': payment.tickets.all()
    })

# Admin views for approving offline payments
@login_required
def admin_approve_payment(request, payment_id):
    """Admin view to approve offline payments"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            payment.payment_status = 'completed'
            payment.is_offline_approved = True
            payment.approved_by = request.user
            payment.approval_date = timezone.now()
            payment.save()
            
            # Update tickets to confirmed
            payment.tickets.update(status='confirmed')
            
            messages.success(request, f"Payment {payment.transaction_id} has been approved.")
        elif action == 'reject':
            payment.payment_status = 'failed'
            payment.save()
            
            # Update tickets to cancelled
            payment.tickets.update(status='cancelled')
            
            messages.warning(request, f"Payment {payment.transaction_id} has been rejected.")
    
    return redirect('admin_payment_list')

@login_required
def admin_payment_list(request):
    """Admin view to list all payments"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Filter for offline payments pending approval
    pending_payments = Payment.objects.filter(
        payment_method='offline',
        payment_status='processing'
    )
    
    all_payments = Payment.objects.all().order_by('-payment_date')
    
    return render(request, 'payments/admin_payment_list.html', {
        'pending_payments': pending_payments,
        'all_payments': all_payments
    })

# API endpoints for AJAX/async operations
@login_required
def validate_stripe_payment(request):
    """AJAX endpoint to validate Stripe payment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            payment_id = data.get('payment_id')
            
            payment = get_object_or_404(Payment, id=payment_id, user=request.user)
            
            # Here you would verify with Stripe API
            # For now, we'll simulate success
            payment.payment_status = 'completed'
            payment.save()
            payment.tickets.update(status='confirmed')
            
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('payment_success', args=[payment.id])
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)