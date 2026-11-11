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

    tables = connection.introspection.table_names()
    if 'app_unit' not in tables:
        return

    print("--- Початок ініціалізації стрес-даних з дефіцитом та гео-розподілом ---")

    # --- 1. ОДИНИЦІ ВИМІРУ ---
    units_dict = {
        'pcs': 'шт',
        'box_10': 'коробка (10 шт)',
        'pack_50': 'ящик (50 упак)',
        'bag_15': 'мішок (15 кг)',
        'kit': 'комплект/набір',
        'bottle_pack': 'пак (6 бут)'
    }

    for key, name in units_dict.items():
        Unit.objects.get_or_create(name=name)

    u_pcs = Unit.objects.get(name=units_dict['pcs'])
    u_box10 = Unit.objects.get(name=units_dict['box_10'])
    u_pack50 = Unit.objects.get(name=units_dict['pack_50'])
    u_bag15 = Unit.objects.get(name=units_dict['bag_15'])
    u_kit = Unit.objects.get(name=units_dict['kit'])
    u_bpack = Unit.objects.get(name=units_dict['bottle_pack'])

    # --- 2. КАТЕГОРІЇ ---
    cat_med, _ = Category.objects.update_or_create(slug='meds', defaults={'name': 'Медицина', 'criticality': 1.0})
    cat_food, _ = Category.objects.update_or_create(slug='food', defaults={'name': 'Продукти харчування', 'criticality': 0.7})
    cat_equip, _ = Category.objects.update_or_create(slug='equip', defaults={'name': 'Тактичне обладнання', 'criticality': 0.7})
    cat_cloth, _ = Category.objects.update_or_create(slug='cloth', defaults={'name': 'Одяг та Тепловий захист', 'criticality': 0.5})
    cat_water, _ = Category.objects.update_or_create(slug='water', defaults={'name': 'Вода', 'criticality': 0.9})
    cat_hygiene, _ = Category.objects.update_or_create(slug='hygiene', defaults={'name': 'Санітарія та гігієна', 'criticality': 0.5})

    # --- 3. ТИПИ ПРИЗНАЧЕННЯ ---
    p_refugees, _ = RequestPurpose.objects.update_or_create(code='refugees', defaults={'name': 'ВПО та евакуйовані', 'weight': 0.6})
    p_disaster, _ = RequestPurpose.objects.update_or_create(code='disaster', defaults={'name': 'Зона гуманітарної катастрофи', 'weight': 0.8})
    p_hospital, _ = RequestPurpose.objects.update_or_create(code='hospital', defaults={'name': 'Військові шпиталі / Клініки', 'weight': 0.9})
    p_military, _ = RequestPurpose.objects.update_or_create(code='military', defaults={'name': 'Забезпечення військових частин', 'weight': 1.0})

    # --- 4. КОРИСТУВАЧІ ---
    admin_user, created = User.objects.get_or_create(
        username='admin@resq.ua',
        defaults={'email': 'admin@resq.ua', 'first_name': 'Адміністратор', 'last_name': 'RESQ', 'is_staff': True, 'is_superuser': True}
    )
    if created:
        admin_user.set_password('adminpassword')
        admin_user.save()
        UserProfile.objects.get_or_create(user=admin_user, organization='RESQ Логістика Координація')

    volunteer_user, created = User.objects.get_or_create(
        username='volunteer@resq.ua',
        defaults={'email': 'volunteer@resq.ua', 'first_name': 'Дарія', 'last_name': 'Россоха', 'is_staff': False}
    )
    if created:
        volunteer_user.set_password('volunteerpassword')
        volunteer_user.save()
        UserProfile.objects.get_or_create(user=volunteer_user, organization='Опорний логістичний центр ХПІ')

    # Демо-акаунти завжди підтверджені (інакше адмін не зможе створювати заявки від їхнього імені)
    for demo_user in (admin_user, volunteer_user):
        profile, _ = UserProfile.objects.get_or_create(user=demo_user, defaults={'organization': 'RESQ'})
        if not profile.is_approved:
            profile.is_approved = True
            profile.save(update_fields=['is_approved'])

    # --- 5. РЕСУРСИ ---
    # Звичайні ресурси (розподіляються через LP - Справедливість)
    res_tourniquet, _ = Resource.objects.update_or_create(
        name='Турнікети CAT Gen 7',
        defaults={'unit': u_box10, 'category': cat_med, 'is_strategic': False}
    )
    res_aspirin, _ = Resource.objects.update_or_create(
        name='Аспірин (Медичний кейс)',
        defaults={'unit': u_pack50, 'category': cat_med, 'is_strategic': False}
    )
    res_stew, _ = Resource.objects.update_or_create(
        name='Армійські Сухпайки №4',
        defaults={'unit': u_kit, 'category': cat_food, 'is_strategic': False}
    )
    res_clothes, _ = Resource.objects.update_or_create(
        name='Зимова форма / Фліс',
        defaults={'unit': u_bag15, 'category': cat_cloth, 'is_strategic': False}
    )
    res_water, _ = Resource.objects.update_or_create(
        name='Вода питна ПЕТ',
        defaults={'unit': u_bpack, 'category': cat_water, 'is_strategic': False}
    )
    res_hygiene, _ = Resource.objects.update_or_create(
        name='Гігієнічні бокси',
        defaults={'unit': u_kit, 'category': cat_hygiene, 'is_strategic': False}
    )

    # СТРАТЕГІЧНИЙ РЕСУРС (розподіляється через Тріаж - Жорсткий пріоритет)
    res_generator, _ = Resource.objects.update_or_create(
        name='Дизель-генератор 5.5 кВт',
        defaults={'unit': u_pcs, 'category': cat_equip, 'is_strategic': True}
    )

    # --- 6. ХАБИ (3 склади для географічного маневру) ---
    wh_center, _ = Warehouse.objects.update_or_create(
        name='Центральний Хаб (Київ)', defaults={'location': 'м. Київ, вул. Логістична 1', 'latitude': 50.4501, 'longitude': 30.5234}
    )
    wh_west, _ = Warehouse.objects.update_or_create(
        name='Західний Логістичний Хаб (Львів)', defaults={'location': 'м. Львів, вул. Кільцева 10', 'latitude': 49.8397, 'longitude': 24.0297}
    )
    wh_east, _ = Warehouse.objects.update_or_create(
        name='Східний Опорний Хаб (Дніпро)', defaults={'location': 'м. Дніпро, вул. Набережна 5', 'latitude': 48.4647, 'longitude': 35.0462}
    )

    # --- 7. НАПОВНЕННЯ СКЛАДІВ З РОЗКИДОМ РЕСУРСІВ ТА СТРОКАМИ ПРИДАТНОСТІ ---
    today_date = date.today()
    future_expiry = today_date + timedelta(days=365)
    near_expiry = today_date + timedelta(days=45)

    Stock.objects.all().delete()

    # Турнікети (Запас: 40, Потреба: 75)
    Stock.objects.create(warehouse=wh_center, resource=res_tourniquet, amount=15, expiration_date=None)
    Stock.objects.create(warehouse=wh_west, resource=res_tourniquet, amount=10, expiration_date=None)
    Stock.objects.create(warehouse=wh_east, resource=res_tourniquet, amount=15, expiration_date=None)

    # Генератори - СТРАТЕГІЧНІ (Запас: 5, Потреба: 11)
    Stock.objects.create(warehouse=wh_center, resource=res_generator, amount=2, expiration_date=None)
    Stock.objects.create(warehouse=wh_west, resource=res_generator, amount=2, expiration_date=None)
    Stock.objects.create(warehouse=wh_east, resource=res_generator, amount=1, expiration_date=None)

    # Аспірин (Запас: 25, Потреба: 50)
    Stock.objects.create(warehouse=wh_center, resource=res_aspirin, amount=10, expiration_date=future_expiry)
    Stock.objects.create(warehouse=wh_west, resource=res_aspirin, amount=5, expiration_date=near_expiry)
    Stock.objects.create(warehouse=wh_east, resource=res_aspirin, amount=10, expiration_date=future_expiry)

    # Зимовий одяг (Запас: 30, Потреба: 60)
    Stock.objects.create(warehouse=wh_center, resource=res_clothes, amount=15, expiration_date=None)
    Stock.objects.create(warehouse=wh_west, resource=res_clothes, amount=10, expiration_date=None)
    Stock.objects.create(warehouse=wh_east, resource=res_clothes, amount=5, expiration_date=None)

    # Додаткові ресурси
    Stock.objects.create(warehouse=wh_center, resource=res_stew, amount=100, expiration_date=future_expiry)
    Stock.objects.create(warehouse=wh_center, resource=res_water, amount=200, expiration_date=None)
    Stock.objects.create(warehouse=wh_east, resource=res_water, amount=100, expiration_date=None)

    # --- 8. ОНОВЛЕНА ЧЕРГА ЗАЯВОК ---
    UserRequest.objects.all().delete()

    # --- ГРУПА А: ТУРНІКЕТИ (LP Справедливість) ---
    UserRequest.objects.create(
        user=volunteer_user, resource=res_tourniquet, quantity_requested=40, purpose=p_military,
        city="м. Слов'янськ, Донецька обл.", latitude=48.8521, longitude=37.6061,
        warehouse_address="Відділення №1", warehouse_ref="NP_SLV_1",
        due_date=today_date + timedelta(days=2), status='new'
    )
    UserRequest.objects.create(
        user=volunteer_user, resource=res_tourniquet, quantity_requested=20, purpose=p_hospital,
        city="м. Харків, Харківська обл.", latitude=50.0038, longitude=36.2336,
        warehouse_address="Відділення №4", warehouse_ref="NP_HRK_4",
        due_date=today_date + timedelta(days=3), status='new'
    )
    UserRequest.objects.create(
        user=volunteer_user, resource=res_tourniquet, quantity_requested=15, purpose=p_refugees,
        city="м. Запоріжжя, Запорізька обл.", latitude=47.8388, longitude=35.1396,
        warehouse_address="Відділення №2", warehouse_ref="NP_ZP_2",
        due_date=today_date + timedelta(days=5), status='new'
    )

    # --- ГРУПА Б: ДИЗЕЛЬ-ГЕНЕРАТОРИ (СТРАТЕГІЧНІ -> Тріаж) ---
    # 1. Шпиталь у Краматорську (Найвищий пріоритет)
    UserRequest.objects.create(
        user=volunteer_user, resource=res_generator, quantity_requested=5, purpose=p_hospital,
        city="м. Краматорськ, Донецька обл.", latitude=48.7390, longitude=37.5834,
        warehouse_address="Медична ВЧ 412", warehouse_ref="ADDRESS_DELIVERY",
        due_date=today_date + timedelta(days=2), status='new'
    )
    # 2. Пункт евакуації у Харкові
    UserRequest.objects.create(
        user=volunteer_user, resource=res_generator, quantity_requested=4, purpose=p_refugees,
        city="м. Харків, Харківська обл.", latitude=50.0038, longitude=36.2336,
        warehouse_address="Відділення №12", warehouse_ref="NP_HRK_12",
        due_date=today_date + timedelta(days=6), status='new'
    )
    # 3. Резерв шелтера у Миколаєві
    UserRequest.objects.create(
        user=volunteer_user, resource=res_generator, quantity_requested=2, purpose=p_refugees,
        city="м. Миколаїв, Миколаївська обл.", latitude=46.9750, longitude=31.9946,
        warehouse_address="Відділення №5", warehouse_ref="NP_MYK_5",
        due_date=today_date + timedelta(days=10), status='new'
    )

    # --- ГРУПА В: АСПІРИН (LP Справедливість) ---
    UserRequest.objects.create(
        user=volunteer_user, resource=res_aspirin, quantity_requested=30, purpose=p_military,
        city="м. Покровськ, Донецька обл.", latitude=48.2810, longitude=37.1739,
        warehouse_address="Польовий склад медмайна", warehouse_ref="ADDRESS_DELIVERY",
        due_date=today_date + timedelta(days=2), status='new'
    )
    UserRequest.objects.create(
        user=volunteer_user, resource=res_aspirin, quantity_requested=20, purpose=p_hospital,
        city="м. Суми, Сумська обл.", latitude=50.9077, longitude=34.7981,
        warehouse_address="Відділення №1", warehouse_ref="NP_SUM_1",
        due_date=today_date + timedelta(days=7), status='new'
    )

    # --- ГРУПА Г: ЗИМОВИЙ ОДЯГ (LP Справедливість) ---
    UserRequest.objects.create(
        user=volunteer_user, resource=res_clothes, quantity_requested=35, purpose=p_military,
        city="м. Куп'янськ, Харківська обл.", latitude=49.7082, longitude=37.6148,
        warehouse_address="Штаб ТрО", warehouse_ref="ADDRESS_DELIVERY",
        due_date=today_date + timedelta(days=4), status='new'
    )
    UserRequest.objects.create(
        user=admin_user, resource=res_clothes, quantity_requested=25, purpose=p_refugees,
        city="м. Дніпро, Дніпропетровська обл.", latitude=48.4647, longitude=35.0462,
        warehouse_address="вул. Дарвіна, буд. 12", warehouse_ref="ADDRESS_DELIVERY",
        due_date=today_date + timedelta(days=5), status='new'
    )

    # --- 9. ДОДАТКОВІ ДОВІДНИКИ, РЕСУРСИ (У Т.Ч. СТРАТЕГІЧНІ МЕДИЧНІ), СКЛАДИ ТА ЗАЛИШКИ ---
    from .seed_extra import seed_extra_catalog
    seed_extra_catalog(force_stock=True)

    def _res(name):
        return Resource.objects.get(name=name)

    def _purpose(code):
        return RequestPurpose.objects.get(code=code)

    # Додаткові тестові заявки (усі статуси «нова»), у тому числі на стратегічні медичні ресурси
    extra_requests = [
        # --- Стратегічні медичні (Тріаж) ---
        (volunteer_user, 'Антибіотики широкого спектра', 12, 'hospital', "м. Краматорськ, Донецька обл.", 48.7390, 37.5834, "Медична ВЧ 412", "ADDRESS_DELIVERY", 2),
        (volunteer_user, 'Антибіотики широкого спектра', 8, 'military', "м. Запоріжжя, Запорізька обл.", 47.8388, 35.1396, "Відділення №3", "NP_ZP_3", 4),
        (volunteer_user, 'Інсулін (набір пенів)', 6, 'elderly', "м. Суми, Сумська обл.", 50.9077, 34.7981, "Відділення №2", "NP_SUM_2", 3),
        (admin_user, 'Інфузійні розчини (Рінгер)', 10, 'hospital', "м. Харків, Харківська обл.", 50.0038, 36.2336, "Обласна лікарня", "ADDRESS_DELIVERY", 2),
        (volunteer_user, 'Портативний апарат ШВЛ', 3, 'rescue', "м. Миколаїв, Миколаївська обл.", 46.9750, 31.9946, "Відділення №7", "NP_MYK_7", 3),
        (volunteer_user, 'Кисневий концентратор', 4, 'hospital', "м. Дніпро, Дніпропетровська обл.", 48.4647, 35.0462, "Міська лікарня №9", "ADDRESS_DELIVERY", 5),
        # --- Звичайні ресурси (Справедливість) ---
        (volunteer_user, 'Аптечка IFAK', 30, 'military', "м. Куп'янськ, Харківська обл.", 49.7082, 37.6148, "Штаб ТрО", "ADDRESS_DELIVERY", 4),
        (volunteer_user, 'Бинти гемостатичні', 25, 'rescue', "м. Покровськ, Донецька обл.", 48.2810, 37.1739, "Відділення №1", "NP_PKR_1", 3),
        (admin_user, 'Суха молочна суміш', 18, 'children', "м. Одеса, Одеська обл.", 46.4825, 30.7233, "Відділення №15", "NP_ODS_15", 6),
        (volunteer_user, 'Підгузки дитячі', 12, 'children', "м. Миколаїв, Миколаївська обл.", 46.9750, 31.9946, "Відділення №5", "NP_MYK_5", 7),
        (volunteer_user, 'Спальні мішки', 40, 'shelters', "м. Запоріжжя, Запорізька обл.", 47.8388, 35.1396, "Пункт незламності №4", "ADDRESS_DELIVERY", 5),
        (volunteer_user, 'Намети 6-місні', 6, 'refugees', "м. Дніпро, Дніпропетровська обл.", 48.4647, 35.0462, "Відділення №21", "NP_DNP_21", 8),
        (volunteer_user, 'Дизельне паливо', 400, 'rescue', "м. Харків, Харківська обл.", 50.0038, 36.2336, "База ДСНС", "ADDRESS_DELIVERY", 3),
        (admin_user, 'Портативна електростанція', 5, 'shelters', "м. Суми, Сумська обл.", 50.9077, 34.7981, "Пункт незламності №2", "ADDRESS_DELIVERY", 4),
    ]
    for owner, res_name, qty, purpose_code, city, lat, lon, address, ref, days in extra_requests:
        UserRequest.objects.create(
            user=owner, resource=_res(res_name), quantity_requested=qty, purpose=_purpose(purpose_code),
            city=city, latitude=lat, longitude=lon, warehouse_address=address, warehouse_ref=ref,
            due_date=today_date + timedelta(days=days), status='new'
        )

    print("--- [Success] База даних успішно наповнена дефіцитними логістичними сценаріями! ---")