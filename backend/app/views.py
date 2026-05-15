import math
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication

from .services import NovaPoshtaService, GeoFrontService
from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category,
    Unit, RequestPurpose
)
from .serializers import *
from .optimizer.distribute import calculate_distribution


# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def calculate_front_multiplier(user_lat, user_lon):
    """
    Розраховує динамічний множник пріоритету на основі живих даних DeepState.
    Використовує експоненційне затухання: чим ближче до фронту, тим вищий пріоритет.
    """
    geo_service = GeoFrontService()
    front_points = geo_service.get_front_line_points()

    if not front_points:
        return 1.0

    # Обчислюємо відстань до найближчої точки фронту (в км)
    distances = [
        math.sqrt((user_lat - fx) ** 2 + (user_lon - fy) ** 2) * 111
        for fx, fy in front_points
    ]
    min_dist = min(distances) if distances else 300

    # Множник: макс 3.0, затухає до 1.0 на великій відстані
    multiplier = 3.0 * math.exp(-min_dist / 250)
    return max(1.0, multiplier)


# --- VIEWSETS ДЛЯ ДОВІДНИКІВ ---

class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Перегляд доступних одиниць виміру (кг, шт, л)."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RequestPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """Перегляд типів призначення та їх ваг."""
    queryset = RequestPurpose.objects.all()
    serializer_class = RequestPurposeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- КЛАСИ АВТОРИЗАЦІЇ ТА КОРИСТУВАЧІВ ---

class RegisterView(APIView):
    """Реєстрація нового користувача."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Реєстрація успішна',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """Керування користувачами (тільки Admin)."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# --- КЕРУВАННЯ РЕСУРСАМИ ТА СКЛАДАМИ ---

class CategoryViewSet(viewsets.ModelViewSet):
    """Категорії ресурсів та їх критичність."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ResourceViewSet(viewsets.ModelViewSet):
    """Номенклатура ресурсів."""
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class WarehouseViewSet(viewsets.ModelViewSet):
    """Логістичні хаби та склади."""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- ОПЕРАЦІЙНА ЛОГІКА: ЗАЯВКИ ТА ЗАПАСИ ---

class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 1. Отримуємо дані з запиту
        warehouse_ref = self.request.data.get('warehouse_ref')

        lat, lon = None, None
        if warehouse_ref:
            np_service = NovaPoshtaService(api_key=settings.NOVA_POSHTA_API_KEY)
            lat, lon = np_service.get_warehouse_coordinates(warehouse_ref)

        if not self.request.user.is_staff:
            serializer.save(
                user=self.request.user,
                latitude=lat,
                longitude=lon
            )
        else:
            user_id = self.request.data.get('user')
            serializer.save(
                user_id=user_id if user_id else self.request.user.id,
                latitude=lat,
                longitude=lon
            )


class StockViewSet(viewsets.ModelViewSet):
    """Облік запасів на складах."""
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['patch'])
    def update_amount(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Доступ заборонено"}, status=status.HTTP_403_FORBIDDEN)
        stock = self.get_object()
        try:
            stock.amount = Decimal(str(request.data.get('amount')))
            stock.save()
            return Response({"status": "success", "new_amount": stock.amount})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def add_resource(self, request):
        """Реєстрація поставки на склад (викликається з StockInForm.js)"""
        if not request.user.is_staff:
            return Response({"error": "Тільки адміністратор може поповнювати склад"}, status=403)

        warehouse_id = request.data.get('warehouse')
        resource_id = request.data.get('resource')
        amount_to_add = request.data.get('amount')

        if not all([warehouse_id, resource_id, amount_to_add]):
            return Response({"error": "Неповні дані для поповнення"}, status=400)

        try:
            with transaction.atomic():
                amount_decimal = Decimal(str(amount_to_add))
                # Отримуємо існуючий запис або створюємо новий
                stock, created = Stock.objects.get_or_create(
                    warehouse_id=warehouse_id,
                    resource_id=resource_id,
                    defaults={'amount': 0}
                )
                stock.amount += amount_decimal
                stock.save()

                return Response({
                    "status": "success",
                    "message": f"Додано {amount_decimal} до складу {stock.warehouse.name}"
                })
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# --- API ДЛЯ АЛГОРИТМУ ОПТИМІЗАЦІЇ ---

class DistributeResourcesView(APIView):
    def post(self, request):
        with transaction.atomic():
            active_requests_qs = UserRequest.objects.exclude(status='done').select_for_update()
            stocks_qs = Stock.objects.filter(amount__gt=0).select_for_update()

            requests_data = []
            for r in active_requests_qs:
                needed = float(r.quantity_requested - r.quantity_allocated)
                if needed > 0:
                    requests_data.append({
                        'id': r.id, 'resource_id': r.resource_id,
                        'amount_needed': needed, 'priority': float(r.priority)
                    })

            stocks_data = [{'warehouse_id': s.warehouse_id, 'resource_id': s.resource_id, 'amount': float(s.amount)} for
                           s in stocks_qs]
            plan_items_data = calculate_distribution(requests_data, stocks_data)

            if not plan_items_data: return Response({"message": "No combinations"}, status=200)

            new_plan = DistributionPlan.objects.create()
            items_to_create = []
            req_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_dec = Decimal(str(item['amount']))
                req = req_map.get(item['request_id'])
                if not req: continue
                items_to_create.append(
                    DistributionItem(plan=new_plan, request=req, warehouse_id=item['warehouse_id'], amount=amount_dec))
                req.quantity_allocated += amount_dec
                req.status = 'done' if req.quantity_allocated >= (
                            req.quantity_requested - Decimal('0.001')) else 'partial'
                req.save()
                stock = Stock.objects.get(warehouse_id=item['warehouse_id'], resource_id=req.resource_id)
                stock.amount -= amount_dec
                stock.save()

            DistributionItem.objects.bulk_create(items_to_create)
            return Response(DistributionPlanSerializer(new_plan).data, status=201)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Історія розподілів."""
    queryset = DistributionItem.objects.select_related(
        'request__user', 'request__resource', 'warehouse', 'plan'
    ).all().order_by('-plan__created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]


# --- NOVA POSHTA PROXY ---

class NovaPoshtaProxyView(APIView):
    """Проксі для API Нової Пошти."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        np_service = NovaPoshtaService(api_key=settings.NOVA_POSHTA_API_KEY)
        action = request.data.get("action")

        if action == "get_cities":
            res = np_service.get_cities(request.data.get("search", ""))
            return Response(res['data'][0].get('Addresses', []) if res.get('success') else [])

        if action == "get_warehouses":
            res = np_service.get_warehouses(request.data.get("city_ref"))
            return Response(res.get('data', []) if res.get('success') else [])

        if action == "get_streets":
            res = np_service.get_streets(request.data.get("city_ref"), request.data.get("search", ""))
            return Response(res['data'][0].get('Addresses', []) if res.get('success') else [])

        return Response({"error": "Invalid action"}, status=400)
