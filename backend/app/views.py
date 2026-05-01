from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from decimal import Decimal
from django.contrib.auth.models import User

from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category,
    Unit, RequestPurpose
)
from .serializers import *
from .optimizer.distribute import calculate_distribution


# --- НОВІ VIEWSETS ДЛЯ ДОВІДНИКІВ  ---

class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Перегляд доступних одиниць виміру (кг, шт, л)."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RequestPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """Перегляд типів призначення (Військові, Медицина тощо) та їх ваг."""
    queryset = RequestPurpose.objects.all()
    serializer_class = RequestPurposeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- КЛАСИ АВТОРИЗАЦІЇ ТА КОРИСТУВАЧІВ ---

class RegisterView(APIView):
    """Реєстрація нового користувача з автоматичним створенням профілю."""
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
    """Керування користувачами (тільки для адмінів)."""
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
    """Номенклатура ресурсів. Створення/зміна тільки для адмінів."""
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class WarehouseViewSet(viewsets.ModelViewSet):
    """Інформація про логістичні хаби та склади."""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- ОПЕРАЦІЙНА ЛОГІКА: ЗАЯВКИ ТА ЗАПАСИ ---

class UserRequestViewSet(viewsets.ModelViewSet):
    """Керування заявками. Пріоритет розраховується автоматично в моделі."""
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(user=self.request.user)
        else:
            user_id = self.request.data.get('user')
            if user_id:
                serializer.save()
            else:
                serializer.save(user=self.request.user)


class StockViewSet(viewsets.ModelViewSet):
    """Облік запасів на складах."""
    queryset = Stock.objects.filter(amount__gt=0)
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['patch'])
    def update_amount(self, request, pk=None):
        """Ручне коригування (тільки адмін)."""
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
        """Реєстрація поставки на склад."""
        if not request.user.is_staff:
            return Response({"error": "Тільки адміністратор може реєструвати поставки"}, status=403)

        warehouse_id = request.data.get('warehouse')
        resource_id = request.data.get('resource')
        amount_to_add = request.data.get('amount')

        if not all([warehouse_id, resource_id, amount_to_add]):
            return Response({"error": "Вкажіть склад, ресурс та кількість"}, status=400)

        try:
            amount_decimal = Decimal(str(amount_to_add))
            stock, created = Stock.objects.get_or_create(
                warehouse_id=warehouse_id,
                resource_id=resource_id,
                defaults={'amount': 0}
            )
            stock.amount += amount_decimal
            stock.save()
            return Response({
                "status": "success",
                "message": f"Додано {amount_decimal}. Склад: {stock.warehouse.name}",
                "resource": stock.resource.name
            })
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# --- API ДЛЯ АЛГОРИТМУ ОПТИМІЗАЦІЇ ---

class DistributeResourcesView(APIView):
    """Запуск алгоритму справедливого розподілу ресурсів за пріоритетами."""
    permission_classes = [permissions.IsAdminUser]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        with transaction.atomic():
            active_requests_qs = UserRequest.objects.exclude(status='done').select_for_update()
            stocks_qs = Stock.objects.filter(amount__gt=0).select_for_update()

            requests_data = []
            for r in active_requests_qs:
                needed = float(r.quantity_requested - r.quantity_allocated)
                if needed > 0:
                    requests_data.append({
                        'id': r.id,
                        'resource_id': r.resource_id,
                        'amount_needed': needed,
                        'priority': float(r.priority)
                    })

            stocks_data = [
                {'warehouse_id': s.warehouse_id, 'resource_id': s.resource_id, 'amount': float(s.amount)}
                for s in stocks_qs
            ]

            plan_items_data = calculate_distribution(requests_data, stocks_data)

            if not plan_items_data:
                return Response({"message": "Немає доступних комбінацій для розподілу."}, status=200)

            new_plan = DistributionPlan.objects.create()
            items_to_create = []
            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_dec = Decimal(str(item['amount']))
                req = requests_map.get(item['request_id'])
                if not req: continue

                items_to_create.append(DistributionItem(
                    plan=new_plan,
                    request=req,
                    warehouse_id=item['warehouse_id'],
                    amount=amount_dec
                ))

                req.quantity_allocated += amount_dec
                is_done = req.quantity_allocated >= req.quantity_requested - Decimal('0.001')
                req.status = 'done' if is_done else 'partial'
                req.save()

                stock = Stock.objects.get(warehouse_id=item['warehouse_id'], resource_id=req.resource_id)
                stock.amount -= amount_dec
                stock.save()

            DistributionItem.objects.bulk_create(items_to_create)
            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
