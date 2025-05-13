# event_management/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken import views as token_views
from django.contrib.auth import views as auth_views
from events.site_views import home, event_list, event_detail, my_events, create_event, edit_event, cancel_event
from users.auth_views import login_view, logout_view, profile_view, register_view
from tickets import ticket_views

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
    path('events/<int:event_id>/cancel/', cancel_event, name='cancel_event'),  # Add this line
    
    # User authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    
    # Ticket views
    path('my-tickets/', ticket_views.my_tickets, name='my_tickets'),
    path('ticket/<uuid:ticket_id>/', ticket_views.ticket_detail, name='ticket_detail'),
    path('ticket/<uuid:ticket_id>/download/', ticket_views.download_ticket, name='download_ticket'),
    path('ticket/<uuid:ticket_id>/transfer/', ticket_views.transfer_ticket, name='transfer_ticket'),
    path('ticket/check-in/<uuid:ticket_id>/', ticket_views.check_in_ticket, name='check_in_ticket'),
    path('ticket/scan/', ticket_views.scan_ticket, name='scan_ticket'),
    path('ticket/stats/<int:event_id>/', ticket_views.ticket_stats, name='ticket_stats'),
    
    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Payment URLs - include all payment routes
    path('payments/', include('payments.urls')),
    
    # API endpoints
    path('api/users/', include('users.urls')),
    path('api/events/', include('events.urls')),
    path('api/tickets/', include('tickets.urls')),
    path('api/payments/', include('payments.urls')),  # Add API payments route
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', token_views.obtain_auth_token),
    
    # Social authentication
    path('auth/', include('social_django.urls', namespace='social')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)