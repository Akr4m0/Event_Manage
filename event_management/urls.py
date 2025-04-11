# event_management/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken import views as token_views
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

# Create a router for the API root view
router = DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),  # This will create a root API view
    path('api/users/', include('users.urls')),
    path('api/events/', include('events.urls')),
    path('api/tickets/', include('tickets.urls')),
    path('api/payments/', include('payments.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', token_views.obtain_auth_token),
    path('auth/', include('social_django.urls', namespace='social')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)