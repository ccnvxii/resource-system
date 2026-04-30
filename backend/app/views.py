from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import *
from .optimizer.distribute import calculate_distribution

from rest_framework.authentication import SessionAuthentication

class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return
    
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    authentication_classes = [UnsafeSessionAuthentication]  # Додай це
    permission_classes = [permissions.AllowAny]

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


@method_decorator(csrf_exempt, name='dispatch')
class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer

    authentication_classes = [UnsafeSessionAuthentication]
    permission_classes = [permissions.AllowAny]

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.filter(amount__gt=0)
    serializer_class = StockSerializer
    authentication_classes = [UnsafeSessionAuthentication]

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

@method_decorator(csrf_exempt, name='dispatch')
class DistributeResourcesView(APIView):
    authentication_classes = [UnsafeSessionAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        with transaction.atomic():
            active_requests_qs = UserRequest.objects.exclude(status='done')
            stocks_qs = Stock.objects.filter(amount__gt=0)

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
                return Response({"message": "Не знайдено розв'язку."}, status=200)

            new_plan = DistributionPlan.objects.create()
            items_to_create = []
            requests_map = {req.id: req for req in active_requests_qs}

            for item in plan_items_data:
                amount_dec = Decimal(str(item['amount']))
                req = requests_map.get(item['request_id'])
                if not req: continue

                items_to_create.append(DistributionItem(
                    plan=new_plan, request=req,
                    warehouse_id=item['warehouse_id'], amount=amount_dec
                ))

                req.quantity_allocated += amount_dec
                req.status = 'done' if req.quantity_allocated >= req.quantity_requested - Decimal('0.01') else 'partial'
                req.save()

                stock = Stock.objects.select_for_update().get(
                    warehouse_id=item['warehouse_id'], resource_id=req.resource_id
                )
                stock.amount -= amount_dec
                stock.save()

            DistributionItem.objects.bulk_create(items_to_create)
            serializer = DistributionPlanSerializer(new_plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)