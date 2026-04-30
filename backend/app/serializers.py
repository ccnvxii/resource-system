from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Resource, Warehouse, Stock, UserRequest, Category, DistributionPlan, DistributionItem

class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source='is_staff', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_admin']

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
    resource_name = serializers.CharField(source='resource.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'warehouse', 'warehouse_name', 'resource', 'resource_name', 'amount']

class UserRequestSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserRequest
        fields = '__all__'
        read_only_fields = ['priority', 'quantity_allocated', 'status']

class DistributionItemSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='request.resource.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    recipient_name = serializers.CharField(source='request.user.username', read_only=True)
    purpose = serializers.CharField(source='request.purpose', read_only=True)
    priority = serializers.FloatField(source='request.priority', read_only=True)

    class Meta:
        model = DistributionItem
        fields = [
            'id', 'resource_name', 'warehouse_name', 'amount',
            'recipient_name', 'purpose', 'request', 'priority'
        ]

class DistributionPlanSerializer(serializers.ModelSerializer):
    items = DistributionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionPlan
        fields = ['id', 'created_at', 'executed', 'items']