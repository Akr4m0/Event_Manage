# payments/stripe_utils.py
import stripe
from django.conf import settings
from .models import Payment

# Configure Stripe with your API key
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_checkout_session(payment, success_url, cancel_url):
    """
    Create a Stripe checkout session for a payment
    
    Args:
        payment: The Payment object
        success_url: URL to redirect to after successful payment
        cancel_url: URL to redirect to after cancelled payment
        
    Returns:
        The checkout session URL
    """
    # Get tickets from the payment
    line_items = []
    for ticket in payment.tickets.all():
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"{ticket.ticket_type.event.title} - {ticket.ticket_type.name}",
                    'description': ticket.ticket_type.event.description[:255] if ticket.ticket_type.event.description else None,
                },
                'unit_amount': int(ticket.ticket_type.price * 100),  # Convert to cents
            },
            'quantity': 1,
        })
    
    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(payment.id),  # To identify the payment
        metadata={
            'payment_id': payment.id,
            'user_id': payment.user.id,
        }
    )
    
    # Update payment with Stripe session ID
    payment.transaction_id = checkout_session.id
    payment.save()
    
    return checkout_session.url

def handle_checkout_completion(session):
    """
    Handle Stripe checkout session completion webhook
    
    Args:
        session: The Stripe checkout session
        
    Returns:
        The updated Payment object
    """
    # Get payment by Stripe session ID
    try:
        payment = Payment.objects.get(transaction_id=session.id)
        
        # Update payment status
        if session.payment_status == 'paid':
            payment.payment_status = 'completed'
            
            # Update tickets status
            payment.tickets.update(status='confirmed')
        else:
            payment.payment_status = 'failed'
        
        payment.save()
        return payment
    except Payment.DoesNotExist:
        return None

def create_refund(payment):
    """
    Create a refund for a payment
    
    Args:
        payment: The Payment object
        
    Returns:
        The refund object or None if failed
    """
    try:
        # Get the checkout session
        session = stripe.checkout.Session.retrieve(payment.transaction_id)
        
        # Get payment intent
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        
        # Create refund
        refund = stripe.Refund.create(
            payment_intent=payment_intent.id,
            reason='requested_by_customer',
        )
        
        # Update payment status
        payment.payment_status = 'refunded'
        payment.save()
        
        # Update tickets status
        payment.tickets.update(status='cancelled')
        
        return refund
    except Exception as e:
        print(f"Refund error: {str(e)}")
        return None