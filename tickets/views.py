# tickets/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Ticket, TicketType
from .serializers import TicketSerializer, TicketTypeSerializer

class TicketTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for ticket types
    """
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['event']

class TicketViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tickets
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['ticket_type', 'status', 'user']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        ticket = self.get_object()
        if ticket.checked_in:
            return Response({'message': 'Ticket already checked in'}, status=status.HTTP_400_BAD_REQUEST)
        
        ticket.checked_in = True
        ticket.checked_in_time = timezone.now()
        ticket.status = 'used'
        ticket.save()
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)