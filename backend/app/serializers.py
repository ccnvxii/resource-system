from rest_framework import serializers
from .models import Resource, Warehouse, Stock, UserRequest, Category, DistributionPlan, DistributionItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ResourceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'unit', 'category', 'category_name']


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class StockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'warehouse', 'warehouse_name', 'resource', 'amount']


class UserRequestSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserRequest
        fields = '__all__'


# --- Серіалайзери для Плану Розподілу ---

class DistributionItemSerializer(serializers.ModelSerializer):
    # Отримуємо назви через зв'язки (3NF)
    resource_name = serializers.CharField(source='request.resource.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = DistributionItem
        fields = ['id', 'resource_name', 'warehouse_name', 'amount', 'request']


class DistributionPlanSerializer(serializers.ModelSerializer):
    items = DistributionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionPlan
        fields = ['id', 'created_at', 'executed', 'items']