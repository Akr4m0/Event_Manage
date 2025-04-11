# tickets/serializers.py
from rest_framework import serializers
from .models import Ticket, TicketType
from events.serializers import EventSerializer

class TicketTypeSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    
    class Meta:
        model = TicketType
        fields = [
            'id', 'event', 'event_title', 'name', 
            'description', 'price', 'quantity_available'
        ]

class TicketSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')
    event_title = serializers.ReadOnlyField(source='ticket_type.event.title')
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type', 'ticket_type_name', 'event_title',
            'user', 'user_username', 'purchase_date', 'ticket_code',
            'status', 'checked_in', 'checked_in_time'
        ]
        read_only_fields = ['purchase_date', 'ticket_code', 'checked_in_time']