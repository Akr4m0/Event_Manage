# events/serializers.py
from rest_framework import serializers
from .models import Event, EventCategory

class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ['id', 'name', 'description']

class EventSerializer(serializers.ModelSerializer):
    organizer_username = serializers.ReadOnlyField(source='organizer.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'organizer', 'organizer_username', 'location', 'start_date', 
            'end_date', 'created_at', 'updated_at', 'status', 
            'max_attendees', 'banner_image'
        ]
        read_only_fields = ['created_at', 'updated_at']