from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.decorators import action
from rest_framework import permissions

from .models import Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem, Category
from .serializers import (
    ResourceSerializer, WarehouseSerializer, StockSerializer,
    UserRequestSerializer, DistributionPlanSerializer, CategorySerializer,
    UserSerializer
)
from .optimizer.distribute import calculate_distribution


class StockViewSet(viewsets.ModelViewSet):
    # Тільки адміни можуть редагувати склад
    def get_permissions(self):
        if self.action in ['update_amount', 'add_resource', 'create', 'update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

class DistributeResourcesView(APIView):
    # Тільки адмін може запускати алгоритм розподілу
    permission_classes = [permissions.IsAdminUser]

# --- ViewSets (CRUD для API) ---
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer


class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.filter(amount__gt=0)  # показуємо лише ті ресурси, яких більше 0
    serializer_class = StockSerializer

    # Додаємо метод для швидкого редагування (PATCH запит)
    @action(detail=True, methods=['patch'])
    def update_amount(self, request, pk=None):
        stock = self.get_object()
        new_amount = request.data.get('amount')

        try:
            stock.amount = Decimal(str(new_amount))
            stock.save()
            return Response({"status": "success", "new_amount": stock.amount})
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    # Цей метод оброблятиме POST запит на /api/stocks/add_resource/
    @action(detail=False, methods=['post'])
    def add_resource(self, request):
        warehouse_id = request.data.get('warehouse')
        resource_id = request.data.get('resource')
        amount_to_add = request.data.get('amount')

        if not all([warehouse_id, resource_id, amount_to_add]):
            return Response({"error": "Необхідно вказати склад, ресурс та кількість"}, status=400)

        try:
            amount_decimal = Decimal(str(amount_to_add))

            # get_or_create знайде існуючий запис або створить новий, якщо такого ресурсу ще немає на складі
            stock, created = Stock.objects.get_or_create(
                warehouse_id=warehouse_id,
                resource_id=resource_id,
                defaults={'amount': 0}
            )

            stock.amount += amount_decimal
            stock.save()

            return Response({
                "status": "success",
                "message": f"Додано {amount_decimal}. Новий залишок: {stock.amount}",
                "warehouse": stock.warehouse.name,
                "resource": stock.resource.name
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)



# --- Головна логіка розподілу (Алгоритм) ---

class DistributeResourcesView(APIView):
    def get(self, request):
        return Response({
            "info": "Ендпоінт розподілу ресурсів",
            "instruction": "Натисніть POST для запуску алгоритму.",
            "method": "POST only"
        })

    def post(self, request):
        with transaction.atomic():
            # 1. ПІДГОТОВКА ДАНИХ
            active_requests_qs = UserRequest.objects.exclude(status='done')
            # Беремо тільки ті запаси, де щось є (>0)
            stocks_qs = Stock.objects.filter(amount__gt=0)

            requests_data = []
            for r in active_requests_qs:
                needed = float(r.quantity_requested - r.quantity_allocated)
                if needed > 0:
                    requests_data.append({
                        'id': r.id,
                        'resource_id': r.resource_id,
                        'amount_needed': needed,
                        'priority': r.priority
                    })

            stocks_data = [
                {
                    'warehouse_id': s.warehouse_id,
                    'resource_id': s.resource_id,
                    'amount': float(s.amount)
                }
                for s in stocks_qs
            ]

            # 2. ЗАПУСК АЛГОРИТМУ
            plan_items_data = calculate_distribution(requests_data, stocks_data)

            if not plan_items_data:
                return Response({"message": "Немає доступних ресурсів для розподілу."}, status=200)

            # 3. ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТУ
            new_plan = DistributionPlan.objects.create()
            items_to_create = []

            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_decimal = Decimal(str(item['amount']))
                req = requests_map[item['request_id']]

                # А) Створюємо запис про трансфер
                items_to_create.append(DistributionItem(
                    plan=new_plan,
                    request=req,
                    warehouse_id=item['warehouse_id'],
                    amount=amount_decimal
                ))

                # Б) Оновлюємо статус заявки
                req.quantity_allocated += amount_decimal

                # Допускаємо похибку 0.01 для float обчислень
                if req.quantity_allocated >= req.quantity_requested - Decimal('0.01'):
                    req.status = 'done'
                    req.quantity_allocated = req.quantity_requested  # Щоб не було 99.999
                else:
                    req.status = 'partial'

                req.save()

                # --- В) СПИСАННЯ ЗІ СКЛАДУ (НОВЕ!) ---
                try:
                    # Знаходимо конкретний запас на складі
                    stock = Stock.objects.select_for_update().get(
                        warehouse_id=item['warehouse_id'],
                        resource_id=req.resource_id
                    )
                    stock.amount -= amount_decimal

                    # Захист від мінусових значень (про всяк випадок)
                    if stock.amount < 0:
                        stock.amount = 0

                    stock.save()
                except Stock.DoesNotExist:
                    # Цього не має статися, якщо алгоритм працює правильно
                    pass

            # Зберігаємо всі трансфери одним запитом
            DistributionItem.objects.bulk_create(items_to_create)

            # 4. ВІДПОВІДЬ
            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=201)
