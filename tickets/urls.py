# tickets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, TicketTypeViewSet
from . import ticket_views

router = DefaultRouter()
router.register(r'types', TicketTypeViewSet)
router.register(r'tickets', TicketViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Frontend URLs
    path('my-tickets/', ticket_views.my_tickets, name='my_tickets'),
    path('ticket/<uuid:ticket_id>/', ticket_views.ticket_detail, name='ticket_detail'),
    path('ticket/<uuid:ticket_id>/download/', ticket_views.download_ticket, name='download_ticket'),
    path('ticket/<uuid:ticket_id>/transfer/', ticket_views.transfer_ticket, name='transfer_ticket'),
    path('check-in/<uuid:ticket_id>/', ticket_views.check_in_ticket, name='check_in_ticket'),
    path('scan/', ticket_views.scan_ticket, name='scan_ticket'),
    path('stats/<int:event_id>/', ticket_views.ticket_stats, name='ticket_stats'),
]