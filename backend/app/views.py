import math
import time
import requests
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .services import NovaPoshtaService
from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category,
    Unit, RequestPurpose
)
from .serializers import *
from .optimizer.distribute import calculate_distribution, calculate_strict_priority


# --- КАСТОМНА АВТОРИЗАЦІЯ З ПЕРЕВІРКОЮ ПІДТВЕРДЖЕННЯ АДМІНІСТРАТОРОМ ---

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if not user.is_staff:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'is_approved': False}
            )

            if not profile.is_approved:
                # Передаємо і текст, і унікальний код помилки
                raise AuthenticationFailed({
                    "detail": "Ваш обліковий запис ще не підтверджено адміністратором.",
                    "code": "not_approved"
                })

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# --- VIEWSETS ДЛЯ ДОВІДНИКІВ ---

class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RequestPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequestPurpose.objects.all()
    serializer_class = RequestPurposeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- КЛАСИ АВТОРИЗАЦІЇ ТА КОРИСТУВАЧІВ ---

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {'message': 'Реєстрація успішна. Очікуйте підтвердження адміністратора.', 'user_id': user.id},
                status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# --- КЕРУВАННЯ РЕСУРСАМИ ТА СКЛАДАМИ ---

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- ОПЕРАЦІЙНА ЛОГІКА ---

class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        warehouse_ref = self.request.data.get('warehouse_ref')
        auto_extend_val = self.request.data.get('auto_extend', True)

        lat, lon = None, None
        if warehouse_ref and warehouse_ref != 'ADDRESS_DELIVERY':
            np_service = NovaPoshtaService(api_key=settings.NOVA_POSHTA_API_KEY)
            lat, lon = np_service.get_warehouse_coordinates(warehouse_ref)
        else:
            try:
                lat = float(self.request.data.get('latitude')) if self.request.data.get('latitude') else None
                lon = float(self.request.data.get('longitude')) if self.request.data.get('longitude') else None
            except (ValueError, TypeError):
                lat, lon = None, None

        save_kwargs = {
            'latitude': lat,
            'longitude': lon,
            'auto_extend': auto_extend_val
        }

        if self.request.data.get('due_date'):
            save_kwargs['due_date'] = self.request.data.get('due_date')

        if not self.request.user.is_staff:
            save_kwargs['user'] = self.request.user
            serializer.save(**save_kwargs)
        else:
            user_id = self.request.data.get('user')
            save_kwargs['user_id'] = user_id if user_id else self.request.user.id
            serializer.save(**save_kwargs)


class StockViewSet(viewsets.ModelViewSet):
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
                today = timezone.now().date()

                expired_requests = UserRequest.objects.filter(
                    status__in=['new', 'partial'],
                    due_date__lt=today
                )

                expired_requests.filter(auto_extend=False).update(status='expired')

                for req in expired_requests.filter(auto_extend=True):
                    req.due_date = today + timedelta(days=5)
                    req.extension_count += 1
                    req.save()

                active_requests_qs = UserRequest.objects.exclude(
                    status__in=['done', 'expired']
                ).select_related('resource').select_for_update(skip_locked=True)

                stocks_qs = Stock.objects.filter(amount__gt=0).select_related('warehouse').select_for_update(
                    skip_locked=True)

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

                stocks_data = []
                for s in stocks_qs:
                    stocks_data.append({
                        'warehouse_id': s.warehouse_id,
                        'resource_id': s.resource_id,
                        'amount': int(s.amount),
                        'lat': float(s.warehouse.latitude) if s.warehouse.latitude else None,
                        'lng': float(s.warehouse.longitude) if s.warehouse.longitude else None
                    })

                strategy = request.data.get('strategy', 'fairness')

                if strategy == 'triage':
                    plan_items_data = calculate_strict_priority(requests_data, stocks_data)
                else:
                    plan_items_data = calculate_distribution(requests_data, stocks_data)

                if not plan_items_data:
                    return Response({"message": "Немає доступних комбінацій для розподілу ресурсів"}, status=200)

                new_plan = DistributionPlan.objects.create()

                req_map = {req.id: req for req in active_requests_qs}
                stock_map = {(s.warehouse_id, s.resource_id): s for s in stocks_qs}

                items_to_create = []
                requests_to_update = set()
                stocks_to_update = set()

                for item in plan_items_data:
                    amount_int = int(item['amount'])
                    if amount_int <= 0:
                        continue

                    req = req_map.get(item['request_id'])
                    if not req:
                        continue

                    stock = stock_map.get((item['warehouse_id'], req.resource_id))
                    if not stock:
                        continue

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
                    requests_to_update.add(req)

                    stock.amount -= amount_int
                    stocks_to_update.add(stock)

                DistributionItem.objects.bulk_create(items_to_create)

                if requests_to_update:
                    UserRequest.objects.bulk_update(list(requests_to_update),
                                                    ['quantity_allocated', 'status', 'due_date', 'extension_count'])

                if stocks_to_update:
                    Stock.objects.bulk_update(list(stocks_to_update), ['amount'])

                return Response(DistributionPlanSerializer(new_plan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Критична помилка розрахунку: {e}")
            return Response({"error": "База даних тимчасово зайнята. Спробуйте ще раз."}, status=status.HTTP_423_LOCKED)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
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

        if action == "get_cities":
            res = np.get_cities(request.data.get("search", ""))
            settlements = (res.get("data", []) and res["data"][0].get("Addresses", [])) or []
            return Response(settlements)

        if action == "get_warehouses":
            res = np.get_warehouses(request.data.get("city_ref"))
            return Response(res.get("data", []))

        if action == "get_streets":
            city_ref = request.data.get("city_ref")
            res = np.get_streets(city_ref, request.data.get("search", ""))
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