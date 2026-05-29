# backend/app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


# Автоматичний розрахунок базового дедлайну (Сьогодні + 5 днів)
def get_default_due_date():
    return timezone.now().date() + timedelta(days=5)


# --- 1. ОДИНИЦІ ВИМІРУ (Коробки, Мішки, Набори, Штуки) ---
class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Одиниця виміру (пакування)")

    def __str__(self):
        return self.name


# --- 2. КАТЕГОРІЇ ---
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    slug = models.SlugField(unique=True, verbose_name="Технічний код")
    criticality = models.FloatField(default=0.5, verbose_name="Критичність ресурсу")

    def __str__(self):
        return f"{self.name} (x{self.criticality})"


# --- 3. РЕСУРСИ (Орієнтовані на укрупнений облік) ---
class Resource(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва ресурсу")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Логістична упаковка")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='resources')

    def __str__(self):
        return f"{self.name} ({self.unit.name})"


# --- 4. СКЛАДИ ---
class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва складу")
    location = models.CharField(max_length=200, verbose_name="Локація")
    latitude = models.FloatField(default=0.0, verbose_name="Широта")
    longitude = models.FloatField(default=0.0, verbose_name="Довгота")

    def __str__(self):
        return self.name


# --- 5. ТИПИ ПРИЗНАЧЕННЯ ---
class RequestPurpose(models.Model):
    name = models.CharField(max_length=100, verbose_name="Тип призначення")
    code = models.CharField(max_length=20, unique=True)
    weight = models.FloatField(default=1.0, verbose_name="Вага пріоритету")

    def __str__(self):
        return self.name


# --- 6. ЗАПАСИ (З урахуванням партій та термінів придатності) ---
class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks')
    amount = models.PositiveIntegerField(default=0, verbose_name="Кількість упаковок/штук")

    # Нове логістичне поле для аналітики та розширення системи (алгоритм ЛП його ігнорує)
    expiration_date = models.DateField(null=True, blank=True, verbose_name="Термін придатності партії")

    class Meta:
        unique_together = ('warehouse', 'resource')

    def __str__(self):
        exp_info = f" (Придатний до: {self.expiration_date})" if self.expiration_date else ""
        return f"{self.warehouse.name} -> {self.resource.name}: {self.amount} {self.resource.unit.name}{exp_info}"


# --- 7. ПРОФІЛЬ КОРИСТУВАЧА ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)


# --- 8. ЗАЯВКИ (Обліковуються в тих же упаковках, що й ресурси) ---
class UserRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Нова'),
        ('partial', 'Частково'),
        ('done', 'Виконана'),
        ('expired', 'Протермінована')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)

    quantity_requested = models.PositiveIntegerField(verbose_name="Запитувана кількість")
    quantity_allocated = models.PositiveIntegerField(default=0, verbose_name="Виділена кількість")

    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Місто")
    warehouse_ref = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID відділення НП")
    warehouse_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адреса відділення")

    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта отримувача")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Довгота отримувача")

    purpose = models.ForeignKey(RequestPurpose, on_delete=models.PROTECT, verbose_name="Призначення")
    priority = models.FloatField(default=1.0, verbose_name="Пріоритет")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    due_date = models.DateField(default=get_default_due_date, verbose_name="Граничний термін виконання")
    auto_extend = models.BooleanField(default=True, verbose_name="Автопродовження терміну")
    extension_count = models.PositiveIntegerField(default=0, verbose_name="Кількість автопродовжень")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        k_purp = float(self.purpose.weight) / 10.0
        k_crit = float(self.resource.category.criticality) if self.resource.category else 0.5

        from app.utils import calculate_front_multiplier, calculate_time_multiplier

        geo_mult = calculate_front_multiplier(self.latitude, self.longitude)
        time_mult = calculate_time_multiplier(self.due_date)

        k_geo = geo_mult / 3.0
        k_time = time_mult / 3.0

        age_penalty = max(0.5, 1.0 - (self.extension_count * 0.1))

        alpha = 0.35
        beta = 0.25
        gamma = 0.25
        delta = 0.15

        weighted_sum = (alpha * k_purp) + (beta * k_time) + (gamma * k_geo) + (delta * k_crit)
        final_index = weighted_sum * 10.0 * age_penalty
        self.priority = round(max(0.0, min(10.0, final_index)), 1)

        super().save(*args, **kwargs)


# --- 9. ПЛАН ТА ЕЛЕМЕНТИ РОЗПОДІЛУ ---
class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)


class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, related_name='items', on_delete=models.CASCADE)
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(verbose_name="Виділена кількість упаковок/штук")