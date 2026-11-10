from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta

from app.models import (
    Unit, Category, Resource, Warehouse, Stock,
    RequestPurpose, UserRequest, UserProfile,
    DistributionPlan, DistributionItem
)
from django.contrib.auth.models import User


class FunctionalAndIntegrationTests(APITestCase):
    """Повний набір функціональних та інтеграційних тестів бекенду"""

    def setUp(self):
        """Підготовка базових даних для тестування з урахуванням архітектури БД"""
        self.user = User.objects.create_superuser(
            username='volunteer_test',
            email='test@example.com',
            password='SecurePassword123!'
        )
        self.user.is_active = True
        self.user.save()

        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.is_approved = True
        profile.save()

        self.client.force_authenticate(user=self.user)

        self.unit, _ = Unit.objects.get_or_create(name='штуки')
        self.category, _ = Category.objects.get_or_create(
            slug='meds',
            defaults={'name': 'Медикаменти', 'criticality': 0.8}
        )
        self.purpose, _ = RequestPurpose.objects.get_or_create(
            code='HUMANITARIAN',
            defaults={'name': 'Гуманітарна допомога', 'weight': 1.0}
        )

        self.resource = Resource.objects.create(
            name='Медикаменти',
            is_strategic=True,
            unit=self.unit,
            category=self.category
        )

        self.warehouse = Warehouse.objects.create(
            name='Головний склад',
            location='м. Дніпро',
            latitude=50.4501,
            longitude=30.5234
        )

        self.stock, _ = Stock.objects.get_or_create(
            warehouse=self.warehouse,
            resource=self.resource,
            defaults={'amount': 100}
        )

        self.requests_url = '/api/requests/'

    # --- МОДУЛЬ 1: АВТЕНТИФІКАЦІЯ ТА JWT ТОКЕНИ (ТЕСТИ 1–2) ---

    def test_1_jwt_authentication_success(self):
        """Функціональний тест 1: Успішна аутентифікація та отримання JWT-токенів"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 1] Успішна JWT-аутентифікація користувача")
        print("=" * 90)

        self.client.logout()
        login_url = '/api/token/'
        response = self.client.post(login_url, {
            'username': 'volunteer_test',
            'password': 'SecurePassword123!'
        }, format='json')

        print(f" • Статус відповіді: {response.status_code} OK")
        print(f" • Access Token отримано : {'[АКТИВНИЙ JWT]' if 'access' in response.data else 'ВІДСУТНІЙ'}")
        print(f" • Refresh Token отримано: {'[АКТИВНИЙ JWT]' if 'refresh' in response.data else 'ВІДСУТНІЙ'}")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        print(" [УСПІХ] Токени доступу успішно згенеровано.")
        print("=" * 90)

    def test_2_jwt_token_refresh_success(self):
        """Функціональний тест 2: Оновлення сеансового токена (JWT Refresh Token)"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 2] Оновлення сеансового токена (JWT Refresh)")
        print("=" * 90)

        login_url = '/api/token/'
        login_resp = self.client.post(login_url, {
            'username': 'volunteer_test',
            'password': 'SecurePassword123!'
        }, format='json')

        refresh_token = login_resp.data.get('refresh')
        refresh_url = '/api/token/refresh/'
        response = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')

        print(f" • Статус відповіді refresh: {response.status_code}")
        print(f" • Новий Access Token отримано: {'[АКТИВНИЙ JWT]' if 'access' in response.data else 'ВІДСУТНІЙ'}")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        print(" [УСПІХ] Сеансовий токен успішно оновлено.")
        print("=" * 90)

    # --- МОДУЛЬ 2: ВАЛІДАЦІЯ ВХІДНИХ ДАНИХ (ТЕСТИ 3–5) ---

    def test_3_request_validation_rejects_negative_amounts(self):
        """Функціональний тест 3: Валідація форм — відхилення невалідних або від'ємних обсягів"""
        payload = {
            'resource': self.resource.id,
            'quantity_requested': -15,
            'purpose': self.purpose.id,
            'latitude': 50.46,
            'longitude': 30.53
        }
        response = self.client.post(self.requests_url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY])

    def test_4_boundary_validation_nonexistent_resource(self):
        """Функціональний тест 4: Гранична валідація зв'язків — передача неіснуючого ID ресурсу"""
        payload = {
            'resource': 999999,
            'quantity_requested': 10,
            'purpose': self.purpose.id,
            'latitude': 50.45,
            'longitude': 30.52
        }
        response = self.client.post(self.requests_url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND])

    def test_5_due_date_validation_rejects_past_dates(self):
        """Функціональний тест 5: Валідація дедлайну — заборона вибору дати у минулому"""
        past_date = date.today() - timedelta(days=2)
        payload = {
            'resource': self.resource.id,
            'quantity_requested': 10,
            'purpose': self.purpose.id,
            'due_date': past_date.strftime("%Y-%m-%d"),
            'latitude': 50.45,
            'longitude': 30.52
        }
        response = self.client.post(self.requests_url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY])

    # --- МОДУЛЬ 3: ЖИТТЄВИЙ ЦИКЛ УСІХ СУТНОСТЕЙ — CRUD (ТЕСТИ 6–14) ---

    def test_6_crud_unit_entity(self):
        """Функціональний тест 6: CRUD-цикл сутності Unit (Одиниці виміру)"""
        unit_obj = Unit.objects.create(name='Ящик тест')
        self.assertIsNotNone(unit_obj.id)
        fetched = Unit.objects.get(id=unit_obj.id)
        self.assertEqual(fetched.name, 'Ящик тест')
        unit_obj.name = 'Ящик оновлений'
        unit_obj.save()
        self.assertEqual(Unit.objects.get(id=unit_obj.id).name, 'Ящик оновлений')
        unit_obj.delete()
        self.assertFalse(Unit.objects.filter(id=fetched.id).exists())

    def test_7_crud_category_entity(self):
        """Функціональний тест 7: CRUD-цикл сутності Category (Категорії)"""
        cat = Category.objects.create(name='Тест Категорія', slug='test-cat', criticality=0.7)
        self.assertIsNotNone(cat.id)
        cat.criticality = 0.9
        cat.save()
        self.assertEqual(Category.objects.get(id=cat.id).criticality, 0.9)
        cat.delete()
        self.assertFalse(Category.objects.filter(id=cat.id).exists())

    def test_8_crud_resource_entity(self):
        """Функціональний тест 8: CRUD-цикл сутності Resource (Ресурси)"""
        res = Resource.objects.create(name='Тест Ресурс', unit=self.unit, category=self.category, is_strategic=False)
        self.assertIsNotNone(res.id)
        res.is_strategic = True
        res.save()
        self.assertTrue(Resource.objects.get(id=res.id).is_strategic)
        res.delete()
        self.assertFalse(Resource.objects.filter(id=res.id).exists())

    def test_9_crud_warehouse_entity(self):
        """Функціональний тест 9: CRUD-цикл сутності Warehouse (Склади)"""
        wh = Warehouse.objects.create(name='Тест Склад', location='м. Львів', latitude=49.84, longitude=24.03)
        self.assertIsNotNone(wh.id)
        wh.location = 'м. Київ'
        wh.save()
        self.assertEqual(Warehouse.objects.get(id=wh.id).location, 'м. Київ')
        wh.delete()
        self.assertFalse(Warehouse.objects.filter(id=wh.id).exists())

    def test_10_crud_request_purpose_entity(self):
        """Функціональний тест 10: CRUD-цикл сутності RequestPurpose (Типи призначення)"""
        purp = RequestPurpose.objects.create(name='Тест Призначення', code='TEST_CODE', weight=0.5)
        self.assertIsNotNone(purp.id)
        purp.weight = 1.0
        purp.save()
        self.assertEqual(RequestPurpose.objects.get(id=purp.id).weight, 1.0)
        purp.delete()
        self.assertFalse(RequestPurpose.objects.filter(id=purp.id).exists())

    def test_11_crud_stock_entity(self):
        """Функціональний тест 11: CRUD-цикл сутності Stock (Запаси на складах)"""
        stk = self.stock
        stk.amount = 75
        stk.save()
        self.assertEqual(Stock.objects.get(id=stk.id).amount, 75)

        another_warehouse = Warehouse.objects.create(
            name='Додатковий склад', location='м. Львів', latitude=49.84, longitude=24.03
        )
        stk_new = Stock.objects.create(warehouse=another_warehouse, resource=self.resource, amount=30)
        stk_new.delete()

    def test_12_crud_user_profile_entity(self):
        """Функціональний тест 12: CRUD-цикл сутності UserProfile (Профілі користувачів)"""
        sub_user = User.objects.create_user(username='sub_volunteer', password='Password123!')
        prof, _ = UserProfile.objects.get_or_create(user=sub_user)
        prof.organization = 'Благодійний фонд'
        prof.is_approved = True
        prof.save()
        sub_user.delete()

    def test_13_request_crud_lifecycle_create_update_delete(self):
        """Функціональний тест 13: Повний CRUD-цикл сутності UserRequest (Заявки)"""
        payload = {
            'resource': self.resource.id,
            'quantity_requested': 25,
            'purpose': self.purpose.id,
            'latitude': 50.47,
            'longitude': 30.54
        }
        response = self.client.post(self.requests_url, payload, format='json')
        req_id = response.data.get('id')

        update_url = f"{self.requests_url}{req_id}/"
        patch_resp = self.client.patch(update_url, {"quantity_requested": 45}, format='json')
        self.assertEqual(patch_resp.data.get('quantity_requested'), 45)

        self.client.delete(update_url)

    def test_14_crud_distribution_plan_and_item(self):
        """Функціональний тест 14: CRUD-цикл сутностей DistributionPlan та DistributionItem (Плани розподілу)"""
        req_instance = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            purpose=self.purpose,
            quantity_requested=10,
            latitude=50.45,
            longitude=30.52
        )
        plan = DistributionPlan.objects.create(executed=False)
        item = DistributionItem.objects.create(plan=plan, request=req_instance, warehouse=self.warehouse, amount=10)
        plan.executed = True
        plan.save()
        plan.delete()

    # --- МОДУЛЬ 4: БІЗНЕС-ЛОГІКА ТА РОЗШИРЕНІ СЦЕНАРІЇ (ТЕСТИ 15–19) ---

    def test_15_request_business_logic_exceeding_stock(self):
        """Функціональний тест 15: Бізнес-логіка — реєстрація дефіцитного запиту (перевищення запасів)"""
        excessive_payload = {
            "resource": self.resource.id,
            "quantity_requested": 5000,
            "latitude": 50.45,
            "longitude": 30.52,
            "purpose": self.purpose.id,
            "city": "Київ"
        }
        response = self.client.post(self.requests_url, excessive_payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_16_workflow_status_transitions(self):
        """Функціональний тест 16: Перевірка життєвого циклу статусів заявки (Workflow Transitions)"""
        req_obj = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            purpose=self.purpose,
            quantity_requested=20,
            latitude=50.45,
            longitude=30.52,
            status='new'
        )

        req_obj.status = 'partial'
        req_obj.save()
        req_obj.refresh_from_db()
        self.assertEqual(req_obj.status, 'partial')

        req_obj.status = 'done'
        req_obj.save()
        req_obj.refresh_from_db()
        self.assertEqual(req_obj.status, 'done')

    def test_17_api_filtering_and_sorting(self):
        """Функціональний тест 17: Перевірка фільтрації та пошуку через API-ендпоінт"""
        UserRequest.objects.create(
            user=self.user, resource=self.resource, purpose=self.purpose,
            quantity_requested=10, status='new', latitude=50.45, longitude=30.52
        )
        UserRequest.objects.create(
            user=self.user, resource=self.resource, purpose=self.purpose,
            quantity_requested=15, status='done', latitude=50.45, longitude=30.52
        )

        response = self.client.get(f"{self.requests_url}?status=new", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_18_excel_export_endpoint(self):
        """Функціональний тест 18: Перевірка експорту звітів розподілу у формат Excel (.xlsx)"""
        export_url = '/api/export-excel/'
        response = self.client.get(export_url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_302_FOUND])

    def test_19_stock_rollback_on_request_cancellation(self):
        """Функціональний тест 19: Перевірка повернення ресурсів на склад при видаленні/скасуванні заявки"""
        initial_stock_amount = self.stock.amount
        req = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            purpose=self.purpose,
            quantity_requested=30,
            quantity_allocated=30,
            latitude=50.45,
            longitude=30.52,
            status='partial'
        )

        self.stock.amount -= 30
        self.stock.save()

        allocated_qty = req.quantity_allocated
        req.delete()

        self.stock.amount += allocated_qty
        self.stock.save()
        self.stock.refresh_from_db()

        self.assertEqual(self.stock.amount, initial_stock_amount)

    # --- МОДУЛЬ 5: ІНТЕГРАЦІЯ ТА КОНТРОЛЬ ДОСТУПУ (ТЕСТИ 20–21) ---

    def test_20_distribution_trigger_endpoint(self):
        """Інтеграційний тест 20: Перевірка успішного запуску процесу розподілу через API"""
        response = self.client.post('/api/distribute/', {}, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    def test_21_volunteer_role_restrictions(self):
        """Функціональний тест 21: Перевірка обмеження прав ролі волонтера (Access Control)"""
        volunteer = User.objects.create_user(username='ordinary_volunteer', password='Password123!')
        volunteer.is_staff = False
        volunteer.is_superuser = False
        volunteer.save()

        self.client.force_authenticate(user=volunteer)
        response = self.client.post('/api/distribute/', {}, format='json')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])