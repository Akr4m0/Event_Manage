# events/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from events.models import Event, EventCategory
from tickets.models import TicketType, Ticket
from payments.models import Payment

class EventViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        
        self.category = EventCategory.objects.create(
            name="Conference",
            description="Professional conferences"
        )
        
        self.now = timezone.now()
        self.future = self.now + timedelta(days=7)
        
        self.event = Event.objects.create(
            title="Test Conference",
            description="A test conference event",
            category=self.category,
            organizer=self.organizer,
            location="Test Venue",
            start_date=self.now + timedelta(days=1),
            end_date=self.now + timedelta(days=2),
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
    
    def test_home_view(self):
        """Test home page loads correctly"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EventHub')
        self.assertIn('featured_events', response.context)
        self.assertIn('categories', response.context)
    
    def test_event_list_view(self):
        """Test event list page loads with events"""
        response = self.client.get(reverse('event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        self.assertIn('page_obj', response.context)
    
    def test_event_list_with_filters(self):
        """Test event list filtering"""
        # Test category filter
        response = self.client.get(reverse('event_list'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        
        # Test search filter
        response = self.client.get(reverse('event_list'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        
        # Test date filter
        response = self.client.get(reverse('event_list'), {'date': 'this-week'})
        self.assertEqual(response.status_code, 200)
    
    def test_event_detail_view(self):
        """Test event detail page"""
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        self.assertContains(response, self.event.description)
        self.assertIn('ticket_types', response.context)
    
    def test_event_detail_draft_access(self):
        """Test that draft events are only visible to organizers"""
        # Create draft event
        draft_event = Event.objects.create(
            title="Draft Event",
            description="This is a draft",
            category=self.category,
            organizer=self.organizer,
            location="Test Location",
            start_date=self.future,
            end_date=self.future + timedelta(hours=2),
            status="draft"
        )
        
        # Anonymous user should be redirected
        response = self.client.get(reverse('event_detail', args=[draft_event.id]))
        self.assertEqual(response.status_code, 302)
        
        # Non-organizer should be redirected
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('event_detail', args=[draft_event.id]))
        self.assertEqual(response.status_code, 302)
        
        # Organizer should have access
        self.client.login(username='organizer', password='organizerpass123')
        response = self.client.get(reverse('event_detail', args=[draft_event.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_create_event_requires_login(self):
        """Test that creating events requires authentication"""
        response = self.client.get(reverse('create_event'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_create_event_get(self):
        """Test create event form loads"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('create_event'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('categories', response.context)
    
    def test_create_event_post(self):
        """Test creating a new event"""
        self.client.login(username='testuser', password='testpassword123')
        
        event_data = {
            'title': 'New Test Event',
            'description': 'This is a new test event',
            'category': self.category.id,
            'location': 'New York',
            'start_date': (self.now + timedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
            'end_date': (self.now + timedelta(days=5, hours=3)).strftime('%Y-%m-%d %H:%M'),
            'max_attendees': 200,
            'status': 'published',
            'ticket_name[]': ['General', 'VIP'],
            'ticket_price[]': ['25.00', '100.00'],
            'ticket_quantity[]': ['100', '20'],
            'ticket_description[]': ['General admission', 'VIP access'],
        }
        
        response = self.client.post(reverse('create_event'), event_data)
        
        # Check event was created
        self.assertTrue(Event.objects.filter(title='New Test Event').exists())
        event = Event.objects.get(title='New Test Event')
        self.assertEqual(event.organizer, self.user)
        
        # Check ticket types were created
        self.assertEqual(event.ticket_types.count(), 2)
        
        # Should redirect to event detail
        self.assertEqual(response.status_code, 302)
    
    def test_edit_event_requires_organizer(self):
        """Test that only organizers can edit their events"""
        # Non-organizer should be redirected
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('edit_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 302)
        
        # Organizer should have access
        self.client.login(username='organizer', password='organizerpass123')
        response = self.client.get(reverse('edit_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_cancel_event(self):
        """Test cancelling an event"""
        self.client.login(username='organizer', password='organizerpass123')
        
        # Create some tickets for the event
        ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.user,
            status='confirmed'
        )
        
        response = self.client.post(reverse('cancel_event', args=[self.event.id]))
        
        # Refresh from database
        self.event.refresh_from_db()
        ticket.refresh_from_db()
        
        self.assertEqual(self.event.status, 'cancelled')
        self.assertEqual(ticket.status, 'cancelled')
        self.assertEqual(response.status_code, 302)
    
    def test_my_events_view(self):
        """Test my events page"""
        self.client.login(username='organizer', password='organizerpass123')
        
        # Create a ticket for the user
        ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            user=self.organizer,
            status='confirmed'
        )
        
        response = self.client.get(reverse('my_events'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('organized_events', response.context)
        self.assertIn('attended_events', response.context)
        
        # Check that the organized event appears
        self.assertIn(self.event, response.context['organized_events'])

class EventFormValidationTest(TestCase):
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
        self.client = Client()
        self.client.login(username='testuser', password='testpassword123')
    
    def test_create_event_with_past_date(self):
        """Test that events cannot be created with past dates"""
        past_date = timezone.now() - timedelta(days=1)
        
        event_data = {
            'title': 'Past Event',
            'description': 'This should fail',
            'category': self.category.id,
            'location': 'Test Location',
            'start_date': past_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': (past_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
            'max_attendees': 100,
            'status': 'published',
            'ticket_name[]': ['General'],
            'ticket_price[]': ['10.00'],
            'ticket_quantity[]': ['50'],
            'ticket_description[]': ['General admission'],
        }
        
        response = self.client.post(reverse('create_event'), event_data)
        
        # Should not create the event
        self.assertFalse(Event.objects.filter(title='Past Event').exists())
        # Should show error message
        self.assertContains(response, 'Start date cannot be in the past')
    
    def test_create_event_with_invalid_dates(self):
        """Test that end date must be after start date"""
        start_date = timezone.now() + timedelta(days=1)
        end_date = start_date - timedelta(hours=1)  # End before start
        
        event_data = {
            'title': 'Invalid Date Event',
            'description': 'This should fail',
            'category': self.category.id,
            'location': 'Test Location',
            'start_date': start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
            'max_attendees': 100,
            'status': 'published',
            'ticket_name[]': ['General'],
            'ticket_price[]': ['10.00'],
            'ticket_quantity[]': ['50'],
            'ticket_description[]': ['General admission'],
        }
        
        response = self.client.post(reverse('create_event'), event_data)
        
        # Should not create the event
        self.assertFalse(Event.objects.filter(title='Invalid Date Event').exists())
        # Should show error message
        self.assertContains(response, 'End date must be after start date')
    
    def test_create_event_without_tickets(self):
        """Test that events must have at least one ticket type"""
        event_data = {
            'title': 'No Tickets Event',
            'description': 'This should fail',
            'category': self.category.id,
            'location': 'Test Location',
            'start_date': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
            'end_date': (timezone.now() + timedelta(days=1, hours=2)).strftime('%Y-%m-%d %H:%M'),
            'max_attendees': 100,
            'status': 'published',
            'ticket_name[]': [''],  # Empty ticket name
            'ticket_price[]': [''],
            'ticket_quantity[]': [''],
            'ticket_description[]': [''],
        }
        
        response = self.client.post(reverse('create_event'), event_data)
        
        # Should not create the event
        self.assertFalse(Event.objects.filter(title='No Tickets Event').exists())
        # Should show error message
        self.assertContains(response, 'Please add at least one ticket type')

class EventSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        self.category1 = EventCategory.objects.create(name="Music", description="Music events")
        self.category2 = EventCategory.objects.create(name="Sports", description="Sports events")
        
        # Create multiple events for testing
        for i in range(5):
            Event.objects.create(
                title=f"Music Event {i}",
                description=f"Description for music event {i}",
                category=self.category1,
                organizer=self.user,
                location="Music Hall",
                start_date=timezone.now() + timedelta(days=i),
                end_date=timezone.now() + timedelta(days=i, hours=2),
                status="published"
            )
        
        for i in range(3):
            Event.objects.create(
                title=f"Sports Event {i}",
                description=f"Description for sports event {i}",
                category=self.category2,
                organizer=self.user,
                location="Stadium",
                start_date=timezone.now() + timedelta(days=i),
                end_date=timezone.now() + timedelta(days=i, hours=3),
                status="published"
            )
    
    def test_search_by_title(self):
        """Test searching events by title"""
        response = self.client.get(reverse('event_list'), {'q': 'Music'})
        self.assertEqual(response.status_code, 200)
        
        # Should find all music events
        for event in response.context['page_obj']:
            self.assertIn('Music', event.title)
    
    def test_search_by_location(self):
        """Test searching events by location"""
        response = self.client.get(reverse('event_list'), {'q': 'Stadium'})
        self.assertEqual(response.status_code, 200)
        
        # Should find all stadium events
        for event in response.context['page_obj']:
            self.assertEqual(event.location, 'Stadium')
    
    def test_filter_by_category(self):
        """Test filtering events by category"""
        response = self.client.get(reverse('event_list'), {'category': self.category1.id})
        self.assertEqual(response.status_code, 200)
        
        # Should only show music events
        for event in response.context['page_obj']:
            self.assertEqual(event.category, self.category1)
    
    def test_pagination(self):
        """Test event list pagination"""
        # Create more events to test pagination
        for i in range(15):
            Event.objects.create(
                title=f"Extra Event {i}",
                description=f"Description {i}",
                category=self.category1,
                organizer=self.user,
                location="Venue",
                start_date=timezone.now() + timedelta(days=10+i),
                end_date=timezone.now() + timedelta(days=10+i, hours=2),
                status="published"
            )
        
        response = self.client.get(reverse('event_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check pagination exists
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertEqual(len(response.context['page_obj']), 9)  # 9 events per page