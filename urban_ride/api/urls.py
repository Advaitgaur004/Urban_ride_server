from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserViewSet, SlotViewSet, AutoQueueViewSet, PaymentViewSet,
    SlotParticipantCreateView, SlotCreateView, AutoDriverAcceptView,
    AutoCreateView, AutoViewSet
)
from .auth_views import request_otp, verify_otp

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'auto-queue', AutoQueueViewSet, basename='autoqueue')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('autos/create/', AutoCreateView.as_view(), name='auto-create'),
    path('autos/', AutoViewSet.as_view({'get': 'list'}), name='auto-list'),
    path('slots/', SlotViewSet.as_view({'get': 'list'}), name='slot-list'),
    path('slots/<int:pk>/', SlotViewSet.as_view({'get': 'retrieve'}), name='slot-detail'),
    path('slots/create/', SlotCreateView.as_view(), name='slot-create'),
    path('slots/<int:pk>/accept/', AutoDriverAcceptView.as_view(), name='slot-accept'),
    path('slots/<int:pk>/join/', SlotParticipantCreateView.as_view(), name='slot-join'),
    path('auth/request-otp/', request_otp, name='request-otp'),
    path('auth/verify-otp/', verify_otp, name='verify-otp'),
]
