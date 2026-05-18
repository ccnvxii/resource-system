# backend/app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


# Автоматичний розрахунок базового дедлайну (Сьогодні + 5 днів)
def get_default_due_date():
    return timezone.now().date() + timedelta(days=5)


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


# --- 7. ПРОФІЛЬ КОРИСТУВАЧА ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)


# --- 8. ЗАЯВКИ ---
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

    # Поля часових обмежень (Дедлайни)
    due_date = models.DateField(default=get_default_due_date, verbose_name="Граничний термін виконання")
    auto_extend = models.BooleanField(default=True, verbose_name="Автопродовження терміну")
    extension_count = models.PositiveIntegerField(default=0, verbose_name="Кількість автопродовжень")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 1. Нормалізація базових критеріїв до шкали [0...1]
        # Максимальна вага призначення в БД = 10.0, тому ділимо на 10
        k_purp = float(self.purpose.weight) / 10.0
        k_crit = float(self.resource.category.criticality) if self.resource.category else 0.5

        from app.utils import calculate_front_multiplier, calculate_time_multiplier

        # 2. Отримання динамічних множників (кожен повертає максимум 3.0)
        geo_mult = calculate_front_multiplier(self.latitude, self.longitude)
        time_mult = calculate_time_multiplier(self.due_date)

        # Нормалізуємо ГІС та Час до шкали [0...1] (ділимо на їхній макс, тобто на 3.0)
        k_geo = geo_mult / 3.0
        k_time = time_mult / 3.0

        # Штраф за тривалий дефіцит (вік заявки при автопродовженні)
        age_penalty = max(0.5, 1.0 - (self.extension_count * 0.1))

        # 3. Визначення вагових коефіцієнтів (Сума = 1.0)
        alpha = 0.35  # Вага призначення (Призначення)
        beta = 0.25  # Вага часу (Дедлайн)
        gamma = 0.25  # Вага простору (ГІС)
        delta = 0.15  # Вага номенклатури (Критичність ресурсу)

        # Обчислення зваженої суми
        weighted_sum = (alpha * k_purp) + (beta * k_time) + (gamma * k_geo) + (delta * k_crit)

        # 4. Масштабування до 10-бальної шкали та застосування штрафу за старість
        final_index = weighted_sum * 10.0 * age_penalty

        # Округлюємо до одного знака після коми для красивого відображення в інтерфейсі (напр. 8.4)
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
    amount = models.PositiveIntegerField(verbose_name="Кількість для видачі")