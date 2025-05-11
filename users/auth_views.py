# users/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
import os
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required

class UserCreationForm(BaseUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter a strong password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
        })

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Explicitly set the authentication backend to fix the multi-backend error
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please check the form.")
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", {"form": form})

@login_required
def profile_view(request):
    # Check for social auth connections
    has_google = False
    has_facebook = False
    
    if request.user.is_authenticated:
        try:
            from social_django.models import UserSocialAuth
            # Check for Google connection
            UserSocialAuth.objects.get(user=request.user, provider='google-oauth2')
            has_google = True
        except:
            pass
            
        try:
            # Check for Facebook connection
            UserSocialAuth.objects.get(user=request.user, provider='facebook')
            has_facebook = True
        except:
            pass
    
    return render(request, "users/profile.html", {
        'has_google': has_google,
        'has_facebook': has_facebook,
    })
@login_required
def update_profile(request):
    """Update user profile information"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        bio = request.POST.get('bio')
        
        # Update user model
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        # Update profile model
        profile = user.profile
        profile.phone_number = phone_number
        profile.address = address
        profile.bio = bio
        profile.save()
        
        messages.success(request, "Profile updated successfully!")
    
    return redirect('profile')

@login_required
def update_profile_picture(request):
    """Update user profile picture"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        profile_picture = request.FILES['profile_picture']
        profile = request.user.profile
        
        # Delete old picture if exists
        if profile.profile_picture:
            if os.path.exists(profile.profile_picture.path):
                os.remove(profile.profile_picture.path)
        
        # Save new picture
        profile.profile_picture = profile_picture
        profile.save()
        
        messages.success(request, "Profile picture updated successfully!")
    
    return redirect('profile')

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        user = request.user
        
        # Check if current password is correct
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('profile')
        
        # Check if new passwords match
        if new_password1 != new_password2:
            messages.error(request, "New passwords don't match.")
            return redirect('profile')
        
        # Change password
        user.set_password(new_password1)
        user.save()
        
        # Update session so user doesn't get logged out
        update_session_auth_hash(request, user)
        
        messages.success(request, "Password changed successfully!")
    
    return redirect('profile')

@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        user = request.user
        
        # Log the user out first
        logout(request)
        
        # Delete the user
        user.delete()
        
        messages.success(request, "Your account has been permanently deleted.")
        return redirect('home')
    
    return redirect('profile')