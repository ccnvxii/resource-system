from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal

# Імпорт моделей та серіалайзерів
from .models import Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem, Category
from .serializers import (
    ResourceSerializer, WarehouseSerializer, StockSerializer,
    UserRequestSerializer, DistributionPlanSerializer, CategorySerializer
)
# Імпорт алгоритму
from .optimizer.distribute import calculate_distribution


# --- CRUD ViewSets ---

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


# --- Головна логіка розподілу ---

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
            # Беремо тільки активні заявки
            active_requests_qs = UserRequest.objects.exclude(status='done')
            # Беремо склади, де є запаси
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
                return Response({"message": "Немає доступних ресурсів або заявок."}, status=200)

            # 3. ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТУ
            new_plan = DistributionPlan.objects.create()
            items_to_create = []

            # Кешуємо заявки
            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_decimal = Decimal(str(item['amount']))
                req = requests_map[item['request_id']]

                # Створення запису в БД
                items_to_create.append(DistributionItem(
                    plan=new_plan,
                    request=req,
                    warehouse_id=item['warehouse_id'],
                    # resource_id БІЛЬШЕ НЕМАЄ ТУТ (3NF: ми беремо ресурс із заявки)
                    amount=amount_decimal
                ))

                # Оновлення статусу заявки
                req.quantity_allocated += amount_decimal

                # Оновлення статусу (враховуємо дрібні похибки float)
                if req.quantity_allocated >= req.quantity_requested - Decimal('0.01'):
                    req.status = 'done'
                else:
                    req.status = 'partial'

                req.save()

            # Масове створення записів (швидше, ніж по одному)
            DistributionItem.objects.bulk_create(items_to_create)

            # 4. ВІДПОВІДЬ
            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=201)