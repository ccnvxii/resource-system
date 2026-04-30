from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Resource, Warehouse, Stock,
    UserRequest, DistributionPlan, DistributionItem,
    Unit, RequestPurpose, UserProfile
)


# --- 1. Довідники 3NF ---

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(RequestPurpose)
class RequestPurposeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'weight')
    list_editable = ('weight',)  # Дозволяє швидко змінювати пріоритети прямо у списку
    search_fields = ('name', 'code')


# --- 2. Профілі користувачів ---

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'phone')
    search_fields = ('user__username', 'organization', 'phone')


# --- 3. Категорії та Ресурси ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'criticality')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('criticality',)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'get_total_stock')
    list_filter = ('category', 'unit')
    search_fields = ('name',)

    def get_total_stock(self, obj):
        # Показує загальну кількість на всіх складах
        from django.db.models import Sum
        total = obj.stocks.aggregate(Sum('amount'))['amount__sum'] or 0
        return f"{total} {obj.unit.name}"

    get_total_stock.short_description = "Загальний запас"


# --- 4. Склади та Запаси ---

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('resource', 'warehouse', 'colored_amount')
    list_filter = ('warehouse', 'resource__category')
    search_fields = ('resource__name',)

    def colored_amount(self, obj):
        # Візуальний контроль: дефіцитні позиції підсвічуються червоним
        color = "red" if obj.amount < 10 else "black"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.amount)

    colored_amount.short_description = "Кількість"


# --- 5. Заявки (Центр управління пріоритетами) ---

@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'resource', 'purpose', 'quantity_requested', 'status_label', 'priority',
                    'created_at')
    list_filter = ('status', 'purpose', 'priority')
    search_fields = ('user__username', 'user__first_name', 'resource__name')
    readonly_fields = ('priority', 'quantity_allocated', 'created_at')
    ordering = ('-priority', 'created_at')

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"

    user_display.short_description = "Заявник"

    def status_label(self, obj):
        # Кольорові бейджі для статусів
        colors = {'new': '#3b82f6', 'partial': '#f59e0b', 'done': '#10b981'}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )

    status_label.short_description = "Статус"


# --- 6. План Розподілу ---

class DistributionItemInline(admin.TabularInline):
    model = DistributionItem
    extra = 0
    readonly_fields = ('get_resource', 'get_recipient', 'warehouse', 'amount')
    can_delete = False

    def get_resource(self, obj):
        return obj.request.resource.name

    get_resource.short_description = "Ресурс"

    def get_recipient(self, obj):
        user = obj.request.user
        return f"{user.first_name} {user.last_name} ({user.username})"

    get_recipient.short_description = "Отримувач"


@admin.register(DistributionPlan)
class DistributionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'item_count', 'executed')
    inlines = [DistributionItemInline]
    list_filter = ('executed',)
    readonly_fields = ('created_at',)

    def item_count(self, obj):
        return obj.items.count()

    item_count.short_description = "Кількість позицій"