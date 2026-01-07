from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResourceViewSet, WarehouseViewSet, StockViewSet,
    UserRequestViewSet, DistributeResourcesView, CategoryViewSet, UserViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'resources', ResourceViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'requests', UserRequestViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('distribute/', DistributeResourcesView.as_view(), name='distribute'),
]