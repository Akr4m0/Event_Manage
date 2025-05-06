# events/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from events.models import Event, EventCategory
from datetime import timedelta

class EventCategoryModelTest(TestCase):
    def setUp(self):
        self.category = EventCategory.objects.create(
            name="Conference",
            description="Professional conferences and meetups"
        )
    
    def test_category_creation(self):
        self.assertEqual(self.category.name, "Conference")
        self.assertEqual(self.category.description, "Professional conferences and meetups")
        self.assertEqual(str(self.category), "Conference")

class EventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        self.category = EventCategory.objects.create(
            name="Concert",
            description="Music events"
        )
        
        self.now = timezone.now()
        self.tomorrow = self.now + timedelta(days=1)
        
        self.event = Event.objects.create(
            title="Test Event",
            description="Test Description",
            category=self.category,
            organizer=self.user,
            location="Test Location",
            start_date=self.now,
            end_date=self.tomorrow,
            status="published",
            max_attendees=100
        )
    
    def test_event_creation(self):
        self.assertEqual(self.event.title, "Test Event")
        self.assertEqual(self.event.organizer, self.user)
        self.assertEqual(self.event.category, self.category)
        self.assertEqual(str(self.event), "Test Event")
    
    def test_is_past_event(self):
        # Current event is not past
        self.assertFalse(self.event.is_past_event)
        
        # Create a past event
        past_start = self.now - timedelta(days=2)
        past_end = self.now - timedelta(days=1)
        past_event = Event.objects.create(
            title="Past Event",
            description="Past Description",
            category=self.category,
            organizer=self.user,
            location="Past Location",
            start_date=past_start,
            end_date=past_end,
            status="completed"
        )
        
        self.assertTrue(past_event.is_past_event)