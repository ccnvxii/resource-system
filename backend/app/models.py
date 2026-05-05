from django.db import models
from django.contrib.auth.models import User


# --- 1. ОДИНИЦІ ВИМІРУ (Додано для 3NF) ---
class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Одиниця виміру")

    def __str__(self):
        return self.name


# --- 2. КАТЕГОРІЇ (Довідник) ---
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    slug = models.SlugField(unique=True, verbose_name="Технічний код")
    criticality = models.FloatField(default=0.5, verbose_name="Критичність ресурсу")

    def __str__(self):
        return f"{self.name} (x{self.criticality})"


# --- 3. РЕСУРСИ ---
class Resource(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва ресурсу")
    # 3NF: Зв'язок з одиницею виміру
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Одиниця")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='resources')

    def __str__(self):
        return self.name


# --- 4. СКЛАДИ ---
class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва складу")
    location = models.CharField(max_length=200, verbose_name="Локація")

    def __str__(self):
        return self.name


# --- 5. ТИПИ ПРИЗНАЧЕННЯ (Винесено з коду в БД для 3NF) ---
class RequestPurpose(models.Model):
    name = models.CharField(max_length=100, verbose_name="Тип призначення")  # Напр: "Військові потреби"
    code = models.CharField(max_length=20, unique=True)  # Напр: "military"
    weight = models.FloatField(default=1.0, verbose_name="Вага пріоритету")

    def __str__(self):
        return self.name


# --- 6. ЗАПАСИ ---
class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('warehouse', 'resource')


# --- 7. ПРОФІЛЬ (Дані про організацію та телефон) ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)


# --- 8. ЗАЯВКИ ---
class UserRequest(models.Model):
    STATUS_CHOICES = [('new', 'Нова'), ('partial', 'Частково'), ('done', 'Виконана')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    quantity_requested = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # --- ПОЛЯ ДЛЯ НП ---
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Місто")
    warehouse_ref = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID відділення НП")
    warehouse_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адреса відділення")
    # ---------------------------

    purpose = models.ForeignKey(RequestPurpose, on_delete=models.PROTECT, verbose_name="Призначення")
    priority = models.FloatField(default=1.0, verbose_name="Пріоритет")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        w_dest = self.purpose.weight
        w_res = self.resource.category.criticality if self.resource.category else 0.5
        self.priority = float(w_dest) * float(w_res)
        super().save(*args, **kwargs)


# --- 9. ПЛАН ТА ЕЛЕМЕНТИ РОЗПОДІЛУ ---
class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)


class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, related_name='items', on_delete=models.CASCADE)
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

