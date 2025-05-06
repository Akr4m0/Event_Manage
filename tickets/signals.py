# tickets/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import Ticket
from payments.models import Payment

@receiver(post_save, sender=Ticket)
def send_ticket_email(sender, instance, created, **kwargs):
    """Send an email when a ticket is created or status is updated"""
    if created:
        # Don't send email on creation as ticket is still pending
        return
    
    # Only send email when status changes to confirmed
    if instance.status == 'confirmed':
        event = instance.ticket_type.event
        user = instance.user
        
        # Prepare email context
        context = {
            'user': user,
            'ticket': instance,
            'event': event,
            'ticket_url': f"{settings.SITE_URL}/tickets/{instance.ticket_code}/"
        }
        
        # Render email content
        subject = f"Your ticket for {event.title} is confirmed!"
        html_message = render_to_string('tickets/emails/ticket_confirmed.html', context)
        plain_message = render_to_string('tickets/emails/ticket_confirmed.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

@receiver(post_save, sender=Payment)
def update_ticket_status(sender, instance, **kwargs):
    """Update ticket status when payment status changes"""
    if instance.payment_status == 'completed':
        # Update all associated tickets to confirmed
        instance.tickets.update(status='confirmed')
    elif instance.payment_status == 'refunded':
        # Update all associated tickets to cancelled
        instance.tickets.update(status='cancelled')