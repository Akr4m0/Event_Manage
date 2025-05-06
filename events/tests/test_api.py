# events/tests/test_api.py
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from events.models import Event, EventCategory
from django.utils import timezone
from datetime import timedelta

class EventAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.category = EventCategory.objects.create(
            name="Workshop",
            description="Hands-on learning sessions"
        )
        
        self.now = timezone.now()
        self.future = self.now + timedelta(days=7)
        
        self.event_data = {
            "title": "API Test Event",
            "description": "Event created through API",
            "category": self.category.id,
            "location": "API Test Location",
            "start_date": self.now.isoformat(),
            "end_date": self.future.isoformat(),
            "status": "published",
            "max_attendees": 50
        }
        
        self.event = Event.objects.create(
            title="Existing Test Event",
            description="Pre-existing event",
            category=self.category,
            organizer=self.user,
            location="Test Location",
            start_date=self.now,
            end_date=self.future,
            status="published"
        )
    
    def test_create_event(self):
        url = reverse('event-list')
        response = self.client.post(url, self.event_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Event.objects.get(title="API Test Event").organizer, self.user)
    
    def test_list_events(self):
        url = reverse('event-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_event(self):
        url = reverse('event-detail', args=[self.event.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Existing Test Event")
    
    def test_update_event(self):
        url = reverse('event-detail', args=[self.event.id])
        updated_data = {"title": "Updated Event Title"}
        response = self.client.patch(url, updated_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.get(id=self.event.id).title, "Updated Event Title")
    
    def test_delete_event(self):
        url = reverse('event-detail', args=[self.event.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 0)
    
    def test_unauthorized_update(self):
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpassword"
        )
        
        # Create an event owned by other user
        other_event = Event.objects.create(
            title="Other User's Event",
            description="Event by other user",
            category=self.category,
            organizer=other_user,
            location="Other Location",
            start_date=self.now,
            end_date=self.future,
            status="published"
        )
        
        # Try to update other user's event
        url = reverse('event-detail', args=[other_event.id])
        updated_data = {"title": "Attempted Update"}
        response = self.client.patch(url, updated_data, format='json')
        
        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Event.objects.get(id=other_event.id).title, "Other User's Event")