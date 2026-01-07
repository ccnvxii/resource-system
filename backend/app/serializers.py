from rest_framework import serializers
from .models import Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem

class ResourceSerializer(serializers.ModelSerializer):
    """Сериализатор для ресурсов с отображением категории"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'unit', 'category', 'category_display']

class WarehouseSerializer(serializers.ModelSerializer):
    """Сериализатор для складов"""
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location']

class StockSerializer(serializers.ModelSerializer):
    """Сериализатор для запасов (с именами ресурсов и складов)"""
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    resource_category = serializers.CharField(source='resource.get_category_display', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'warehouse', 'warehouse_name', 'resource', 'resource_name', 'resource_category', 'amount']

class UserRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для заявок пользователей"""
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    resource_category = serializers.CharField(source='resource.get_category_display', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserRequest
        fields = [
            'id', 'user', 'username', 'resource', 'resource_name', 'resource_category',
            'quantity_requested', 'quantity_allocated', 'priority', 'status', 'created_at'
        ]
        # Поля, которые пользователь не может менять сам:
        read_only_fields = ['user', 'quantity_allocated', 'status', 'created_at']

    def create(self, validated_data):
        # Автоматически подставляем текущего пользователя из запроса
        user = self.context['request'].user
        return UserRequest.objects.create(user=user, **validated_data)

class DistributionItemSerializer(serializers.ModelSerializer):
    """Сериализатор элемента плана (строка перемещения)"""
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = DistributionItem
        fields = ['id', 'resource_name', 'warehouse_name', 'amount', 'request']

class DistributionPlanSerializer(serializers.ModelSerializer):
    """Сериализатор плана распределения (содержит список элементов)"""
    items = DistributionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionPlan
        fields = ['id', 'created_at', 'executed', 'items']