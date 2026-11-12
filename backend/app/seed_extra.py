"""Додаткові довідники та стартові залишки (використовуються і в apps.py, і в команді seed_extra_catalog)."""
from datetime import date, timedelta

UNITS = ['кг', 'л', 'пара', 'рулон', 'упаковка (20 шт)', 'упаковка (100 шт)']

CATEGORIES = [
    # slug, назва, критичність
    ('power', 'Енергетика та зв’язок', 0.8),
    ('shelter', 'Тимчасове житло та сон', 0.7),
    ('kids', 'Дитячі товари', 0.8),
    ('fuel', 'Паливо', 0.6),
    ('repair', 'Інструменти та ремонт', 0.4),
]

PURPOSES = [
    # code, назва, вага
    ('children', 'Дитячі будинки та школи', 0.7),
    ('elderly', 'Літні люди та маломобільні групи', 0.7),
    ('shelters', 'Пункти незламності / укриття', 0.75),
    ('rescue', 'Рятувальні служби (ДСНС)', 0.9),
]

WAREHOUSES = [
    # назва, локація, широта, довгота
    ('Південний Хаб (Одеса)', 'м. Одеса, вул. Портова 7', 46.4825, 30.7233),
    ('Північно-Східний Хаб (Харків)', 'м. Харків, вул. Індустріальна 12', 49.9935, 36.2304),
    ('Центральний Опорний Хаб (Вінниця)', 'м. Вінниця, вул. Складська 3', 49.2328, 28.4810),
]

# назва, одиниця, slug категорії, стратегічний?, термін придатності (днів) або None
RESOURCES = [
    # --- Медицина ---
    ('Аптечка IFAK', 'комплект/набір', 'meds', False, 730),
    ('Бинти гемостатичні', 'коробка (10 шт)', 'meds', False, 900),
    ('Парацетамол', 'ящик (50 упак)', 'meds', False, 540),
    # Стратегічні медичні ресурси (дефіцитні, розподіляються через Тріаж)
    ('Антибіотики широкого спектра', 'ящик (50 упак)', 'meds', True, 480),
    ('Інсулін (набір пенів)', 'коробка (10 шт)', 'meds', True, 270),
    ('Інфузійні розчини (Рінгер)', 'ящик (50 упак)', 'meds', True, 600),
    ('Портативний апарат ШВЛ', 'шт', 'meds', True, None),
    ('Кисневий концентратор', 'шт', 'meds', True, None),
    # --- Гігієна / їжа / діти ---
    ('Антисептик для рук', 'упаковка (20 шт)', 'hygiene', False, 700),
    ('Консерви м’ясні', 'ящик (50 упак)', 'food', False, 600),
    ('Крупа гречана', 'мішок (15 кг)', 'food', False, 500),
    ('Суха молочна суміш', 'упаковка (20 шт)', 'kids', False, 365),
    ('Підгузки дитячі', 'упаковка (100 шт)', 'kids', False, None),
    # --- Житло, одяг, енергетика, паливо, ремонт ---
    ('Спальні мішки', 'шт', 'shelter', False, None),
    ('Термоковдри', 'упаковка (20 шт)', 'shelter', False, None),
    ('Намети 6-місні', 'шт', 'shelter', False, None),
    ('Зимові шкарпетки', 'пара', 'cloth', False, None),
    ('Рації переносні', 'шт', 'power', False, None),
    ('Портативна електростанція', 'шт', 'power', True, None),
    ('Дизельне паливо', 'л', 'fuel', True, None),
    ('Бензин А-95', 'л', 'fuel', False, None),
    ('Плівка для вікон', 'рулон', 'repair', False, None),
    ('Набір інструментів', 'комплект/набір', 'repair', False, None),
]

# Стартові обсяги (комбінуються по колу для різних пар «ресурс × склад»)
BASE_AMOUNTS = [60, 25, 90, 40, 15, 120, 30, 8]

# Ліміти на одну заявку (сумарно на заявника). Для стратегічних ресурсів - суворіші.
MAX_PER_REQUEST = {
    'Дизель-генератор 5.5 кВт': 10,
    'Портативна електростанція': 10,
    'Портативний апарат ШВЛ': 5,
    'Кисневий концентратор': 10,
    'Інсулін (набір пенів)': 20,
    'Антибіотики широкого спектра': 50,
    'Інфузійні розчини (Рінгер)': 60,
    'Дизельне паливо': 1000,
    'Бензин А-95': 1000,
    'Турнікети CAT Gen 7': 100,
    'Аспірин (Медичний кейс)': 100,
    'Аптечка IFAK': 100,
    'Намети 6-місні': 50,
}


def seed_extra_catalog(force_stock=False):
    """
    Додає додаткові довідники, ресурси та залишки. Нічого не видаляє.
    force_stock=False - залишки лише для щойно доданих ресурсів (безпечно для запуску вручну).
    force_stock=True  - залишки для всіх додаткових ресурсів, яким бракує позицій (після очищення складів).
    """
    from .models import Unit, Category, Resource, Warehouse, RequestPurpose, Stock

    created = {'units': 0, 'categories': 0, 'purposes': 0, 'warehouses': 0, 'resources': 0, 'stocks': 0}

    for name in UNITS:
        _, c = Unit.objects.get_or_create(name=name)
        created['units'] += c

    for slug, name, crit in CATEGORIES:
        _, c = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'criticality': crit})
        created['categories'] += c

    for code, name, weight in PURPOSES:
        _, c = RequestPurpose.objects.get_or_create(code=code, defaults={'name': name, 'weight': weight})
        created['purposes'] += c

    for name, location, lat, lon in WAREHOUSES:
        _, c = Warehouse.objects.get_or_create(
            name=name, defaults={'location': location, 'latitude': lat, 'longitude': lon}
        )
        created['warehouses'] += c

    warehouses = list(Warehouse.objects.order_by('id'))
    today = date.today()

    for i, (name, unit_name, cat_slug, strategic, shelf_days) in enumerate(RESOURCES):
        unit = Unit.objects.get(name=unit_name)
        category = Category.objects.get(slug=cat_slug)
        resource, c = Resource.objects.get_or_create(
            name=name, defaults={'unit': unit, 'category': category, 'is_strategic': strategic}
        )
        created['resources'] += c

        if not (c or (force_stock and not Stock.objects.filter(resource=resource).exists())):
            continue

        for j, wh in enumerate(warehouses):
            # Не кладемо ресурс на всі склади - так розподілу є де маневрувати
            if (i + j) % 3 == 2:
                continue
            amount = BASE_AMOUNTS[(i + j) % len(BASE_AMOUNTS)]
            if strategic:
                amount = max(2, amount // 10)
            expiry = today + timedelta(days=shelf_days) if shelf_days else None
            _, sc = Stock.objects.get_or_create(
                warehouse=wh, resource=resource,
                defaults={'amount': amount, 'expiration_date': expiry},
            )
            created['stocks'] += sc

    # Ліміти на одну заявку: виставляємо лише там, де їх ще не задано вручну
    for res_name, cap in MAX_PER_REQUEST.items():
        Resource.objects.filter(name=res_name, max_per_request__isnull=True).update(max_per_request=cap)

    return created
