# payments/models.py
from django.db import models
from django.contrib.auth.models import User
from tickets.models import Ticket
import uuid

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('offline', 'Offline Payment'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    tickets = models.ManyToManyField(Ticket, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_offline_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payments')
    approval_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.user.username}"