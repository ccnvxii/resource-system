# app/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection


class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        post_migrate.connect(create_initial_data, sender=self)


def create_initial_data(sender, **kwargs):
    from django.contrib.auth.models import User
    from .models import Resource, Warehouse, Stock, UserRequest, Category

    if sender.name != 'app':
        return

    try:
        if 'app_resource' not in connection.introspection.table_names():
            return
    except Exception:
        return

    print("--- [System Init] Наповнення бази: Логін = Email ---")

    # --- 1. КАТЕГОРІЇ ---
    categories_data = [
        ('meds', 'Медицина / Ліки', 1.0),
        ('water', 'Вода питна', 0.9),
        ('food', 'Продукти харчування', 0.7),
        ('clothes', 'Одяг та Тепло', 0.5),
        ('hygiene', 'Гігієна', 0.4),
        ('other', 'Інше / Комфорт', 0.1),
    ]

    cats_objs = {}
    for slug, name, crit in categories_data:
        cat, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={'name': name, 'criticality': crit}
        )
        cats_objs[slug] = cat

    # --- 2. КОРИСТУВАЧІ (Логін збігається з Email) ---
    users_info = [
        {
            'first': 'Адмін',
            'last': 'Системи',
            'email': 'admin@resq.ua',
            'is_staff': True
        },
        {
            'first': 'Олексій',
            'last': 'Військовий',
            'email': 'mil@test.com',
            'is_staff': False
        },
        {
            'first': 'Марія',
            'last': 'Лікар',
            'email': 'doc@test.com',
            'is_staff': False
        },
        {
            'first': 'Дар’я',
            'last': 'Волонтер',
            'email': 'vol@test.com',
            'is_staff': False
        },
    ]

    users_map = {}
    for u in users_info:
        # Ми ставимо email у поле username. Тепер логін — це пошта.
        user, created = User.objects.get_or_create(
            username=u['email'],
            defaults={
                'email': u['email'],
                'first_name': u['first'],
                'last_name': u['last'],
            }
        )

        if created:
            pwd = 'adminpassword' if u['is_staff'] else '1234'
            user.set_password(pwd)
            if u['is_staff']:
                user.is_staff = True
                user.is_superuser = True
            user.save()

        users_map[u['email']] = user

    # --- 3. РЕСУРСИ ---
    resources_data = [
        {'name': 'Аспірин', 'unit': 'упак', 'cat': 'meds'},
        {'name': 'Турнікет', 'unit': 'шт', 'cat': 'meds'},
        {'name': 'Вода (6л)', 'unit': 'бут', 'cat': 'water'},
        {'name': 'Тушонка', 'unit': 'банка', 'cat': 'food'},
        {'name': 'Ковдра тепла', 'unit': 'шт', 'cat': 'clothes'},
    ]

    res_objs = {}
    for res in resources_data:
        cat_obj = cats_objs.get(res['cat'])
        obj, _ = Resource.objects.update_or_create(
            name=res['name'],
            defaults={'unit': res['unit'], 'category': cat_obj}
        )
        res_objs[res['name']] = obj

    # --- 4. СКЛАДИ ---
    w_main, _ = Warehouse.objects.get_or_create(name='Центральний Хаб (Київ)')
    w_east, _ = Warehouse.objects.get_or_create(name='Східний Склад (Харків)')
    w_west, _ = Warehouse.objects.get_or_create(name='Західний Склад (Львів)')

    # --- 5. ЗАПАСИ ---
    stocks_data = [
        (w_east, 'Аспірин', 50),
        (w_west, 'Аспірин', 10),
        (w_main, 'Турнікет', 100),
    ]

    for wh, res_name, qty in stocks_data:
        Stock.objects.update_or_create(
            warehouse=wh,
            resource=res_objs[res_name],
            defaults={'amount': qty}
        )

    # --- 6. ЗАЯВКИ ---
    UserRequest.objects.all().delete()
    scenarios = [
        {'email': 'mil@test.com', 'res': 'Аспірин', 'qty': 100, 'purpose': 'military'},
        {'email': 'doc@test.com', 'res': 'Аспірин', 'qty': 50, 'purpose': 'hospital'},
        {'email': 'vol@test.com', 'res': 'Аспірин', 'qty': 20, 'purpose': 'refugees'},
    ]

    for s in scenarios:
        UserRequest.objects.create(
            user=users_map[s['email']],
            resource=res_objs[s['res']],
            quantity_requested=s['qty'],
            purpose=s['purpose'],
            status='new'
        )

    print("--- [Success] Логіни тепер відповідають Email. Адмін: admin@resq.ua ---")