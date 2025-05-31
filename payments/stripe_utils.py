# payments/stripe_utils.py
import stripe
from django.conf import settings
from .models import Payment
import logging

logger = logging.getLogger(__name__)

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
        The checkout session URL or None if failed
    """
    try:
        # Get tickets from the payment
        line_items = []
        
        # Group tickets by type for better display
        ticket_groups = {}
        for ticket in payment.tickets.all():
            ticket_type = ticket.ticket_type
            if ticket_type.id not in ticket_groups:
                ticket_groups[ticket_type.id] = {
                    'ticket_type': ticket_type,
                    'count': 0
                }
            ticket_groups[ticket_type.id]['count'] += 1
        
        # Create line items for Stripe
        for group in ticket_groups.values():
            ticket_type = group['ticket_type']
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{ticket_type.event.title} - {ticket_type.name}",
                        'description': ticket_type.description or f"Ticket for {ticket_type.event.title}",
                        'metadata': {
                            'event_id': str(ticket_type.event.id),
                            'ticket_type_id': str(ticket_type.id),
                        }
                    },
                    'unit_amount': int(ticket_type.price * 100),  # Convert to cents
                },
                'quantity': group['count'],
            })
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(payment.id),
            metadata={
                'payment_id': str(payment.id),
                'user_id': str(payment.user.id),
            },
            customer_email=payment.user.email,
        )
        
        # Store the Stripe session ID in our payment record
        payment.stripe_session_id = checkout_session.id
        payment.save()
        
        logger.info(f"Created Stripe checkout session {checkout_session.id} for payment {payment.id}")
        
        return checkout_session.url
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {str(e)}")
        return None

def retrieve_checkout_session(session_id):
    """
    Retrieve a checkout session from Stripe
    
    Args:
        session_id: The Stripe session ID
        
    Returns:
        The session object or None if failed
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {str(e)}")
        return None

def handle_checkout_completion(session):
    """
    Handle Stripe checkout session completion webhook
    
    Args:
        session: The Stripe checkout session
        
    Returns:
        The updated Payment object or None if failed
    """
    try:
        # Get payment by client reference ID (which is our payment ID)
        payment_id = session.get('client_reference_id')
        if not payment_id:
            logger.error("No client_reference_id in session")
            return None
        
        payment = Payment.objects.get(id=payment_id)
        
        # Update payment with Stripe details
        payment.stripe_session_id = session.id
        payment.stripe_payment_intent = session.payment_intent
        
        # Update payment status based on Stripe status
        if session.payment_status == 'paid':
            payment.payment_status = 'completed'
            # Update all associated tickets to confirmed
            payment.tickets.update(status='confirmed')
            logger.info(f"Payment {payment.id} completed successfully")
        else:
            payment.payment_status = 'failed'
            logger.warning(f"Payment {payment.id} failed with status: {session.payment_status}")
        
        payment.save()
        return payment
        
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for session {session.id}")
        return None
    except Exception as e:
        logger.error(f"Error handling checkout completion: {str(e)}")
        return None

def create_payment_intent(amount, currency='usd', metadata=None):
    """
    Create a payment intent directly (for custom payment flows)
    
    Args:
        amount: Amount in dollars (will be converted to cents)
        currency: Currency code (default: usd)
        metadata: Optional metadata dict
        
    Returns:
        The payment intent object or None if failed
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency,
            metadata=metadata or {},
            automatic_payment_methods={
                'enabled': True,
            },
        )
        return intent
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {str(e)}")
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
        # First, retrieve the payment intent
        if not payment.stripe_payment_intent:
            logger.error(f"No payment intent found for payment {payment.id}")
            return None
        
        # Create refund
        refund = stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent,
            reason='requested_by_customer',
        )
        
        # Update payment status
        payment.payment_status = 'refunded'
        payment.save()
        
        # Update tickets status
        payment.tickets.update(status='cancelled')
        
        logger.info(f"Created refund {refund.id} for payment {payment.id}")
        return refund
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating refund: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating refund: {str(e)}")
        return None

def verify_webhook_signature(payload, signature, endpoint_secret):
    """
    Verify that a webhook payload came from Stripe
    
    Args:
        payload: The raw request body
        signature: The Stripe-Signature header value
        endpoint_secret: Your webhook endpoint secret
        
    Returns:
        The constructed event object or None if verification failed
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, endpoint_secret
        )
        return event
    except ValueError:
        # Invalid payload
        logger.error("Invalid webhook payload")
        return None
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        logger.error("Invalid webhook signature")
        return None

def get_payment_method_details(payment_method_id):
    """
    Get details about a payment method
    
    Args:
        payment_method_id: The Stripe payment method ID
        
    Returns:
        The payment method object or None if failed
    """
    try:
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        return payment_method
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving payment method: {str(e)}")
        return None