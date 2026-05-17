import math
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .services import NovaPoshtaService
from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category,
    Unit, RequestPurpose
)
from .serializers import *
from .optimizer.distribute import calculate_distribution

# Імпортуємо функцію розрахунку з утиліт, уникаючи циклічного імпорту
from .utils import calculate_front_multiplier


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
        warehouse_ref = self.request.data.get('warehouse_ref')

        lat, lon = None, None
        # Якщо обрано відділення НП — тягнемо його координати через сервіс
        if warehouse_ref and warehouse_ref != 'ADDRESS_DELIVERY':
            np_service = NovaPoshtaService(api_key=settings.NOVA_POSHTA_API_KEY)
            lat, lon = np_service.get_warehouse_coordinates(warehouse_ref)
        else:
            # Для адресної доставки забираємо прямі гео-координати міста, які прийшли з фронтенду
            try:
                lat = float(self.request.data.get('latitude')) if self.request.data.get('latitude') else None
                lon = float(self.request.data.get('longitude')) if self.request.data.get('longitude') else None
            except (ValueError, TypeError):
                lat, lon = None, None

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
            stock.amount = int(request.data.get('amount'))
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
                amount_int = int(amount_to_add)
                stock, created = Stock.objects.get_or_create(
                    warehouse_id=warehouse_id,
                    resource_id=resource_id,
                    defaults={'amount': 0}
                )
                stock.amount += amount_int
                stock.save()

                return Response({
                    "status": "success",
                    "message": f"Додано {amount_int} до складу {stock.warehouse.name}"
                })
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# --- API ДЛЯ АЛГОРИТМУ ОПТИМІЗАЦІЇ ---

class DistributeResourcesView(APIView):
    def post(self, request):
        try:
            with transaction.atomic():
                # Блокуємо рядки від дедлоків, пропускаючи заблоковані паралельними сесіями адмінки
                active_requests_qs = UserRequest.objects.exclude(status='done').select_for_update(skip_locked=True)
                stocks_qs = Stock.objects.filter(amount__gt=0).select_for_update(skip_locked=True)

                # Збір потреб із прокиданням широти та довготи отримувача (lat/lng)
                requests_data = []
                for r in active_requests_qs:
                    needed = int(r.quantity_requested - r.quantity_allocated)
                    if needed > 0:
                        requests_data.append({
                            'id': r.id,
                            'resource_id': r.resource_id,
                            'amount_needed': needed,
                            'priority': float(r.priority),
                            'lat': float(r.latitude) if r.latitude else None,
                            'lng': float(r.longitude) if r.longitude else None
                        })

                # Збір залишків складів із прокиданням широти та довготи хабу (lat/lng)
                stocks_data = []
                for s in stocks_qs:
                    stocks_data.append({
                        'warehouse_id': s.warehouse_id,
                        'resource_id': s.resource_id,
                        'amount': int(s.amount),
                        'lat': float(s.warehouse.latitude) if s.warehouse.latitude else None,
                        'lng': float(s.warehouse.longitude) if s.warehouse.longitude else None
                    })

                # Виклик покращеного алгоритму оптимізації розподілу (Географія + Справедливість)
                plan_items_data = calculate_distribution(requests_data, stocks_data)

                if not plan_items_data:
                    return Response({"message": "Немає доступних комбінацій для розподілу ресурсів"}, status=200)

                new_plan = DistributionPlan.objects.create()
                items_to_create = []
                req_map = {req.id: req for req in active_requests_qs}

                # Захисний лімітатор ітерацій для запобігання Infinite Loop через округлення
                max_iterations = 5000
                iteration = 0

                for item in plan_items_data:
                    iteration += 1
                    if iteration > max_iterations:
                        print("🚨 Захисний лімітатор: виявлено ризик зациклення при імпорті елементів плану!")
                        break

                    amount_int = int(item['amount'])
                    if amount_int <= 0:
                        continue

                    req = req_map.get(item['request_id'])
                    if not req:
                        continue

                    # Створюємо операцію розподілу. Поля координат у плані за бажанням пишуться
                    # у логи або використовуються безпосередньо у відповіді серіалізатора
                    items_to_create.append(
                        DistributionItem(
                            plan=new_plan,
                            request=req,
                            warehouse_id=item['warehouse_id'],
                            amount=amount_int
                        )
                    )

                    req.quantity_allocated += amount_int
                    req.status = 'done' if req.quantity_allocated >= req.quantity_requested else 'partial'
                    req.save()

                    stock = Stock.objects.get(warehouse_id=item['warehouse_id'], resource_id=req.resource_id)
                    stock.amount -= amount_int
                    stock.save()

                DistributionItem.objects.bulk_create(items_to_create)
                return Response(DistributionPlanSerializer(new_plan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Критична помилка блокування або розрахунку: {e}")
            return Response({"error": "База даних тимчасово зайнята обробкою операцій. Спробуйте ще раз."},
                            status=status.HTTP_423_LOCKED)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Історія розподілів для панелі адміністратора."""
    queryset = DistributionItem.objects.select_related(
        'request__user', 'request__resource', 'warehouse', 'plan'
    ).all().order_by('-plan__created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]


# --- NOVA POSHTA PROXY ---

class NovaPoshtaProxyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        np = NovaPoshtaService(settings.NOVA_POSHTA_API_KEY)
        action = request.data.get("action")

        # 1. ОБРОБКА МІСТ
        if action == "get_cities":
            res = np.get_cities(request.data.get("search", ""))
            settlements = (
                res.get("data", []) and res["data"][0].get("Addresses", [])
            ) or []
            return Response(settlements)

        # 2. ОБРОБКА ВІДДІЛЕНЬ
        if action == "get_warehouses":
            res = np.get_warehouses(request.data.get("city_ref"))
            return Response(res.get("data", []))

        # 3. ОБРОБКА ВУЛИЦЬ
        if action == "get_streets":
            city_ref = request.data.get("city_ref")
            res = np.get_streets(
                city_ref,
                request.data.get("search", "")
            )
            raw_data = res.get("data", [])
            streets_list = []

            if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
                if "AddressesList" in raw_data[0]:
                    streets_list = raw_data[0].get("AddressesList", [])
                elif "Addresses" in raw_data[0]:
                    streets_list = raw_data[0].get("Addresses", [])
                else:
                    streets_list = raw_data

            final_streets = []
            for s in streets_list:
                if isinstance(s, dict):
                    desc = s.get("Description") or s.get("Presentation") or s.get("SettlementStreetDescription")
                    if desc:
                        s["Description"] = desc
                        final_streets.append(s)

            return Response(final_streets)

        return Response({"error": "Invalid action"}, status=400)