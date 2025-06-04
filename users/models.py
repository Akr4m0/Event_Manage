# users/models.py
# users/models.py - Update with UserRole model
from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics', blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

class UserRole(models.Model):
    """Model to define different user roles in the system"""
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('event_manager', 'Event Manager'),
        ('host', 'Event Host'),
        ('buyer', 'Ticket Buyer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer')
    is_approved = models.BooleanField(default=False, 
                                     help_text="Approval status for event creation permissions")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                   null=True, blank=True, 
                                   related_name='approved_users')
    approval_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def save(self, *args, **kwargs):
        # Create/update the user role
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Assign user to the appropriate group based on role
        if is_new or self._role_changed():
            self._update_user_groups()
    
    def _role_changed(self):
        """Check if role has changed by comparing with DB state"""
        if self.pk:
            old_instance = UserRole.objects.get(pk=self.pk)
            return old_instance.role != self.role
        return False
    
    def _update_user_groups(self):
        """Update user group membership based on role"""
        # Remove user from all role groups
        role_groups = Group.objects.filter(name__in=[r[0] for r in self.ROLE_CHOICES])
        self.user.groups.remove(*role_groups)
        
        # Add user to the appropriate group based on their role
        group, created = Group.objects.get_or_create(name=self.role)
        self.user.groups.add(group)
        
        # If user is admin, add to admin group
        if self.role == 'admin':
            self.user.is_staff = True
            self.user.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        
        # Also create a default role for the user
        UserRole.objects.create(user=instance, role='buyer')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()