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
    from .models import (
        Resource, Warehouse, Stock, UserRequest,
        Category, Unit, RequestPurpose, UserProfile
    )

    if sender.name != 'app':
        return

    # Перевірка наявності таблиць (захист від помилок при першій міграції)
    tables = connection.introspection.table_names()
    if 'app_unit' not in tables:
        return

    # --- 1. ОДИНИЦІ ВИМІРУ ---
    for name in ['шт', 'кг', 'л', 'упак']:
        Unit.objects.get_or_create(name=name)
    unit_pcs = Unit.objects.get(name='шт')

    # --- 2. КАТЕГОРІЇ ---
    cat_med, _ = Category.objects.update_or_create(
        slug='meds', defaults={'name': 'Медицина', 'criticality': 1.0}
    )

    # --- 3. ТИПИ ПРИЗНАЧЕННЯ ---
    purp_mil, _ = RequestPurpose.objects.update_or_create(
        code='military', defaults={'name': 'Військові потреби', 'weight': 10.0}
    )

    # --- 4. КОРИСТУВАЧІ ---
    admin_user, created = User.objects.get_or_create(
        username='admin@resq.ua',
        defaults={'email': 'admin@resq.ua', 'is_staff': True, 'is_superuser': True}
    )
    if created:
        admin_user.set_password('adminpassword')
        admin_user.save()
        UserProfile.objects.get_or_create(user=admin_user, organization='RESQ HQ')

    # --- 5. РЕСУРСИ ТА СКЛАДИ ---
    res_tourniquet, _ = Resource.objects.get_or_create(
        name='Турнікет', defaults={'unit': unit_pcs, 'category': cat_med}
    )
    wh_main, _ = Warehouse.objects.get_or_create(
        name='Центральний Хаб', location='Київ'
    )
    Stock.objects.update_or_create(
        warehouse=wh_main, resource=res_tourniquet, defaults={'amount': 100}
    )

    # --- 6. ТЕСТОВІ ЗАЯВКИ (З ГЕО-ДАННИМИ) ---
    UserRequest.objects.all().delete()

    # Заявка для Слов'янська (Прифронтова зона)
    UserRequest.objects.create(
        user=admin_user,
        resource=res_tourniquet,
        quantity_requested=30,
        purpose=purp_mil,
        city="Слов'янськ",
        latitude=48.85,
        longitude=37.60,
        status='new'
    )

    # Заявка для Львова (Тил) - створюється через адмінку для порівняння
    print("--- [Success] База даних готова. ---")