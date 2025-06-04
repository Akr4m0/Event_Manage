# payments/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid
import json
from unittest.mock import patch, MagicMock
from events.models import Event, EventCategory
from tickets.models import Ticket, TicketType
from payments.models import Payment
from payments.stripe_utils import create_checkout_session, handle_checkout_completion

class PaymentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword123'
        )
        
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        self.category = EventCategory.objects.create(
            name="Conference",
            description="Professional conferences"
        )
        
        self.event = Event.objects.create(
            title="Test Conference",
            description="A test conference event",
            category=self.category,
            organizer=self.organizer,
            location="Test Venue",
            start_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=8),
            status="published",
            max_attendees=100
        )
        
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="General Admission",
            price=50.00,
            quantity_available=50,
            description="Standard ticket"
        )
        
        self.vip_ticket_type = TicketType.objects.create(
            event=self.event,
            name="VIP",
            price=150.00,
            quantity_available=10,
            description="VIP access"
        )
        
        # Create a test payment
        self.payment = Payment.objects.create(
            user=self.user,
            amount=50.00,
            payment_method='credit_card',
            payment_status='pending'
        )
        
        # Create a test ticket and link to payment
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user,
            status='pending',
            ticket_code=uuid.uuid4()
        )
        self.payment.tickets.add(self.ticket)
    
    def test_create_payment_requires_login(self):
        """Test that creating payment requires authentication"""
        response = self.client.post(reverse('create_payment'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_create_payment_success(self):
        """Test successful payment creation"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('create_payment'), {
            'event_id': self.event.id,
            'ticket_quantities[{}]'.format(self.ticket_type.id): '2',
            'ticket_quantities[{}]'.format(self.vip_ticket_type.id): '1',
        })
        
        # Should redirect to payment method selection
        self.assertEqual(response.status_code, 302)
        
        # Check payment was created
        payments = Payment.objects.filter(user=self.user).order_by('-id')
        self.assertTrue(payments.exists())
        
        payment = payments.first()
        expected_amount = (2 * 50.00) + (1 * 150.00)  # 2 general + 1 VIP
        self.assertEqual(payment.amount, expected_amount)
        self.assertEqual(payment.tickets.count(), 3)
    
    def test_create_payment_no_tickets_selected(self):
        """Test payment creation with no tickets selected"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('create_payment'), {
            'event_id': self.event.id,
        })
        
        # Should redirect back to event detail
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/events/{self.event.id}/', response.url)
    
    def test_create_payment_exceeds_availability(self):
        """Test payment creation when exceeding ticket availability"""
        # Create existing tickets to reduce availability
        for i in range(48):
            Ticket.objects.create(
                ticket_type=self.ticket_type,
                user=self.other_user,
                status='confirmed'
            )
        
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('create_payment'), {
            'event_id': self.event.id,
            'ticket_quantities[{}]'.format(self.ticket_type.id): '5',  # Only 2 left
        })
        
        # Should redirect back with error
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/events/{self.event.id}/', response.url)
    
    def test_select_payment_method_view(self):
        """Test payment method selection page"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('select_payment_method', args=[self.payment.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select Payment Method')
        self.assertContains(response, 'Credit/Debit Card')
        self.assertContains(response, 'PayPal')
        self.assertContains(response, 'Bank Transfer')
        self.assertContains(response, 'Cash Payment')
    
    def test_select_payment_method_post(self):
        """Test selecting a payment method"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('select_payment_method', args=[self.payment.id]), {
            'payment_method': 'offline'
        })
        
        # Should redirect to offline payment instructions
        self.assertEqual(response.status_code, 302)
        self.assertIn('process-offline', response.url)
        
        # Check payment method was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, 'offline')
    
    def test_process_offline_payment(self):
        """Test offline payment processing"""
        self.payment.payment_method = 'offline'
        self.payment.save()
        
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('process_offline_payment', args=[self.payment.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Offline Payment Instructions')
        self.assertContains(response, 'Bank Transfer Details')
        
        # Check payment status was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_status, 'processing')
    
    @patch('payments.payment_views.create_checkout_session')
    def test_process_online_payment_stripe(self, mock_create_session):
        """Test online payment processing with Stripe"""
        mock_create_session.return_value = 'https://checkout.stripe.com/test'
        
        self.payment.payment_method = 'credit_card'
        self.payment.save()
        
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('process_online_payment', args=[self.payment.id]))
        
        # Should redirect to Stripe checkout
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://checkout.stripe.com/test')
        
        # Verify create_checkout_session was called
        mock_create_session.assert_called_once()
    
    def test_payment_success_view(self):
        """Test payment success page"""
        self.payment.payment_status = 'completed'
        self.payment.save()
        self.ticket.status = 'confirmed'
        self.ticket.save()
        
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('payment_success', args=[self.payment.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Successful')
        self.assertContains(response, 'Thank you for your purchase')
        self.assertIn('tickets', response.context)
    
    def test_payment_cancel_view(self):
        """Test payment cancellation page"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('payment_cancel', args=[self.payment.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Cancelled')
        
        # Check payment was cancelled
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_status, 'cancelled')
        
        # Check tickets were cancelled
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'cancelled')
    
    def test_payment_status_view(self):
        """Test payment status page"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('payment_status', args=[self.payment.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Status')
        self.assertContains(response, str(self.payment.transaction_id))
        self.assertIn('payment', response.context)
        self.assertIn('tickets', response.context)
    
    def test_admin_payment_list_requires_staff(self):
        """Test admin payment list requires staff privileges"""
        # Regular user should be denied
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('admin_payment_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('home', response.url)
        
        # Staff user should have access
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get(reverse('admin_payment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Management')
    
    def test_admin_approve_payment(self):
        """Test admin payment approval"""
        # Create offline payment
        offline_payment = Payment.objects.create(
            user=self.other_user,
            amount=100.00,
            payment_method='offline',
            payment_status='processing'
        )
        
        # Create a ticket for this payment
        offline_ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.other_user,
            status='pending',
            ticket_code=uuid.uuid4()
        )
        offline_payment.tickets.add(offline_ticket)
        
        # Login as staff
        self.client.login(username='staff', password='staffpass123')
        
        # Approve payment
        response = self.client.post(reverse('admin_approve_payment', args=[offline_payment.id]), {
            'action': 'approve'
        })
        
        # Should redirect to admin payment list
        self.assertEqual(response.status_code, 302)
        self.assertIn('admin_payment_list', response.url)
        
        # Check payment was approved
        offline_payment.refresh_from_db()
        self.assertEqual(offline_payment.payment_status, 'completed')
        self.assertTrue(offline_payment.is_offline_approved)
        self.assertEqual(offline_payment.approved_by, self.staff_user)
        
        # Check ticket status was updated
        offline_ticket.refresh_from_db()
        self.assertEqual(offline_ticket.status, 'confirmed')
    
    def test_admin_reject_payment(self):
        """Test admin payment rejection"""
        # Create offline payment
        offline_payment = Payment.objects.create(
            user=self.other_user,
            amount=100.00,
            payment_method='offline',
            payment_status='processing'
        )
        
        # Create a ticket for this payment
        offline_ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.other_user,
            status='pending',
            ticket_code=uuid.uuid4()
        )
        offline_payment.tickets.add(offline_ticket)
        
        # Login as staff
        self.client.login(username='staff', password='staffpass123')
        
        # Reject payment
        response = self.client.post(reverse('admin_approve_payment', args=[offline_payment.id]), {
            'action': 'reject'
        })
        
        # Should redirect to admin payment list
        self.assertEqual(response.status_code, 302)
        self.assertIn('admin_payment_list', response.url)
        
        # Check payment was rejected
        offline_payment.refresh_from_db()
        self.assertEqual(offline_payment.payment_status, 'failed')
        
        # Check ticket status was updated
        offline_ticket.refresh_from_db()
        self.assertEqual(offline_ticket.status, 'cancelled')
    
    def test_validate_stripe_payment(self):
        """Test AJAX validation of Stripe payment"""
        self.client.login(username='testuser', password='testpassword123')
        
        # Create payment intent data
        data = {
            'payment_method_id': 'pm_test123',
            'payment_id': self.payment.id
        }
        
        # Send AJAX request
        response = self.client.post(
            reverse('validate_stripe_payment'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return successful JSON response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('redirect_url', response_data)
        
        # Check payment status was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_status, 'completed')
        
        # Check ticket status was updated
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'confirmed')
    
    def test_payment_security_other_user(self):
        """Test that users cannot access other users' payments"""
        self.client.login(username='otheruser', password='otherpassword123')
        
        # Try to access another user's payment
        response = self.client.get(reverse('payment_status', args=[self.payment.id]))
        
        # Should return 404 as the payment should not be found for this user
        self.assertEqual(response.status_code, 404)
        
        # Try to approve a payment
        response = self.client.post(reverse('admin_approve_payment', args=[self.payment.id]), {
            'action': 'approve'
        })
        
        # Non-staff user should be redirected
        self.assertEqual(response.status_code, 302)
        self.assertIn('home', response.url)
    
    @patch('payments.stripe_utils.stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_stripe_create):
        """Test creating a Stripe checkout session"""
        # Mock the Stripe API response
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/test-session'
        mock_stripe_create.return_value = mock_session
        
        # Call the function
        success_url = 'https://example.com/success'
        cancel_url = 'https://example.com/cancel'
        
        checkout_url = create_checkout_session(self.payment, success_url, cancel_url)
        
        # Verify results
        self.assertEqual(checkout_url, 'https://checkout.stripe.com/test-session')
        mock_stripe_create.assert_called_once()
        
        # Check payment was updated with session ID
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.stripe_session_id, 'cs_test_123')
    
    @patch('payments.stripe_utils.stripe.checkout.Session.retrieve')
    def test_handle_checkout_completion(self, mock_stripe_retrieve):
        """Test handling Stripe checkout completion webhook"""
        # Set up payment for testing
        self.payment.stripe_session_id = 'cs_test_123'
        self.payment.save()
        
        # Mock Stripe session
        mock_session = {
            'id': 'cs_test_123',
            'payment_intent': 'pi_test_123',
            'payment_status': 'paid',
            'client_reference_id': str(self.payment.id)
        }
        
        # Call the function
        updated_payment = handle_checkout_completion(mock_session)
        
        # Verify results
        self.assertIsNotNone(updated_payment)
        self.assertEqual(updated_payment.id, self.payment.id)
        
        # Check payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_status, 'completed')
        self.assertEqual(self.payment.stripe_payment_intent, 'pi_test_123')
        
        # Check tickets were updated
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'confirmed')