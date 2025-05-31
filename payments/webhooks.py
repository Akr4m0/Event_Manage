# payments/webhooks.py
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .stripe_utils import verify_webhook_signature, handle_checkout_completion
from .models import Payment

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events
    """
    payload = request.body
    signature_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Verify webhook signature
    event = verify_webhook_signature(
        payload, 
        signature_header, 
        settings.STRIPE_WEBHOOK_SECRET
    )
    
    if not event:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Handle successful payment
        payment = handle_checkout_completion(session)
        
        if payment:
            logger.info(f"Successfully processed payment {payment.id}")
            
            # Here you could send confirmation emails
            # send_payment_confirmation_email(payment)
        else:
            logger.error(f"Failed to process session {session.id}")
    
    elif event['type'] == 'checkout.session.expired':
        # Handle expired checkout sessions
        session = event['data']['object']
        payment_id = session.get('client_reference_id')
        
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
                if payment.payment_status == 'pending':
                    payment.payment_status = 'cancelled'
                    payment.save()
                    payment.tickets.update(status='cancelled')
                    logger.info(f"Cancelled expired payment {payment.id}")
            except Payment.DoesNotExist:
                logger.error(f"Payment {payment_id} not found")
    
    elif event['type'] == 'payment_intent.payment_failed':
        # Handle failed payments
        payment_intent = event['data']['object']
        
        # Find payment by payment intent ID
        try:
            payment = Payment.objects.get(stripe_payment_intent=payment_intent['id'])
            payment.payment_status = 'failed'
            payment.save()
            logger.info(f"Marked payment {payment.id} as failed")
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for intent {payment_intent['id']}")
    
    # Return 200 OK to acknowledge receipt of the event
    return HttpResponse(status=200)