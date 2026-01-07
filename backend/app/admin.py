from django.contrib import admin
from .models import Resource, Warehouse, Stock, UserRequest, DistributionPlan, DistributionItem

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit') # Видим категорию в списке
    list_filter = ('category',) # Фильтр справа по категории
    search_fields = ('name',)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'resource', 'amount')
    list_filter = ('warehouse', 'resource__category') # Фильтр по категории ресурса

@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'resource', 'quantity_requested', 'priority', 'status')
    list_filter = ('status', 'priority', 'resource__category')
    readonly_fields = ('quantity_allocated', 'created_at')

class DistributionItemInline(admin.TabularInline):
    model = DistributionItem
    extra = 0
    readonly_fields = ('resource', 'warehouse', 'amount', 'request')
    can_delete = False

@admin.register(DistributionPlan)
class DistributionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'executed')
    inlines = [DistributionItemInline]