# tickets/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import TicketType

class TicketPurchaseForm(forms.Form):
    """Form for purchasing tickets"""
    quantity = forms.IntegerField(
        min_value=1,
        max_value=10,  # Limit for a single purchase
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10'
        })
    )
    
    def __init__(self, *args, ticket_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket_type = ticket_type
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        
        if self.ticket_type and self.ticket_type.quantity_available > 0:
            # Check if enough tickets are available
            available = self.ticket_type.quantity_available - self.ticket_type.tickets.count()
            if quantity > available:
                raise forms.ValidationError(f"Only {available} tickets available")
        
        return quantity

class TicketTransferForm(forms.Form):
    """Form for transferring tickets"""
    recipient_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter the username of the recipient'
        })
    )
    
    def clean_recipient_username(self):
        username = self.cleaned_data.get('recipient_username')
        
        try:
            recipient = User.objects.get(username=username)
            return username
        except User.DoesNotExist:
            raise ValidationError(f"User '{username}' does not exist.")
        
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('recipient_username')
        
        if username:
            try:
                recipient = User.objects.get(username=username)
                
                # Additional validation can be added here
                # For example, preventing transfers to staff users
                if recipient.is_staff:
                    raise ValidationError("Cannot transfer tickets to staff users")
                
            except User.DoesNotExist:
                # Already handled in clean_recipient_username
                pass
        
        return cleaned_data