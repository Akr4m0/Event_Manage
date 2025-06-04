# tickets/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid
from events.models import Event, EventCategory
from tickets.models import Ticket, TicketType
from tickets.utils import validate_ticket_purchase, create_ticket
from payments.models import Payment

class TicketViewsTest(TestCase):
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
        
        # Create a confirmed ticket for testing
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user,
            status='confirmed',
            ticket_code=uuid.uuid4()
        )
    
    def test_my_tickets_view(self):
        """Test my tickets page displays user's tickets"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('my_tickets'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        self.assertContains(response, self.ticket_type.name)
        self.assertIn('tickets_by_event', response.context)
    
    def test_my_tickets_requires_login(self):
        """Test my tickets page requires authentication"""
        response = self.client.get(reverse('my_tickets'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_ticket_detail_view(self):
        """Test ticket detail page for ticket owner"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.ticket_code]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.ticket.ticket_code))
        self.assertContains(response, self.event.title)
        self.assertIn('qr_code', response.context)
    
    def test_ticket_detail_permission(self):
        """Test ticket detail page permissions"""
        # Other user should not have access
        self.client.login(username='otheruser', password='otherpassword123')
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.ticket_code]))
        self.assertEqual(response.status_code, 302)
        
        # Staff should have access
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.ticket_code]))
        self.assertEqual(response.status_code, 200)
    
    def test_download_ticket(self):
        """Test ticket download functionality"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('download_ticket', args=[self.ticket.ticket_code]))
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')  # Mock PDF
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_transfer_ticket_get(self):
        """Test transfer ticket form"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('transfer_ticket', args=[self.ticket.ticket_code]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transfer Ticket')
        self.assertContains(response, 'Recipient Username')
    
    def test_transfer_ticket_post_success(self):
        """Test successful ticket transfer"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('transfer_ticket', args=[self.ticket.ticket_code]), {
            'recipient_username': 'otheruser'
        })
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
        # Check ticket was transferred
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.user, self.other_user)
    
    def test_transfer_ticket_invalid_recipient(self):
        """Test ticket transfer with invalid recipient"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('transfer_ticket', args=[self.ticket.ticket_code]), {
            'recipient_username': 'nonexistentuser'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'does not exist')
        
        # Ticket should not be transferred
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.user, self.user)
    
    def test_transfer_ticket_to_self(self):
        """Test preventing ticket transfer to self"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('transfer_ticket', args=[self.ticket.ticket_code]), {
            'recipient_username': 'testuser'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cannot transfer a ticket to yourself')
    
    def test_transfer_used_ticket(self):
        """Test that used tickets cannot be transferred"""
        # Mark ticket as used
        self.ticket.status = 'used'
        self.ticket.checked_in = True
        self.ticket.save()
        
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('transfer_ticket', args=[self.ticket.ticket_code]))
        
        self.assertEqual(response.status_code, 302)
    
    def test_check_in_ticket_staff_only(self):
        """Test check-in requires staff privileges"""
        # Regular user should be denied
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('check_in_ticket', args=[self.ticket.ticket_code]))
        self.assertEqual(response.status_code, 302)
        
        # Staff should have access
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get(reverse('check_in_ticket', args=[self.ticket.ticket_code]))
        self.assertEqual(response.status_code, 302)  # Redirects after check-in
        
        # Verify ticket was checked in
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.checked_in)
        self.assertEqual(self.ticket.status, 'used')
    
    def test_scan_ticket_page(self):
        """Test ticket scanning page"""
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get(reverse('scan_ticket'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scan Tickets')
        self.assertContains(response, 'Scanner')
    
    def test_scan_ticket_ajax(self):
        """Test AJAX ticket scanning"""
        self.client.login(username='staff', password='staffpass123')
        
        response = self.client.post(reverse('scan_ticket'), {
            'ticket_code': str(self.ticket.ticket_code)
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('ticket', data)
        
        # Verify ticket was checked in
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.checked_in)
    
    def test_scan_invalid_ticket(self):
        """Test scanning invalid ticket code"""
        self.client.login(username='staff', password='staffpass123')
        
        response = self.client.post(reverse('scan_ticket'), {
            'ticket_code': 'invalid-code'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid ticket code', data['message'])
    
    def test_scan_already_used_ticket(self):
        """Test scanning already used ticket"""
        # Mark ticket as used
        self.ticket.checked_in = True
        self.ticket.checked_in_time = timezone.now()
        self.ticket.status = 'used'
        self.ticket.save()
        
        self.client.login(username='staff', password='staffpass123')
        
        response = self.client.post(reverse('scan_ticket'), {
            'ticket_code': str(self.ticket.ticket_code)
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('already been checked in', data['message'])
    
    def test_ticket_stats_view(self):
        """Test ticket statistics page"""
        # Create some additional tickets
        for i in range(5):
            Ticket.objects.create(
                ticket_type=self.ticket_type,
                user=self.user,
                status='confirmed' if i < 3 else 'used',
                checked_in=i >= 3,
                ticket_code=uuid.uuid4()
            )
        
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get(reverse('ticket_stats', args=[self.event.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ticket Statistics')
        self.assertIn('ticket_stats', response.context)
        self.assertIn('total_tickets', response.context)


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        self.category = EventCategory.objects.create(
            name="Test Category",
            description="Test description"
        )
        
        self.event = Event.objects.create(
            title="Test Event",
            description="Test description",
            category=self.category,
            organizer=self.user,
            location="Test Location",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            status="published"
        )
        
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="General",
            price=25.00,
            quantity_available=100
        )
    
    def test_ticket_creation(self):
        """Test ticket creation"""
        ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user,
            status='pending'
        )
        
        self.assertIsNotNone(ticket.ticket_code)
        self.assertEqual(ticket.status, 'pending')
        self.assertFalse(ticket.checked_in)
        self.assertIsNotNone(ticket.purchase_date)
    
    def test_ticket_str_method(self):
        """Test ticket string representation"""
        ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user
        )
        
        expected = f"Ticket {ticket.ticket_code} - {self.event.title}"
        self.assertEqual(str(ticket), expected)
    
    def test_ticket_type_str_method(self):
        """Test ticket type string representation"""
        expected = f"{self.ticket_type.name} - {self.event.title}"
        self.assertEqual(str(self.ticket_type), expected)
    
    def test_ticket_unique_code(self):
        """Test that ticket codes are unique"""
        tickets = []
        for i in range(10):
            ticket = Ticket.objects.create(
                ticket_type=self.ticket_type,
                user=self.user
            )
            tickets.append(ticket)
        
        # Check all codes are unique
        codes = [t.ticket_code for t in tickets]
        self.assertEqual(len(codes), len(set(codes)))


class TicketUtilsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        self.category = EventCategory.objects.create(
            name="Test Category",
            description="Test description"
        )
        
        self.event = Event.objects.create(
            title="Test Event",
            description="Test description",
            category=self.category,
            organizer=self.user,
            location="Test Location",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            status="published"
        )
        
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="Limited",
            price=25.00,
            quantity_available=5
        )
        
        self.unlimited_ticket_type = TicketType.objects.create(
            event=self.event,
            name="Unlimited",
            price=20.00,
            quantity_available=0  # 0 means unlimited
        )
    
    def test_validate_ticket_purchase_with_availability(self):
        """Test ticket purchase validation with available tickets"""
        valid, message = validate_ticket_purchase(self.ticket_type, 3)
        self.assertTrue(valid)
        self.assertEqual(message, "Tickets available")
    
    def test_validate_ticket_purchase_exceeds_availability(self):
        """Test ticket purchase validation when exceeding availability"""
        # Create 3 tickets (leaving 2 available)
        for i in range(3):
            Ticket.objects.create(
                ticket_type=self.ticket_type,
                user=self.user,
                status='confirmed'
            )
        
        valid, message = validate_ticket_purchase(self.ticket_type, 3)
        self.assertFalse(valid)
        self.assertEqual(message, "Only 2 tickets available")
    
    def test_validate_ticket_purchase_unlimited(self):
        """Test ticket purchase validation for unlimited tickets"""
        valid, message = validate_ticket_purchase(self.unlimited_ticket_type, 1000)
        self.assertTrue(valid)
        self.assertEqual(message, "Tickets available")
    
    def test_create_ticket_utility(self):
        """Test create_ticket utility function"""
        ticket = create_ticket(self.ticket_type, self.user)
        
        self.assertIsInstance(ticket, Ticket)
        self.assertEqual(ticket.ticket_type, self.ticket_type)
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.status, 'pending')
        self.assertIsNotNone(ticket.ticket_code)


class TicketAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        self.category = EventCategory.objects.create(
            name="Test Category",
            description="Test description"
        )
        
        self.event = Event.objects.create(
            title="Test Event",
            description="Test description",
            category=self.category,
            organizer=self.user,
            location="Test Location",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            status="published"
        )
        
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="General",
            price=25.00,
            quantity_available=100
        )
        
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user,
            status='confirmed'
        )
    
    def test_ticket_list_api(self):
        """Test ticket list API endpoint"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get('/api/tickets/tickets/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        
        # User should only see their own tickets
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.ticket.id)
    
    def test_ticket_check_in_api(self):
        """Test ticket check-in API endpoint"""
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(f'/api/tickets/tickets/{self.ticket.id}/check_in/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['checked_in'])
        self.assertEqual(data['status'], 'used')
        
        # Verify in database
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.checked_in)
        self.assertIsNotNone(self.ticket.checked_in_time)
    
    def test_ticket_type_list_api(self):
        """Test ticket type list API endpoint"""
        response = self.client.get('/api/tickets/types/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], 'General')