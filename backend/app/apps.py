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
    Автоматичне наповнення бази даних.
    Реалізує сценарії для "Матриці Пріоритетів" (Priority Matrix).
    """
    # Перевірка, що це наш додаток
    if sender.name != 'app':
        return

    # Перевірка, чи створені таблиці (щоб не впало при першому запуску)
    try:
        if 'app_resource' not in connection.introspection.table_names():
            return
    except Exception:
        return

    # Імпорти всередині функції (щоб уникнути помилок завантаження Django)
    from django.contrib.auth.models import User
    from .models import Resource, Warehouse, Stock, UserRequest, Category

    print("--- [System Init] Починаємо наповнення даних (Матриця Пріоритетів) ---")

    # --- 1. КАТЕГОРІЇ З КРИТИЧНІСТЮ (K_res) ---
    # Медицина найважливіша (1.0), солодощі найменш важливі (0.1)
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

    # --- 2. КОРИСТУВАЧІ ---
    users_data = [
        {'username': 'coord_military', 'email': 'mil@test.com'},  # Координатор військових
        {'username': 'doc_hospital', 'email': 'doc@test.com'},  # Головний лікар
        {'username': 'vol_civilian', 'email': 'vol@test.com'},  # Волонтер по цивільних
    ]

    users_map = {}
    for u_data in users_data:
        user, created = User.objects.get_or_create(
            username=u_data['username'],
            defaults={'email': u_data['email']}
        )
        if created:
            user.set_password('1234')
            user.save()
        users_map[u_data['username']] = user

    # --- 3. РЕСУРСИ ---
    resources_data = [
        {'name': 'Аспірин', 'unit': 'упак', 'cat': 'meds'},
        {'name': 'Бинти стерильні', 'unit': 'шт', 'cat': 'meds'},
        {'name': 'Турнікет', 'unit': 'шт', 'cat': 'meds'},
        {'name': 'Вода (6л)', 'unit': 'бут', 'cat': 'water'},
        {'name': 'Тушонка', 'unit': 'банка', 'cat': 'food'},
        {'name': 'Хліб', 'unit': 'шт', 'cat': 'food'},
        {'name': 'Ковдра тепла', 'unit': 'шт', 'cat': 'clothes'},
        {'name': 'Шоколад', 'unit': 'шт', 'cat': 'other'},
    ]

    resource_objects = {}
    for res in resources_data:
        cat_obj = cats_objs.get(res['cat'])
        obj, _ = Resource.objects.update_or_create(
            name=res['name'],
            defaults={'unit': res['unit'], 'category': cat_obj}
        )
        resource_objects[res['name']] = obj

    # --- 4. СКЛАДИ ---
    w_main, _ = Warehouse.objects.get_or_create(name='Центральний Хаб (Київ)')
    w_east, _ = Warehouse.objects.get_or_create(name='Східний Склад (Харків)')
    w_west, _ = Warehouse.objects.get_or_create(name='Західний Склад (Львів)')

    # --- 5. ЗАПАСИ (STOCKS) ---
    # Створюємо ситуацію дефіциту для цікавого розподілу
    stocks_list = [
        # Медицина (Дефіцит)
        (w_east, 'Аспірин', 50),
        (w_west, 'Аспірин', 10),
    ]

    for warehouse, res_name, amount in stocks_list:
        Stock.objects.update_or_create(
            warehouse=warehouse,
            resource=resource_objects[res_name],
            defaults={'amount': amount}
        )

    # --- 6. ЗАЯВКИ (SCENARIOS) ---
    # Очищаємо старі заявки при перезапуску, щоб бачити чистий експеримент
    UserRequest.objects.all().delete()
    print("Старі заявки очищено.")

    requests_scenarios = [
        ##main test script
        {
            'user': 'coord_military',
            'res': 'Аспірин',
            'qty': 100,
            'purpose': 'military'
        },

        {
            'user': 'doc_hospital',
            'res': 'Аспірин',
            'qty': 50,
            'purpose': 'hospital'
        },
        {
            'user': 'vol_civilian',
            'res': 'Аспірин',
            'qty': 20,
            'purpose': 'refugees'
        },

    ]

    for req in requests_scenarios:
        # Створюємо об'єкт. Метод .save() у моделі автоматично порахує priority!
        UserRequest.objects.create(
            user=users_map[req['user']],
            resource=resource_objects[req['res']],
            quantity_requested=req['qty'],
            purpose=req['purpose'],
            status='new',
            quantity_allocated=0
        )

    print(f"Успішно створено {len(requests_scenarios)} тестових сценаріїв.")
    print("--- [System Init] Готово! ---")