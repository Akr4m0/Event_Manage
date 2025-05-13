# payments/urls.py - Updated version
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet
from . import payment_views

router = DefaultRouter()
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Frontend payment views
    path('create/', payment_views.create_payment, name='create_payment'),
    path('<int:payment_id>/select-method/', payment_views.select_payment_method, name='select_payment_method'),
    path('<int:payment_id>/process-offline/', payment_views.process_offline_payment, name='process_offline_payment'),
    path('<int:payment_id>/process-online/', payment_views.process_online_payment, name='process_online_payment'),
    path('<int:payment_id>/success/', payment_views.payment_success, name='payment_success'),
    path('<int:payment_id>/cancel/', payment_views.payment_cancel, name='payment_cancel'),
    path('<int:payment_id>/status/', payment_views.payment_status, name='payment_status'),
    
    # Admin views
    path('admin/list/', payment_views.admin_payment_list, name='admin_payment_list'),
    path('admin/<int:payment_id>/approve/', payment_views.admin_approve_payment, name='admin_approve_payment'),
    
    # AJAX endpoints
    path('validate-stripe/', payment_views.validate_stripe_payment, name='validate_stripe_payment'),
]