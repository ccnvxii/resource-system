from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Resource, Warehouse, Stock, UserRequest, Category,
    DistributionPlan, DistributionItem, Unit, RequestPurpose, UserProfile
)


# --- НОВІ СЕРІАЛІЗАТОРИ ДЛЯ 3NF ДОДІДНИКІВ ---

class UnitSerializer(serializers.ModelSerializer):
    """Серіалізатор для довідника одиниць виміру (кг, шт, л)"""

    class Meta:
        model = Unit
        fields = '__all__'


class RequestPurposeSerializer(serializers.ModelSerializer):
    """Серіалізатор для довідника типів призначення та їх ваг"""

    class Meta:
        model = RequestPurpose
        fields = '__all__'


# --- КОРИСТУВАЧІ ТА ПРОФІЛІ ---

class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source='is_staff', read_only=True)
    full_name = serializers.SerializerMethodField()
    organization = serializers.CharField(source='profile.organization', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_admin', 'organization',
                  'phone']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    organization = serializers.CharField(write_only=True, required=False)
    phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'organization', 'phone')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        # Витягуємо дані профілю
        org = validated_data.pop('organization', '')
        ph = validated_data.pop('phone', '')

        # Створюємо користувача
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )

        # Створюємо профіль (зв'язок 1-до-1 для 3NF)
        UserProfile.objects.create(user=user, organization=org, phone=ph)
        return user


# --- РЕСУРСИ ТА СКЛАДИ ---

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ResourceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'unit', 'unit_name', 'category', 'category_name']


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class StockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    unit_name = serializers.CharField(source='resource.unit.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'warehouse', 'warehouse_name', 'resource', 'resource_name', 'unit_name', 'amount']


# --- ЗАЯВКИ ТА РОЗПОДІЛ ---

class UserRequestSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    unit_name = serializers.CharField(source='resource.unit.name', read_only=True)
    purpose_name = serializers.CharField(source='purpose.name', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserRequest
        fields = '__all__'
        read_only_fields = ['priority', 'quantity_allocated', 'status']
        extra_kwargs = {'user': {'required': False}}

    def get_user_full_name(self, obj):
        if not obj.user:
            return "Невідомий"
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class DistributionItemSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='request.resource.name', read_only=True)
    unit_name = serializers.CharField(source='request.resource.unit.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    recipient_name = serializers.SerializerMethodField()
    purpose_name = serializers.CharField(source='request.purpose.name', read_only=True)
    priority = serializers.FloatField(source='request.priority', read_only=True)

    class Meta:
        model = DistributionItem
        fields = [
            'id', 'resource_name', 'unit_name', 'warehouse_name', 'amount',
            'recipient_name', 'purpose_name', 'request', 'priority'
        ]

    def get_recipient_name(self, obj):
        user = obj.request.user
        return f"{user.first_name} {user.last_name}".strip() or user.username


class DistributionPlanSerializer(serializers.ModelSerializer):
    items = DistributionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionPlan
        fields = ['id', 'created_at', 'executed', 'items']

class AuditLogSerializer(serializers.ModelSerializer):
    plan_id = serializers.IntegerField(source='plan.id', read_only=True)
    username = serializers.CharField(source='request.user.username', read_only=True)
    # Додайте цей метод, щоб ПІБ відображалося коректно
    user_full_name = serializers.SerializerMethodField()
    resource_name = serializers.CharField(source='request.resource.name', read_only=True)
    unit = serializers.CharField(source='request.resource.unit.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    timestamp = serializers.DateTimeField(source='plan.created_at', read_only=True)

    class Meta:
        model = DistributionItem
        fields = [
            'id', 'plan_id', 'timestamp', 'username', 'user_full_name',
            'resource_name', 'unit', 'warehouse_name', 'amount'
        ]

    def get_user_full_name(self, obj):
        user = obj.request.user
        return f"{user.first_name} {user.last_name}".strip() or user.username