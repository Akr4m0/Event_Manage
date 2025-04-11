# payments/serializers.py
from rest_framework import serializers
from .models import Payment
from tickets.serializers import TicketSerializer

class PaymentSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=True)
    user_username = serializers.ReadOnlyField(source='user.username')
    approver_username = serializers.ReadOnlyField(source='approved_by.username')
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_username', 'tickets', 'amount',
            'payment_date', 'payment_status', 'payment_method',
            'transaction_id', 'is_offline_approved', 'approved_by',
            'approver_username', 'approval_date'
        ]
        read_only_fields = ['payment_date', 'transaction_id', 'approved_by', 'approval_date']