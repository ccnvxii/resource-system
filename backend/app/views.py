from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal

# Импортируем модели и сериализаторы
from .models import Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem
from .serializers import (
    ResourceSerializer, WarehouseSerializer, StockSerializer,
    UserRequestSerializer, DistributionPlanSerializer
)
# Импортируем наш алгоритм
from .optimizer.distribute import calculate_distribution


# --- CRUD ViewSets (Стандартные действия: получить, создать, изменить, удалить) ---

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


# --- Logic View (Главная кнопка "Распределить") ---

class DistributeResourcesView(APIView):
    def get(self, request):
        """
        Возвращает инструкцию. Нужен для того, чтобы в браузере
        появилась кнопка POST.
        """
        return Response({
            "info": "Это эндпоинт для распределения ресурсов.",
            "instruction": "Нажмите кнопку POST внизу, чтобы запустить алгоритм.",
            "method": "POST only"
        })

    def post(self, request):
        with transaction.atomic():
            # 1. ПОДГОТОВКА ДАННЫХ
            # Берем только активные заявки (не выполненные)
            active_requests_qs = UserRequest.objects.exclude(status='done')
            # Берем склады, где есть запасы
            stocks_qs = Stock.objects.filter(amount__gt=0)

            # Превращаем данные из БД в список словарей для алгоритма
            # Важно: конвертируем Decimal в float, так как Python легче считает float
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

            # 2. ЗАПУСК АЛГОРИТМА
            # (Функция лежит в backend/app/optimizer/distribute.py)
            plan_items_data = calculate_distribution(requests_data, stocks_data)

            if not plan_items_data:
                return Response({"message": "Нет доступных ресурсов для распределения или нет активных заявок."},
                                status=200)

            # 3. СОХРАНЕНИЕ РЕЗУЛЬТАТА
            new_plan = DistributionPlan.objects.create()
            items_to_create = []

            # Словарь для кэширования заявок, чтобы не дергать БД лишний раз
            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_decimal = Decimal(str(item['amount']))
                req = requests_map[item['request_id']]

                # Создаем запись в плане
                items_to_create.append(DistributionItem(
                    plan=new_plan,
                    request=req,
                    warehouse_id=item['warehouse_id'],
                    resource_id=item['resource_id'],
                    amount=amount_decimal
                ))

                # Обновляем статус заявки (виртуальное резервирование)
                req.quantity_allocated += amount_decimal

                if req.quantity_allocated >= req.quantity_requested:
                    req.status = 'done'
                else:
                    req.status = 'partial'

                req.save()

            # Сохраняем все элементы плана одним запросом (быстро)
            DistributionItem.objects.bulk_create(items_to_create)

            # 4. ОТВЕТ
            # Возвращаем красивый JSON с планом
            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=201)