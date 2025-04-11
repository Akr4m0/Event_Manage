# tickets/models.py
from django.db import models
from django.contrib.auth.models import User
from events.models import Event
import uuid

class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField(default=0)  # 0 means unlimited
    
    def __str__(self):
        return f"{self.name} - {self.event.title}"

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('used', 'Used'),
    )
    
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    purchase_date = models.DateTimeField(auto_now_add=True)
    ticket_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    checked_in = models.BooleanField(default=False)
    checked_in_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Ticket {self.ticket_code} - {self.ticket_type.event.title}"