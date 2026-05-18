import time
from datetime import date, timedelta
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

    # Захист від помилок при першій міграції бази даних
    tables = connection.introspection.table_names()
    if 'app_unit' not in tables:
        return

    print("--- Початок ініціалізації даних ---")

    # --- 1. ОДИНИЦІ ВИМІРУ ---
    for name in ['шт', 'кг', 'л', 'упак', 'бут', 'банка']:
        Unit.objects.get_or_create(name=name)

    u_pcs = Unit.objects.get(name='шт')
    u_kg = Unit.objects.get(name='кг')
    u_l = Unit.objects.get(name='л')
    u_pack = Unit.objects.get(name='упак')
    u_bot = Unit.objects.get(name='бут')
    u_can = Unit.objects.get(name='банка')

    # --- 2. КАТЕГОРІЇ  ---
    cat_med, _ = Category.objects.update_or_create(slug='meds', defaults={'name': 'Медицина', 'criticality': 1.0})
    cat_food, _ = Category.objects.update_or_create(slug='food',
                                                    defaults={'name': 'Продукти харчування', 'criticality': 0.7})
    cat_equip, _ = Category.objects.update_or_create(slug='equip', defaults={'name': 'Обладнання', 'criticality': 0.7})
    cat_cloth, _ = Category.objects.update_or_create(slug='cloth',
                                                     defaults={'name': 'Одяг та Тепло', 'criticality': 0.5})
    cat_water, _ = Category.objects.update_or_create(slug='water', defaults={'name': 'Вода питна', 'criticality': 0.9})
    cat_hygiene, _ = Category.objects.update_or_create(slug='hygiene',
                                                       defaults={'name': 'Засоби гігієни', 'criticality': 0.5})

    # --- 3. ТИПИ ПРИЗНАЧЕННЯ ---
    p_refugees, _ = RequestPurpose.objects.update_or_create(code='refugees',
                                                            defaults={'name': 'ВПО та біженці', 'weight': 6.0})
    p_disaster, _ = RequestPurpose.objects.update_or_create(code='disaster',
                                                            defaults={'name': 'Зона лиха', 'weight': 8.0})
    p_hospital, _ = RequestPurpose.objects.update_or_create(code='hospital',
                                                            defaults={'name': 'Медичні заклади', 'weight': 9.0})
    p_military, _ = RequestPurpose.objects.update_or_create(code='military',
                                                            defaults={'name': 'Військові потреби', 'weight': 10.0})

    # --- 4. АДМІНІСТРАТОР ТА ТЕСТОВІ КОРИСТУВАЧІ ---
    admin_user, created = User.objects.get_or_create(
        username='admin@resq.ua',
        defaults={'email': 'admin@resq.ua', 'first_name': 'Адміністратор', 'last_name': 'RESQ', 'is_staff': True,
                  'is_superuser': True}
    )
    if created:
        admin_user.set_password('adminpassword')
        admin_user.save()
        UserProfile.objects.get_or_create(user=admin_user, organization='RESQ Логістика Центр')

    volunteer_user, created = User.objects.get_or_create(
        username='volunteer@resq.ua',
        defaults={'email': 'volunteer@resq.ua', 'first_name': 'Дарія', 'last_name': 'Росоха', 'is_staff': False}
    )
    if created:
        volunteer_user.set_password('volunteerpassword')
        volunteer_user.save()
        UserProfile.objects.get_or_create(user=volunteer_user, organization='Східний Волонтерський Штаб')

    # --- 5. РЕСУРСИ  ---
    res_tourniquet, _ = Resource.objects.get_or_create(name='Турнікет', defaults={'unit': u_pcs, 'category': cat_med})
    res_aspirin, _ = Resource.objects.get_or_create(name='Аспірин', defaults={'unit': u_pack, 'category': cat_med})
    res_stew, _ = Resource.objects.get_or_create(name='Тушонка', defaults={'unit': u_can, 'category': cat_food})
    res_blanket, _ = Resource.objects.get_or_create(name='Ковдра', defaults={'unit': u_pcs, 'category': cat_cloth})
    res_generator, _ = Resource.objects.get_or_create(name='Генератор', defaults={'unit': u_pcs, 'category': cat_equip})
    res_water, _ = Resource.objects.get_or_create(name='Вода 1.5л', defaults={'unit': u_bot, 'category': cat_water})
    res_hygiene, _ = Resource.objects.get_or_create(name='Гігієнічний набір №1',
                                                    defaults={'unit': u_pcs, 'category': cat_hygiene})

    # --- 6. ВЕЛИКІ ОПОРНІ ЛОГІСТИЧНІ ХАБИ  ---
    wh_center, _ = Warehouse.objects.update_or_create(
        name='Центральний Хаб (Київ)',
        defaults={'location': 'м. Київ, вул. Логістична 1', 'latitude': 50.4501, 'longitude': 30.5234}
    )
    wh_west, _ = Warehouse.objects.update_or_create(
        name='Західний Логістичний Хаб (Львів)',
        defaults={'location': 'м. Львів, вул. Кільцева 10', 'latitude': 49.8397, 'longitude': 24.0297}
    )
    wh_east, _ = Warehouse.objects.update_or_create(
        name='Східний Опорний Хаб (Дніпро)',
        defaults={'location': 'м. Дніпро, вул. Набережна 5', 'latitude': 48.4647, 'longitude': 35.0462}
    )

    # --- 7. НАПОВНЕННЯ СКЛАДІВ ЗАПАСАМИ  ---
    # Київ (Центр)
    Stock.objects.update_or_create(warehouse=wh_center, resource=res_generator, defaults={'amount': 12})
    Stock.objects.update_or_create(warehouse=wh_center, resource=res_tourniquet, defaults={'amount': 250})
    Stock.objects.update_or_create(warehouse=wh_center, resource=res_stew, defaults={'amount': 1500})
    Stock.objects.update_or_create(warehouse=wh_center, resource=res_water, defaults={'amount': 2000})

    # Львів (Захід)
    Stock.objects.update_or_create(warehouse=wh_west, resource=res_blanket, defaults={'amount': 650})
    Stock.objects.update_or_create(warehouse=wh_west, resource=res_hygiene, defaults={'amount': 400})
    Stock.objects.update_or_create(warehouse=wh_west, resource=res_stew, defaults={'amount': 800})
    Stock.objects.update_or_create(warehouse=wh_west, resource=res_aspirin, defaults={'amount': 150})

    # Дніпро (Схід — близько до фронту)
    Stock.objects.update_or_create(warehouse=wh_east, resource=res_tourniquet, defaults={'amount': 500})
    Stock.objects.update_or_create(warehouse=wh_east, resource=res_aspirin, defaults={'amount': 300})
    Stock.objects.update_or_create(warehouse=wh_east, resource=res_water, defaults={'amount': 1200})
    Stock.objects.update_or_create(warehouse=wh_east, resource=res_generator, defaults={'amount': 3})

    # --- 8. ОНОВЛЕНА ЧЕРГА ЗАЯВОК ---
    UserRequest.objects.all().delete()

    today = date.today()

    # КРИТИЧНО ТЕРМІНОВІ ЗАЯВКИ (Дедлайн 2-3 дні)
    UserRequest.objects.create(
        user=volunteer_user, resource=res_tourniquet, quantity_requested=120, purpose=p_military,
        city="м. Слов'янськ, Донецька обл.", latitude=48.8521, longitude=37.6061,
        warehouse_address="Відділення №1", warehouse_ref="NP_SLV_1",
        due_date=today + timedelta(days=2), status='new'
    )

    UserRequest.objects.create(
        user=volunteer_user, resource=res_generator, quantity_requested=4, purpose=p_hospital,
        city="м. Харків, Харківська обл.", latitude=50.0038, longitude=36.2336,
        warehouse_address="Відділення №4", warehouse_ref="NP_HRK_4",
        due_date=today + timedelta(days=3), status='new'
    )

    # СТАНДАРТНІ ЗАЯВКИ (Дедлайн 5 днів)
    UserRequest.objects.create(
        user=volunteer_user, resource=res_water, quantity_requested=800, purpose=p_disaster,
        city="м. Запоріжжя, Запорізька обл.", latitude=47.8388, longitude=35.1396,
        warehouse_address="Відділення №2", warehouse_ref="NP_ZP_2",
        due_date=today + timedelta(days=5), status='new'
    )

    UserRequest.objects.create(
        user=admin_user, resource=res_stew, quantity_requested=500, purpose=p_refugees,
        city="м. Дніпро, Дніпропетровська обл.", latitude=48.4647, longitude=35.0462,
        warehouse_address="вул. Дарвіна, буд. 12", warehouse_ref="ADDRESS_DELIVERY",
        due_date=today + timedelta(days=5), status='new'
    )

    #  ПЛАНОВІ ЗАЯВКИ (Дедлайн 10 - 14 днів)
    UserRequest.objects.create(
        user=volunteer_user, resource=res_blanket, quantity_requested=200, purpose=p_refugees,
        city="м. Миколаїв, Миколаївська обл.", latitude=46.9750, longitude=31.9946,
        warehouse_address="Відділення №5", warehouse_ref="NP_MYK_5",
        due_date=today + timedelta(days=10), status='new'
    )

    UserRequest.objects.create(
        user=volunteer_user, resource=res_hygiene, quantity_requested=150, purpose=p_refugees,
        city="м. Харків, Харківська обл.", latitude=50.0038, longitude=36.2336,
        warehouse_address="Відділення №12", warehouse_ref="NP_HRK_12",
        due_date=today + timedelta(days=14), status='new'
    )

    UserRequest.objects.create(
        user=volunteer_user, resource=res_aspirin, quantity_requested=80, purpose=p_hospital,
        city="м. Слов'янськ, Донецька обл.", latitude=48.8521, longitude=37.6061,
        warehouse_address="Відділення №1", warehouse_ref="NP_SLV_1",
        due_date=today + timedelta(days=7), status='new'
    )

    print("--- [Success] База даних успішно наповнена тестовими хабами, дедлайнами та номенклатурою. ---")