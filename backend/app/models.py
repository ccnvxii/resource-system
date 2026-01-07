from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    slug = models.SlugField(unique=True, verbose_name="Код (slug)")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"


class Resource(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва")
    unit = models.CharField(max_length=20, default='шт', verbose_name="Од. виміру")

    # Зв'язок з категорією
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        verbose_name="Категорія",
        related_name='resources'
    )

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    class Meta:
        verbose_name = "Ресурс"
        verbose_name_plural = "Ресурси"


class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва складу")
    location = models.CharField(max_length=200, blank=True, verbose_name="Локація")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склади"


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks', verbose_name="Склад")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks', verbose_name="Ресурс")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Кількість")

    class Meta:
        unique_together = ('warehouse', 'resource')
        verbose_name = "Запас"
        verbose_name_plural = "Запаси"

    def __str__(self):
        return f"{self.resource.name} на {self.warehouse.name}"


class UserRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Нова'),
        ('partial', 'Частково виконана'),
        ('done', 'Виконана'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, verbose_name="Ресурс")

    quantity_requested = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Необхідна кількість")
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Виділено")

    priority = models.IntegerField(default=1, verbose_name="Пріоритет (1-10)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return f"Заявка від {self.user.username}: {self.resource.name}"

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"


class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    executed = models.BooleanField(default=False, verbose_name="Виконано")

    class Meta:
        verbose_name = "План розподілу"
        verbose_name_plural = "Плани розподілу"

    def __str__(self):
        return f"План від {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, on_delete=models.CASCADE, related_name='items', verbose_name="План")
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE, verbose_name="Заявка")

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Зі складу")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Кількість")

    class Meta:
        verbose_name = "Елемент розподілу"
        verbose_name_plural = "Елементи розподілу"

    def __str__(self):
        return f"{self.request.resource.name}: {self.amount} зі складу {self.warehouse.name}"