from django.db import models
from django.contrib.auth.models import User

class Resource(models.Model):
    # Новые категории, как вы просили
    CATEGORY_CHOICES = [
        ('food', 'Еда'),
        ('water', 'Вода'),
        ('meds', 'Лекарства'),
        ('clothes', 'Вещи'),
        ('other', 'Прочее'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название")
    unit = models.CharField(max_length=20, default='шт', verbose_name="Ед. измерения")
    # Новое поле
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="Категория"
    )

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название склада")
    location = models.CharField(max_length=200, blank=True, verbose_name="Локация")

    def __str__(self):
        return self.name

class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Количество")

    class Meta:
        unique_together = ('warehouse', 'resource')

class UserRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('partial', 'Частично выполнена'),
        ('done', 'Выполнена'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    quantity_requested = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Требуется")
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Выделено")
    priority = models.IntegerField(default=1, verbose_name="Приоритет (1-10)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Заявка: {self.resource.name} - {self.quantity_requested} {self.resource.unit}"

class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)

class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, on_delete=models.CASCADE, related_name='items')
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)