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
    from .models import Resource, Warehouse, Stock, UserRequest, Category, Unit, RequestPurpose, UserProfile

    if sender.name != 'app':
        return

    # Перевірка наявності таблиць, щоб не впасти під час самих міграцій
    tables = connection.introspection.table_names()
    if 'app_unit' not in tables or 'app_requestpurpose' not in tables:
        return

    print("--- [System Init] Наповнення бази даних (3NF) ---")

    # --- 1. ОДИНИЦІ ВИМІРУ (3NF) ---
    units_data = ['шт', 'кг', 'л', 'упак', 'банка', 'бут']
    unit_objs = {}
    for name in units_data:
        u_obj, _ = Unit.objects.get_or_create(name=name)
        unit_objs[name] = u_obj

    # --- 2. КАТЕГОРІЇ ---
    categories_data = [
        ('meds', 'Медицина / Ліки', 1.0),
        ('water', 'Вода питна', 0.9),
        ('food', 'Продукти харчування', 0.7),
        ('clothes', 'Одяг та Тепло', 0.5),
    ]
    cats_objs = {}
    for slug, name, crit in categories_data:
        cat, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={'name': name, 'criticality': crit}
        )
        cats_objs[slug] = cat

    # --- 3. ТИПИ ПРИЗНАЧЕННЯ (3NF) ---
    purposes_data = [
        ('military', 'Військові потреби', 10.0),
        ('hospital', 'Медичні заклади', 9.0),
        ('disaster', 'Зона лиха', 8.0),
        ('refugees', 'ВПО та біженці', 6.0),
        ('personal', 'Особисті потреби', 1.0),
    ]
    purp_objs = {}
    for code, name, weight in purposes_data:
        p_obj, _ = RequestPurpose.objects.update_or_create(
            code=code,
            defaults={'name': name, 'weight': weight}
        )
        purp_objs[code] = p_obj

    # --- 4. КОРИСТУВАЧІ ТА ПРОФІЛІ (3NF) ---
    users_info = [
        {'first': 'Адмін', 'last': 'Системи', 'email': 'admin@resq.ua', 'is_staff': True, 'org': 'RESQ HQ'},
        {'first': 'Дар’я', 'last': 'Россоха', 'email': 'vol@test.com', 'is_staff': False, 'org': 'Volunteer Center'},
    ]
    users_map = {}
    for u in users_info:
        user, created = User.objects.get_or_create(
            username=u['email'],
            defaults={'email': u['email'], 'first_name': u['first'], 'last_name': u['last']}
        )
        if created:
            user.set_password('adminpassword' if u['is_staff'] else '1234')
            user.is_staff = u['is_staff']
            user.is_superuser = u['is_staff']
            user.save()

        # Створюємо профіль (3NF)
        UserProfile.objects.get_or_create(user=user, defaults={'organization': u['org'], 'phone': '+38000000000'})
        users_map[u['email']] = user

    # --- 5. РЕСУРСИ ---
    resources_data = [
        {'name': 'Турнікет', 'unit': 'шт', 'cat': 'meds'},
        {'name': 'Аспірин', 'unit': 'упак', 'cat': 'meds'},
        {'name': 'Тушонка', 'unit': 'банка', 'cat': 'food'},
    ]
    res_objs = {}
    for res in resources_data:
        obj, _ = Resource.objects.update_or_create(
            name=res['name'],
            defaults={
                'unit': unit_objs[res['unit']],  # Зв'язок з Unit
                'category': cats_objs[res['cat']]
            }
        )
        res_objs[res['name']] = obj

    # --- 6. СКЛАДИ ТА ЗАПАСИ ---
    w_main, _ = Warehouse.objects.get_or_create(name='Центральний Хаб (Київ)', location='Київ, вул. Центральна 1')
    Stock.objects.update_or_create(warehouse=w_main, resource=res_objs['Турнікет'], defaults={'amount': 100})

    # --- 7. ЗАЯВКИ (3NF) ---
    UserRequest.objects.all().delete()
    UserRequest.objects.create(
        user=users_map['vol@test.com'],
        resource=res_objs['Турнікет'],
        quantity_requested=50,
        purpose=purp_objs['military'],  # Зв'язок з RequestPurpose
        status='new'
    )

    print("--- [Success] База даних готова. Логін: admin@resq.ua / adminpassword ---")
