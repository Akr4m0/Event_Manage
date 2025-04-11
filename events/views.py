# events/views.py
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Event, EventCategory
from .serializers import EventSerializer, EventCategorySerializer

class EventCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for event categories
    """
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'start_date', 'location']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_date', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)