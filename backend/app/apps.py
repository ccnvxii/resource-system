from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Підключаємо сигнал
        post_migrate.connect(create_initial_data, sender=self)


def create_initial_data(sender, **kwargs):
    """
    Автоматичне наповнення бази даних після міграції.
    """
    # 1. Перевірка, що це міграція саме нашого додатку
    if sender.name != 'app':
        return

    # 2. Перевірка, чи створені таблиці в БД
    # (Важливо, щоб не отримати помилку при першому запуску)
    if 'app_resource' not in connection.introspection.table_names():
        return

    # Імпорти робимо всередині функції, щоб уникнути помилки "AppRegistryNotReady"
    from django.contrib.auth.models import User
    from .models import Resource, Warehouse, Stock, UserRequest

    print("--- [Auto-Populate] Починаємо перевірку та наповнення даних ---")

    # --- 1. Користувачі ---
    users_data = [
        {'username': 'volunteer_1', 'email': 'v1@test.com', 'pass': '1234'},
        {'username': 'doctor_1', 'email': 'd1@test.com', 'pass': '1234'},
    ]

    users_map = {}
    for u_data in users_data:
        user, created = User.objects.get_or_create(
            username=u_data['username'],
            defaults={'email': u_data['email']}
        )
        if created:
            user.set_password(u_data['pass'])
            user.save()
        users_map[u_data['username']] = user

    # --- 2. Ресурси ---
    resources_data = [
        {'name': 'Аспирин', 'unit': 'упак', 'category': 'meds'},
        {'name': 'Бинты', 'unit': 'шт', 'category': 'meds'},
        {'name': 'Хлеб', 'unit': 'шт', 'category': 'food'},
        {'name': 'Тушенка', 'unit': 'банка', 'category': 'food'},
        {'name': 'Вода питьевая (5л)', 'unit': 'бут', 'category': 'water'},
        {'name': 'Куртка теплая', 'unit': 'шт', 'category': 'clothes'},
        {'name': 'Одеяло', 'unit': 'шт', 'category': 'clothes'},
    ]

    resource_objects = {}
    for res in resources_data:
        obj, _ = Resource.objects.update_or_create(
            name=res['name'],
            defaults={'unit': res['unit'], 'category': res['category']}
        )
        resource_objects[res['name']] = obj

    # --- 3. Склади ---
    warehouses_data = [
        {'name': 'Центральный Хаб', 'location': 'Центр города'},
        {'name': 'Мед. Склад', 'location': 'Больница №1'},
        {'name': 'Продуктовый', 'location': 'Промзона'},
    ]

    warehouse_objects = {}
    for wh in warehouses_data:
        obj, _ = Warehouse.objects.update_or_create(
            name=wh['name'],
            defaults={'location': wh['location']}
        )
        warehouse_objects[wh['name']] = obj

    # --- 4. Запасы (Stock) ---
    # Структура: (Назва складу, Назва ресурсу, Кількість)
    stocks_list = [
        ('Мед. Склад', 'Аспирин', 500),
        ('Мед. Склад', 'Бинты', 1000),
        ('Продуктовый', 'Хлеб', 200),
        ('Продуктовый', 'Тушенка', 300),
        ('Продуктовый', 'Вода питьевая (5л)', 1000),
        ('Центральный Хаб', 'Вода питьевая (5л)', 100),
        ('Центральный Хаб', 'Куртка теплая', 50),
        ('Центральный Хаб', 'Одеяло', 50),
        ('Центральный Хаб', 'Аспирин', 100),
    ]

    for wh_name, res_name, amount in stocks_list:
        Stock.objects.update_or_create(
            warehouse=warehouse_objects[wh_name],
            resource=resource_objects[res_name],
            defaults={'amount': amount}
        )

    # --- 5. Заявки (UserRequest) ---
    requests_list = [
        {'user': 'volunteer_1', 'res': 'Вода питьевая (5л)', 'qty': 500, 'pri': 10},
        {'user': 'doctor_1', 'res': 'Бинты', 'qty': 200, 'pri': 8},
        {'user': 'volunteer_1', 'res': 'Одеяло', 'qty': 10, 'pri': 5},
    ]

    for req in requests_list:
        UserRequest.objects.update_or_create(
            user=users_map[req['user']],
            resource=resource_objects[req['res']],
            quantity_requested=req['qty'],
            defaults={
                'priority': req['pri'],
                'status': 'new'
            }
        )

    print("--- [Auto-Populate] Дані успішно оновлено! ---")