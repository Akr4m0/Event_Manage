# payments/views.py - Updated version
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer
from tickets.models import Ticket, TicketType
from django.db import transaction
import uuid

class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for payments
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['payment_status', 'payment_method', 'user']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve_offline_payment(self, request, pk=None):
        payment = self.get_object()
        if payment.payment_method != 'offline':
            return Response({'message': 'Only offline payments can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        if payment.is_offline_approved:
            return Response({'message': 'Payment already approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment.is_offline_approved = True
        payment.approved_by = request.user
        payment.approval_date = timezone.now()
        payment.payment_status = 'completed'
        payment.save()
        
        # Update related tickets to confirmed status
        payment.tickets.update(status='confirmed')
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def process_stripe_payment(self, request, pk=None):
        """
        Process payment using Stripe integration
        """
        payment = self.get_object()
        if payment.payment_status != 'pending':
            return Response({'message': 'Payment already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Here we would integrate with Stripe payment processing
            # For now, we'll simulate successful payment
            payment.payment_status = 'completed'
            payment.save()
            
            # Update tickets to confirmed
            payment.tickets.update(status='confirmed')
            
            return Response({'message': 'Payment processed successfully', 'payment_id': payment.id})
        except Exception as e:
            payment.payment_status = 'failed'
            payment.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel_payment(self, request, pk=None):
        """
        Cancel a pending payment
        """
        payment = self.get_object()
        if payment.payment_status not in ['pending', 'processing']:
            return Response({'message': 'Cannot cancel completed payment'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment.payment_status = 'cancelled'
        payment.save()
        
        # Update tickets to cancelled
        payment.tickets.update(status='cancelled')
        
        return Response({'message': 'Payment cancelled successfully'})
    
    def create(self, request, *args, **kwargs):
        """
        Override create method to handle ticket creation with payment
        """
        # Extract ticket information from request
        ticket_data = request.data.get('tickets', [])
        
        # Create the payment
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(user=request.user)
        
        # Process and create tickets
        for ticket_info in ticket_data:
            ticket_type_id = ticket_info.get('ticket_type_id')
            quantity = ticket_info.get('quantity', 1)
            
            # Create tickets based on the quantity
            for _ in range(quantity):
                ticket = Ticket.objects.create(
                    ticket_type_id=ticket_type_id,
                    user=request.user,
                    status='pending'
                )
                payment.tickets.add(ticket)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)