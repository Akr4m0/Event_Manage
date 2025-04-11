# event_management/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken import views as token_views
from rest_framework.documentation import include_docs_urls
from events.site_views import home, event_list, event_detail, my_events, create_event, edit_event
from users.auth_views import login_view, logout_view, profile_view, register_view

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Frontend views
    path('', home, name='home'),
    path('events/', event_list, name='event_list'),
    path('events/<int:event_id>/', event_detail, name='event_detail'),
    path('my-events/', my_events, name='my_events'),
    path('events/create/', create_event, name='create_event'),
    path('events/<int:event_id>/edit/', edit_event, name='edit_event'),
    
    # User authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    
    # API endpoints
    path('api/users/', include('users.urls')),
    path('api/events/', include('events.urls')),
    path('api/tickets/', include('tickets.urls')),
    path('api/payments/', include('payments.urls')),
    path('api-auth/', include('rest_framework.urls')),  # Keep only this one
    path('api-token-auth/', token_views.obtain_auth_token),
    
    # Social authentication
    path('auth/', include('social_django.urls', namespace='social')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)