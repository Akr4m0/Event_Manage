# tickets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, TicketTypeViewSet

router = DefaultRouter()
router.register(r'types', TicketTypeViewSet)
router.register(r'tickets', TicketViewSet)

urlpatterns = [
    path('', include(router.urls)),
]