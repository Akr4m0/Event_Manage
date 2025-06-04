# events/views.py - Updated with role-based permissions
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Event, EventCategory
from .serializers import EventSerializer, EventCategorySerializer
from .permissions import IsOrganizerOrReadOnly, IsOrganizerOrStaff, CanCreateEvent, CanManageEventCategory

class EventCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for event categories
    """
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanManageEventCategory]

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'start_date', 'location']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_date', 'created_at']
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, CanCreateEvent]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizerOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizerOrStaff])
    def cancel(self, request, pk=None):
        """
        Cancel an event
        """
        event = self.get_object()
        event.status = 'cancelled'
        event.save()
        
        # Cancel all associated tickets
        for ticket_type in event.ticket_types.all():
            ticket_type.tickets.all().update(status='cancelled')
        
        return Response({'status': 'event cancelled'})
        
    def get_queryset(self):
        queryset = Event.objects.all()
        
        # Filter by date range if provided
        start_date_min = self.request.query_params.get('start_date_min')
        start_date_max = self.request.query_params.get('start_date_max')
        
        if start_date_min:
            queryset = queryset.filter(start_date__gte=start_date_min)
        if start_date_max:
            queryset = queryset.filter(start_date__lte=start_date_max)
            
        # Filter by organizer if provided
        organizer = self.request.query_params.get('organizer')
        if organizer:
            queryset = queryset.filter(organizer__username=organizer)
            
        return queryset