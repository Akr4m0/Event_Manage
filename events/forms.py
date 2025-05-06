# events/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event, EventCategory

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'location', 'start_date', 
                  'end_date', 'max_attendees', 'status', 'banner_image']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
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
            raise ValidationError('Cannot create events in the past')
        
        return cleaned_data

class TicketTypeFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Ensure at least one ticket type is created
        if any(self.errors):
            return
        
        if not any(cleaned_data and not cleaned_data.get('DELETE', False)
                  for cleaned_data in self.cleaned_data):
            raise ValidationError('At least one ticket type is required')