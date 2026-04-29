from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.contrib.auth.models import User
from decimal import Decimal

# Імпорт моделей та серіалізаторів
from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category
)
from .serializers import (
    ResourceSerializer, WarehouseSerializer, StockSerializer,
    UserRequestSerializer, DistributionPlanSerializer, CategorySerializer,
    UserSerializer
)
# Імпорт вашого алгоритму
from .optimizer.distribute import calculate_distribution


# --- 1. ViewSets для стандартних операцій (CRUD) ---

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.AllowAny]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управління запасами.
    Фільтрує тільки позитивні залишки для відображення.
    """
    queryset = Stock.objects.filter(amount__gt=0)
    serializer_class = StockSerializer

    def get_permissions(self):
        if self.action in ['update_amount', 'add_resource', 'create', 'update', 'destroy']:
            return [permissions.AllowAny()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['patch'])
    def update_amount(self, request, pk=None):
        stock = self.get_object()
        try:
            stock.amount = Decimal(str(request.data.get('amount')))
            stock.save()
            return Response({"status": "success", "new_amount": stock.amount})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def add_resource(self, request):
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


# --- 2. Головна логіка розподілу (API View) ---

class DistributeResourcesView(APIView):
    permission_classes = [permissions.AllowAny] #IsAdminUser

    def get(self, request):
        return Response({"message": "Використовуйте POST для запуску розподілу."})

    def post(self, request):
        with transaction.atomic():
            # 1. ПІДГОТОВКА ДАНИХ
            # Шукаємо тільки заявки, що не виконані (new, partial)
            active_requests_qs = UserRequest.objects.exclude(status='done')
            stocks_qs = Stock.objects.filter(amount__gt=0)

            # --- ДЕБАГ ЛОГУВАННЯ (Дивіться в консоль Docker) ---
            print(f"\n--- [OPTIMIZER START] ---")
            print(f"Активних заявок у базі: {active_requests_qs.count()}")
            print(f"Записів запасів у базі: {stocks_qs.count()}")

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
                {
                    'warehouse_id': s.warehouse_id,
                    'resource_id': s.resource_id,
                    'amount': float(s.amount)
                }
                for s in stocks_qs
            ]

            # Перевірка наявності спільних ресурсів
            req_ids = set(r['resource_id'] for r in requests_data)
            stk_ids = set(s['resource_id'] for s in stocks_data)
            common = req_ids.intersection(stk_ids)
            print(f"Спільні ID ресурсів для розподілу: {common}")

            if not common:
                return Response({"message": "Не знайдено спільних ресурсів між складом та заявками."}, status=200)

            # 2. ЗАПУСК АЛГОРИТМУ
            plan_items_data = calculate_distribution(requests_data, stocks_data)

            if not plan_items_data:
                print("АЛГОРИТМ: Результат порожній.")
                return Response({"message": "Ресурси не розподілено (алгоритм не знайшов розв'язку)."}, status=200)

            # 3. ФІКСАЦІЯ РЕЗУЛЬТАТІВ У БАЗІ
            new_plan = DistributionPlan.objects.create()
            items_to_create = []
            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_dec = Decimal(str(item['amount']))
                req = requests_map.get(item['request_id'])

                if not req: continue

                # Створення елемента плану
                items_to_create.append(DistributionItem(
                    plan=new_plan,
                    request=req,
                    warehouse_id=item['warehouse_id'],
                    amount=amount_dec
                ))

                # Оновлення заявки
                req.quantity_allocated += amount_dec
                if req.quantity_allocated >= req.quantity_requested - Decimal('0.01'):
                    req.status = 'done'
                else:
                    req.status = 'partial'
                req.save()

                # Списання зі складу
                stock = Stock.objects.select_for_update().get(
                    warehouse_id=item['warehouse_id'],
                    resource_id=req.resource_id
                )
                stock.amount -= amount_dec
                if stock.amount < 0: stock.amount = 0
                stock.save()

            DistributionItem.objects.bulk_create(items_to_create)

            print(f"Успішно створено {len(items_to_create)} трансферів.")
            print(f"--- [OPTIMIZER END] ---\n")

            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)