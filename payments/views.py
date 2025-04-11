# payments/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Payment
from .serializers import PaymentSerializer

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