from django.db import models
from django.contrib.auth.models import User


# --- 1. ОДИНИЦІ ВИМІРУ ---
class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Одиниця виміру")

    def __str__(self):
        return self.name


# --- 2. КАТЕГОРІЇ ---
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    slug = models.SlugField(unique=True, verbose_name="Технічний код")
    criticality = models.FloatField(default=0.5, verbose_name="Критичність ресурсу")

    def __str__(self):
        return f"{self.name} (x{self.criticality})"


# --- 3. РЕСУРСИ ---
class Resource(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва ресурсу")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Одиниця")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='resources')

    def __str__(self):
        return self.name


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


# --- 6. ЗАПАСИ ---
class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks')
    amount = models.PositiveIntegerField(default=0, verbose_name="Кількість на складі")

    class Meta:
        unique_together = ('warehouse', 'resource')


# --- 7. ПРОФІЛЬ ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)


# --- 8. ЗАЯВКИ ---
class UserRequest(models.Model):
    STATUS_CHOICES = [('new', 'Нова'), ('partial', 'Частково'), ('done', 'Виконана')]

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
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Розрахунок базового пріоритету
        w_dest = float(self.purpose.weight)
        w_res = float(self.resource.category.criticality) if self.resource.category else 0.5
        base_priority = w_dest * w_res

        multiplier = 1.0
        if self.latitude and self.longitude:
            try:
                from app.utils import calculate_front_multiplier
                multiplier = calculate_front_multiplier(self.latitude, self.longitude)
            except Exception as e:
                print(f"Save Priority Error inside models.py: {e}")

        self.priority = base_priority * multiplier
        super().save(*args, **kwargs)


# --- 9. ПЛАН ТА ЕЛЕМЕНТИ РОЗПОДІЛУ ---
class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)


class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, related_name='items', on_delete=models.CASCADE)
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(verbose_name="Кількість для видачі")