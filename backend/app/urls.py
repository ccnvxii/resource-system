from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResourceViewSet, WarehouseViewSet, StockViewSet,
    UserRequestViewSet, DistributeResourcesView
)

# Создаем роутер и регистрируем в нем наши ViewSets
router = DefaultRouter()
router.register(r'resources', ResourceViewSet)  # /api/resources/
router.register(r'warehouses', WarehouseViewSet)  # /api/warehouses/
router.register(r'stocks', StockViewSet)  # /api/stocks/
router.register(r'requests', UserRequestViewSet)  # /api/requests/

urlpatterns = [
    # Автоматические маршруты от роутера
    path('', include(router.urls)),

    # Отдельный маршрут для запуска распределения (POST запрос)
    path('distribute/', DistributeResourcesView.as_view(), name='distribute-resources'),
]