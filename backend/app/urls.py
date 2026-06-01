from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResourceViewSet, WarehouseViewSet, StockViewSet,
    UserRequestViewSet, DistributeResourcesView, CategoryViewSet, UserViewSet, RegisterView, UnitViewSet,
    RequestPurposeViewSet, AuditLogViewSet, NovaPoshtaProxyView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'resources', ResourceViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'requests', UserRequestViewSet)
router.register(r'users', UserViewSet)
router.register(r'units', UnitViewSet)
router.register(r'purposes', RequestPurposeViewSet)
router.register(r'logs', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    path('', include(router.urls)),
    path('distribute/', DistributeResourcesView.as_view(), name='distribute'),

    path('register/', RegisterView.as_view(), name='register'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('novaposhta/', NovaPoshtaProxyView.as_view(), name='novaposhta-proxy'),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
