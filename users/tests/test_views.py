# users/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from users.models import Profile
from social_django.models import UserSocialAuth

class UserAuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
    
    def test_login_view_get(self):
        """Test login page loads correctly"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
        self.assertContains(response, 'Sign in with Google')
        self.assertContains(response, 'Sign in with Facebook')
    
    def test_login_view_post_success(self):
        """Test successful login"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_view_post_failure(self):
        """Test failed login with wrong credentials"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on login page
        self.assertContains(response, 'Invalid username or password')
    
    def test_logout_view(self):
        """Test logout functionality"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_register_view_get(self):
        """Test registration page loads correctly"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
        self.assertContains(response, 'Sign up with Google')
    
    def test_register_view_post_success(self):
        """Test successful registration"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after registration
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        new_user = User.objects.get(username='newuser')
        
        # Check profile was created
        self.assertTrue(hasattr(new_user, 'profile'))
    
    def test_register_view_post_password_mismatch(self):
        """Test registration with mismatched passwords"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'differentpassword123'
        })
        self.assertEqual(response.status_code, 200)  # Stay on registration page
        self.assertContains(response, 'Registration failed')
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_register_view_post_duplicate_username(self):
        """Test registration with existing username"""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',  # Already exists
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 200)  # Stay on registration page
        self.assertContains(response, 'Registration failed')
    
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication"""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('login', response.url)
    
    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile Information')
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
    
    def test_profile_creation_signal(self):
        """Test profile is automatically created when user is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, Profile)
    
    def test_profile_str_method(self):
        """Test profile string representation"""
        profile = self.user.profile
        self.assertEqual(str(profile), 'testuser Profile')
    
    def test_profile_fields(self):
        """Test profile fields can be updated"""
        profile = self.user.profile
        profile.bio = "Test bio"
        profile.phone_number = "+1234567890"
        profile.address = "123 Test St"
        profile.save()
        
        # Refresh from database
        profile.refresh_from_db()
        
        self.assertEqual(profile.bio, "Test bio")
        self.assertEqual(profile.phone_number, "+1234567890")
        self.assertEqual(profile.address, "123 Test St")
    
    def test_profile_deletion_cascade(self):
        """Test profile is deleted when user is deleted"""
        profile_id = self.user.profile.id
        self.user.delete()
        
        # Profile should be deleted too
        with self.assertRaises(Profile.DoesNotExist):
            Profile.objects.get(id=profile_id)


class UserAPITest(TestCase):
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
    
    def test_user_list_requires_auth(self):
        """Test user list API requires authentication"""
        response = self.client.get('/api/users/users/')
        self.assertEqual(response.status_code, 401)
    
    def test_user_list_authenticated(self):
        """Test user list API for authenticated user"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get('/api/users/users/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.json())
    
    def test_user_profile_endpoint(self):
        """Test user profile API endpoint"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(f'/api/users/users/{self.user.id}/profile/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('bio', data)
        self.assertIn('phone_number', data)
        self.assertIn('address', data)
    
    def test_update_profile_endpoint(self):
        """Test updating profile via API"""
        self.client.login(username='testuser', password='testpassword123')
        
        profile_data = {
            'bio': 'Updated bio',
            'phone_number': '+9876543210',
            'address': '456 New St'
        }
        
        response = self.client.put(
            f'/api/users/users/{self.user.id}/update_profile/',
            data=profile_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Updated bio')
        self.assertEqual(self.user.profile.phone_number, '+9876543210')
        self.assertEqual(self.user.profile.address, '456 New St')
    
    def test_cannot_update_other_user_profile(self):
        """Test that users cannot update other users' profiles"""
        self.client.login(username='testuser', password='testpassword123')
        
        profile_data = {
            'bio': 'Hacked bio'
        }
        
        response = self.client.put(
            f'/api/users/users/{self.other_user.id}/update_profile/',
            data=profile_data,
            content_type='application/json'
        )
        
        # Should get 404 because viewset filters by user
        self.assertEqual(response.status_code, 404)


class SocialAuthIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='socialuser',
            email='social@example.com',
            password='socialpass123'
        )
        
        # Create a social auth entry
        self.social_auth = UserSocialAuth.objects.create(
            user=self.user,
            provider='google-oauth2',
            uid='123456789',
            extra_data={'access_token': 'fake-token'}
        )
    
    def test_profile_view_shows_social_connections(self):
        """Test profile view shows connected social accounts"""
        self.client.login(username='socialuser', password='socialpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        
        # Should show Google as connected
        self.assertContains(response, 'Google')
        self.assertContains(response, 'Connected')
    
    def test_social_auth_creates_profile(self):
        """Test that social auth creates user profile"""
        # Simulate pipeline creating user
        from users.pipeline import create_user_profile
        
        # Create a new user without profile
        new_user = User.objects.create_user(
            username='newsocialuser',
            email='newsocial@example.com'
        )
        
        # Delete auto-created profile
        if hasattr(new_user, 'profile'):
            new_user.profile.delete()
        
        # Run pipeline
        result = create_user_profile(
            backend=None,
            user=new_user,
            response={},
        )
        
        # Check profile was created
        new_user.refresh_from_db()
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertIn('profile', result)


class PasswordResetTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
    
    def test_password_reset_view(self):
        """Test password reset page loads"""
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password reset')
    
    def test_password_reset_form_submission(self):
        """Test password reset form submission"""
        response = self.client.post(reverse('password_reset'), {
            'email': 'test@example.com'
        })
        
        # Should redirect to password_reset_done
        self.assertEqual(response.status_code, 302)
        self.assertIn('password_reset/done/', response.url)
        
        # In a real test, you would check that an email was sent
        # from django.core import mail
        # self.assertEqual(len(mail.outbox), 1)
        # self.assertIn('Password reset', mail.outbox[0].subject)