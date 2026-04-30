from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Resource, Warehouse, Stock, UserRequest, Category, DistributionPlan, DistributionItem

class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source='is_staff', read_only=True)
    # Додаємо повне ім'я для зручного відображення на фронтенді
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_admin']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

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
    user_full_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserRequest
        fields = '__all__'
        # ПРИБИРАЄМО 'user' звідси, щоб адмін міг його передавати
        read_only_fields = ['priority', 'quantity_allocated', 'status']
        # Додаємо налаштування, щоб поле не було обов'язковим для волонтера
        extra_kwargs = {
            'user': {'required': False}
        }

    def get_user_full_name(self, obj):
        if not obj.user:
            return "Невідомий"
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

class DistributionItemSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='request.resource.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    # Тут також замінюємо технічний логін на читабельне ім'я отримувача
    recipient_name = serializers.SerializerMethodField()
    purpose = serializers.CharField(source='request.purpose', read_only=True)
    priority = serializers.FloatField(source='request.priority', read_only=True)

    class Meta:
        model = DistributionItem
        fields = [
            'id', 'resource_name', 'warehouse_name', 'amount',
            'recipient_name', 'purpose', 'request', 'priority'
        ]

    def get_recipient_name(self, obj):
        return f"{obj.request.user.first_name} {obj.request.user.last_name}".strip() or obj.request.user.username

class DistributionPlanSerializer(serializers.ModelSerializer):
    items = DistributionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionPlan
        fields = ['id', 'created_at', 'executed', 'items']