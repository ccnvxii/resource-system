from django.db import models
from django.contrib.auth.models import User


# --- 1. КАТЕГОРІЇ (Довідник) ---
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    slug = models.SlugField(unique=True, verbose_name="Технічний код")

    # КРИТЕРІЙ ВРАЗЛИВОСТІ РЕСУРСУ (0.0 - 1.0)
    # Наприклад: Медицина = 1.0, Їжа = 0.8, Одяг = 0.5, Цукерки = 0.1
    criticality = models.FloatField(default=0.5, verbose_name="Критичність ресурсу")

    def __str__(self):
        return f"{self.name} (x{self.criticality})"

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"


# --- 2. РЕСУРСИ (Довідник) ---
class Resource(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва ресурсу")
    unit = models.CharField(max_length=20, verbose_name="Одиниця виміру")  # шт, кг, літри

    # Зв'язок з категорією. Якщо категорію видалять, ресурси залишаться (SET_NULL)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resources',
        verbose_name="Категорія"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ресурс"
        verbose_name_plural = "Ресурси"


# --- 3. СКЛАДИ (Довідник) ---
class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва складу")
    location = models.CharField(max_length=200, verbose_name="Локація")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склади"


# --- 4. ЗАПАСИ (Таблиця зв'язку Склад-Ресурс) ---
class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='stocks')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Кількість")

    class Meta:
        unique_together = ('warehouse', 'resource')
        verbose_name = "Запас"
        verbose_name_plural = "Запаси"

    def __str__(self):
        return f"{self.resource.name} @ {self.warehouse.name}: {self.amount}"


# --- 5. ЗАЯВКИ КОРИСТУВАЧІВ (Головна таблиця) ---
class UserRequest(models.Model):
    # ВАРІАНТИ ПРИЗНАЧЕННЯ (Матриця Пріоритетів - Koef Destination)
    PURPOSE_CHOICES = [
        ('military', 'Військові потреби / Фронт'),  # Вага 10
        ('hospital', 'Медичні заклади / Реанімація'),  # Вага 9
        ('disaster', 'Постраждалі від лих (Пожежі/Повені)'),  # Вага 8
        ('refugees', 'ВПО / Біженці'),  # Вага 6
        ('school', 'Освітні заклади / Діти'),  # Вага 4
        ('personal', 'Особисті потреби'),  # Вага 1
    ]

    STATUS_CHOICES = [
        ('new', 'Нова'),
        ('partial', 'Частково виконана'),
        ('done', 'Виконана'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, verbose_name="Ресурс")

    quantity_requested = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Замовлено")
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Видано")

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default='personal',
        verbose_name="Призначення"
    )

    # Пріоритет розраховується автоматично (0.0 - 10.0)
    priority = models.FloatField(default=1.0, verbose_name="Розрахунковий пріоритет")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Формула: P = K_dest * K_res
        """
        # 1. Вага призначення (Hardcoded policy)
        purpose_weights = {
            'military': 10.0,
            'hospital': 9.0,
            'disaster': 8.0,
            'refugees': 6.0,
            'school': 4.0,
            'personal': 1.0
        }
        w_dest = purpose_weights.get(self.purpose, 1.0)

        # 2. Вага ресурсу (беремо з категорії)
        w_res = 0.5  # Значення за замовчуванням
        if self.resource.category:
            w_res = self.resource.category.criticality

        # 3. Фінальний розрахунок
        self.priority = float(w_dest) * float(w_res)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-priority', 'created_at']


# --- 6. ПЛАН РОЗПОДІЛУ (Історія операцій) ---
class DistributionPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "План розподілу"
        verbose_name_plural = "Плани розподілу"


# --- 7. ЕЛЕМЕНТ РОЗПОДІЛУ (Транзакція) ---
class DistributionItem(models.Model):
    plan = models.ForeignKey(DistributionPlan, related_name='items', on_delete=models.CASCADE)

    # Зв'язок із Заявкою (звідси ми знаємо, який це ресурс і кому він йде)
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE)

    # Зв'язок зі Складом (звідки беремо)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Трансфер"
        verbose_name_plural = "Трансфери"