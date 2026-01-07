from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Підключаємо сигнал, який спрацює після завершення міграцій
        post_migrate.connect(create_initial_data, sender=self)


def create_initial_data(sender, **kwargs):
    """
    Автоматичне наповнення бази даних (версія 3NF - українська локалізація).
    Створює Категорії -> Ресурси -> Склади -> Запаси -> Заявки.
    """
    # Перевірка, що міграція стосується саме нашого додатку 'app'
    if sender.name != 'app':
        return

    # Безпечна перевірка наявності таблиць у БД (щоб код не впав на старті)
    try:
        if 'app_resource' not in connection.introspection.table_names():
            return
    except Exception:
        return

    # Імпорти робимо всередині функції, щоб уникнути помилки раннього завантаження Django
    from django.contrib.auth.models import User
    from .models import Resource, Warehouse, Stock, UserRequest, Category

    print("--- [Auto-Populate] Починаємо наповнення (Українська версія) ---")

    # --- 1. Створення Категорій ---
    # slug - технічний код (латиницею), name - назва для людей
    categories_data = [
        ('meds', 'Медицина'),
        ('food', 'Їжа'),
        ('water', 'Вода'),
        ('clothes', 'Одяг'),
        ('other', 'Інше'),
    ]

    cats_objs = {}  # Словник для швидкого пошуку об'єктів категорій
    for slug, name in categories_data:
        cat, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name}
        )
        cats_objs[slug] = cat

    # --- 2. Створення Користувачів ---
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
            print(f"Створено користувача: {u_data['username']}")
        users_map[u_data['username']] = user

    # --- 3. Створення Ресурсів ---
    # Використовуємо 'cat_slug' для прив'язки до категорії
    resources_data = [
        {'name': 'Аспірин', 'unit': 'упак', 'cat_slug': 'meds'},
        {'name': 'Бинти', 'unit': 'шт', 'cat_slug': 'meds'},
        {'name': 'Хліб', 'unit': 'шт', 'cat_slug': 'food'},
        {'name': 'Тушонка', 'unit': 'банка', 'cat_slug': 'food'},
        {'name': 'Вода питна (5л)', 'unit': 'бут', 'cat_slug': 'water'},
        {'name': 'Куртка тепла', 'unit': 'шт', 'cat_slug': 'clothes'},
        {'name': 'Ковдра', 'unit': 'шт', 'cat_slug': 'clothes'},
    ]

    resource_objects = {}
    for res in resources_data:
        # Отримуємо об'єкт категорії зі словника
        cat_obj = cats_objs.get(res['cat_slug'])

        # Страховка: якщо категорію не знайдено, ставимо "Інше"
        if not cat_obj:
            cat_obj = cats_objs['other']

        obj, _ = Resource.objects.update_or_create(
            name=res['name'],
            defaults={
                'unit': res['unit'],
                'category': cat_obj  # <-- Передаємо об'єкт Category (ForeignKey)
            }
        )
        resource_objects[res['name']] = obj

    # --- 4. Створення Складів ---
    warehouses_data = [
        {'name': 'Центральний Хаб', 'location': 'Центр міста'},
        {'name': 'Медичний Склад', 'location': 'Лікарня №1'},
        {'name': 'Продуктовий', 'location': 'Промзона'},
    ]

    warehouse_objects = {}
    for wh in warehouses_data:
        obj, _ = Warehouse.objects.update_or_create(
            name=wh['name'],
            defaults={'location': wh['location']}
        )
        warehouse_objects[wh['name']] = obj

    # --- 5. Створення Запасів (Stock) ---
    # Формат: (Назва Складу, Назва Ресурсу, Кількість)
    stocks_list = [
        ('Медичний Склад', 'Аспірин', 500),
        ('Медичний Склад', 'Бинти', 1000),
        ('Продуктовий', 'Хліб', 200),
        ('Продуктовий', 'Тушонка', 300),
        ('Продуктовий', 'Вода питна (5л)', 1000),
        ('Центральний Хаб', 'Вода питна (5л)', 100),
        ('Центральний Хаб', 'Куртка тепла', 50),
        ('Центральний Хаб', 'Ковдра', 50),
        ('Центральний Хаб', 'Аспірин', 100),
    ]

    for wh_name, res_name, amount in stocks_list:
        # Використовуємо update_or_create, щоб не дублювати запаси при перезапуску
        Stock.objects.update_or_create(
            warehouse=warehouse_objects[wh_name],
            resource=resource_objects[res_name],
            defaults={'amount': amount}
        )

    # --- 6. Створення Заявок (UserRequest) ---
    requests_list = [
        {'user': 'volunteer_1', 'res': 'Вода питна (5л)', 'qty': 500, 'pri': 10},
        {'user': 'doctor_1', 'res': 'Бинти', 'qty': 200, 'pri': 8},
        {'user': 'volunteer_1', 'res': 'Ковдра', 'qty': 10, 'pri': 5},
    ]

    for req in requests_list:
        UserRequest.objects.get_or_create(
            user=users_map[req['user']],
            resource=resource_objects[req['res']],
            quantity_requested=req['qty'],
            defaults={
                'priority': req['pri'],
                'status': 'new'
            }
        )

    print("--- [Auto-Populate] Дані успішно завантажено (UA)! ---")