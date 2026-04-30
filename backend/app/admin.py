from django.contrib import admin
from .models import Category, Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem


# 1. Категорії
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'criticality')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('criticality',)

# 2. Ресурси
@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit')
    list_filter = ('category',)
    search_fields = ('name',)


# 3. Склади
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')


# 4. Запаси
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'resource', 'amount')
    list_filter = ('warehouse', 'resource__category')
    search_fields = ('resource__name',)


# 5. Заявки
@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'purpose', 'quantity_requested', 'status', 'priority', 'created_at')
    list_filter = ('status', 'purpose', 'priority')
    search_fields = ('user__username', 'resource__name')
    readonly_fields = ('priority', 'quantity_allocated')

    # Сортування: спочатку найвищий пріоритет
    ordering = ('-priority', 'created_at')


# --- Налаштування для Плану Розподілу ---
class DistributionItemInline(admin.TabularInline):
    model = DistributionItem
    extra = 0
    readonly_fields = ('get_resource_name', 'get_recipient', 'warehouse', 'amount')
    fields = ('get_resource_name', 'get_recipient', 'warehouse', 'amount')
    can_delete = False

    def get_resource_name(self, obj):
        return obj.request.resource.name

    get_resource_name.short_description = "Ресурс"

    def get_recipient(self, obj):
        return obj.request.user.username

    get_recipient.short_description = "Отримувач"

@admin.register(DistributionPlan)
class DistributionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'executed')
    inlines = [DistributionItemInline]
    readonly_fields = ('created_at',)