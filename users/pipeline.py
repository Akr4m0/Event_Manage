# users/pipeline.py

def create_user_profile(backend, user, response, *args, **kwargs):
    """
    Create user profile after successful social authentication if it doesn't exist.
    This function is called by python-social-auth after a user successfully
    authenticates through a social platform.
    """
    from .models import Profile
    
    # Profile should be created automatically by the signal in models.py
    # but let's make sure it exists
    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user)
    
    return {'profile': user.profile}