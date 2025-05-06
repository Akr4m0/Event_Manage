# tickets/purchase.py
from django.db import transaction
from django.contrib.auth.models import User
from .models import Ticket, TicketType
from payments.models import Payment
import uuid

def process_ticket_purchase(user, ticket_selections, payment_method):
    """
    Process a bulk ticket purchase
    
    Args:
        user: The user purchasing tickets
        ticket_selections: Dictionary of ticket_type_id -> quantity
        payment_method: The payment method used
    
    Returns:
        tuple: (payment_obj, created_tickets)
    """
    if not ticket_selections:
        raise ValueError("No tickets selected for purchase")
    
    # Validate user
    if not isinstance(user, User):
        raise ValueError("Invalid user")
    
    # Calculate total amount and validate ticket availability
    total_amount = 0
    ticket_types = {}
    
    for ticket_type_id, quantity in ticket_selections.items():
        try:
            ticket_type = TicketType.objects.get(id=ticket_type_id)
            quantity = int(quantity)
            
            if quantity <= 0:
                continue
                
            # Check availability
            if ticket_type.quantity_available > 0:
                sold_tickets = ticket_type.tickets.count()
                remaining = ticket_type.quantity_available - sold_tickets
                
                if quantity > remaining:
                    raise ValueError(f"Only {remaining} tickets available for {ticket_type.name}")
            
            # Add to total
            total_amount += ticket_type.price * quantity
            ticket_types[ticket_type] = quantity
            
        except TicketType.DoesNotExist:
            raise ValueError(f"Invalid ticket type: {ticket_type_id}")
    
    if not ticket_types:
        raise ValueError("No valid tickets selected")
    
    # Start transaction to ensure all operations succeed or fail together
    with transaction.atomic():
        # Create payment
        payment = Payment.objects.create(
            user=user,
            amount=total_amount,
            payment_method=payment_method,
            payment_status='pending'
        )
        
        # Create tickets
        created_tickets = []
        
        for ticket_type, quantity in ticket_types.items():
            for _ in range(quantity):
                ticket = Ticket.objects.create(
                    ticket_type=ticket_type,
                    user=user,
                    status='pending',
                    ticket_code=uuid.uuid4()
                )
                created_tickets.append(ticket)
                payment.tickets.add(ticket)
        
        return payment, created_tickets

def cancel_tickets(payment_id):
    """
    Cancel tickets associated with a payment
    
    Args:
        payment_id: The ID of the payment to cancel
    """
    try:
        payment = Payment.objects.get(id=payment_id)
        
        # Update payment status
        payment.payment_status = 'refunded'
        payment.save()
        
        # Update all associated tickets to cancelled
        payment.tickets.update(status='cancelled')
        
        return True
    except Payment.DoesNotExist:
        return False