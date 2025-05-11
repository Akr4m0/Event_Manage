from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event, EventCategory

class TicketTypeForm(forms.Form):
    """Form for adding ticket types to an event"""
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-dark',
            'placeholder': 'e.g. General Admission'
        })
    )
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-dark',
            'step': '0.01',
            'min': '0',
            'placeholder': '0.00'
        })
    )
    quantity_available = forms.IntegerField(
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-dark',
            'min': '0',
            'placeholder': '0 for unlimited'
        })
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-dark',
            'placeholder': 'Optional description'
        })
    )
    
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'location', 'start_date', 
                  'end_date', 'max_attendees', 'status', 'banner_image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-dark', 
                'placeholder': 'Give your event a clear, catchy title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-dark', 
                'rows': 5,
                'placeholder': 'Describe your event, include what attendees can expect'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control form-control-dark',
                'placeholder': 'Venue name or address'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control form-control-dark', 
                'type': 'text',
                'placeholder': 'Select date and time'
            }),
           'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control form-control-dark', 
                'type': 'text',
                'placeholder': 'Select date and time'
            }),
            'max_attendees': forms.NumberInput(attrs={
                'class': 'form-control form-control-dark', 
                'min': 0,
                'placeholder': '0 for unlimited'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select form-control-dark'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select form-control-dark'
            }),
            'banner_image': forms.FileInput(attrs={
                'class': 'form-control form-control-dark',
                'accept': 'image/*'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate that end_date is after start_date
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date')
        
        # Validate that start_date is not in the past
        if start_date and start_date < timezone.now():
            raise ValidationError('Start date cannot be in the past')
        
        # Validate category (should exist in the database)
        category = cleaned_data.get('category')
        if category and not EventCategory.objects.filter(id=category.id).exists():
            raise ValidationError('Selected category does not exist')
            
        # Validate max_attendees is non-negative
        max_attendees = cleaned_data.get('max_attendees')
        if max_attendees and max_attendees < 0:
            raise ValidationError('Maximum attendees cannot be negative')
            
        return cleaned_data