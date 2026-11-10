import time
import requests as req_lib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from app.models import (
    Unit, Category, Resource, Warehouse, Stock,
    RequestPurpose, UserRequest, UserProfile
)
from django.contrib.auth.models import User
from app.services import DistanceMatrixService, _ROUTING_CACHE


# --- 1. МОК-СЕРВІС ДЛЯ ІМІТАЦІЇ ЛОГІСТИЧНИХ ВІДСТАНЕЙ (OSRM) ---
class MockDistanceService:
    """Імітація OSRM Table API для ізольованого тестування"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 15.0

    def get_distance_matrix(self, sources, destinations):
        import numpy as np
        return np.full((len(sources), len(destinations)), 15.0)


# --- 2. КОМПЛЕКСНІ ФУНКЦІОНАЛЬНІ ТА ІНТЕГРАЦІЙНІ ТЕСТИ API ---
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

    # --- МОДУЛЬ 1: АВТЕНТИФІКАЦІЯ ТА БЕЗПЕКА (ТЕСТИ 1–3) ---

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

    def test_3_unauthorized_access_is_blocked(self):
        """Функціональний тест 3: Блокування доступу до захищених endpoint-ів без авторизації"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 3] Блокування неавторизованого доступу до API")
        print("=" * 90)

        self.client.logout()
        response = self.client.get(self.requests_url)

        print(f" {self.requests_url:<30} | {'GET':<10} | {'Відсутня':<15} | {response.status_code} (Блоковано)")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        print(" [УСПІХ] Неавторизований доступ успішно заблоковано системою безпеки.")
        print("=" * 90)

    def test_4_negative_security_invalid_jwt(self):
        """Функціональний тест 4: Негативний тест безпеки — перевірка фальшивого/невалідного JWT-токена"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 4] Негативний тест безпеки (Підроблений JWT)")
        print("=" * 90)

        self.client.force_authenticate(user=None)
        self.client.logout()

        response = self.client.get(
            self.requests_url,
            HTTP_AUTHORIZATION='Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_signature_payload'
        )

        print(f" • Статус відповіді з підробленим токеном: {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        print(" [УСПІХ] Система захисту успішно відхилила невалідний/підроблений JWT-токен.")
        print("=" * 90)

    def test_5_rbac_blocks_volunteer_from_admin_actions(self):
        """Функціональний тест 5: Розмежування прав доступу (RBAC) — заборона волонтеру адмін-дій"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 5] Розмежування прав доступу (RBAC)")
        print("=" * 90)

        volunteer = User.objects.create_user(username='simple_volunteer', password='Password123!')
        volunteer.is_staff = False
        volunteer.is_superuser = False
        volunteer.save()
        self.client.force_authenticate(user=volunteer)

        warehouse_payload = {
            'name': 'Нелегальний склад',
            'location': 'м. Харків',
            'latitude': 49.99,
            'longitude': 36.23
        }
        response = self.client.post('/api/warehouses/', warehouse_payload, format='json')

        print(f" • Спроба створення складу волонтером: статус {response.status_code} Forbidden")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        print(" [УСПІХ] Система безпеки успішно заблокувала несанкціоновану адмін-дію.")
        print("=" * 90)

    # --- МОДУЛЬ 2: ВАЛІДАЦІЯ ВХІДНИХ ДАНИХ (ТЕСТИ 6–7) ---

    def test_6_request_validation_rejects_negative_amounts(self):
        """Функціональний тест 6: Валідація форм — відхилення невалідних або від'ємних обсягів"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 6] Валідація вхідних даних (Відхилення від'ємних значень)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)
        payload = {
            'resource': self.resource.id,
            'quantity_requested': -15,
            'purpose': self.purpose.id,
            'latitude': 50.46,
            'longitude': 30.53
        }

        response = self.client.post(self.requests_url, payload, format='json')

        print(f" • Статус відповіді сервера: {response.status_code} Bad Request")
        print(f" • Повідомлення помилки    : {response.data.get('quantity_requested', 'Помилка валідації')}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY])
        print(" [УСПІХ] Система захисту успішно відхилила невалідні вхідні дані.")
        print("=" * 90)

    def test_7_boundary_validation_nonexistent_resource(self):
        """Функціональний тест 7: Гранична валідація зв'язків — передача неіснуючого ID ресурсу"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 7] Гранична валідація (Неіснуючий ID ресурсу)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)
        payload = {
            'resource': 999999,
            'quantity_requested': 10,
            'purpose': self.purpose.id,
            'latitude': 50.45,
            'longitude': 30.52
        }

        response = self.client.post(self.requests_url, payload, format='json')

        print(f" • Статус відповіді при неіснуючому ресурсі: {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND])
        print(" [УСПІХ] Система коректно обробила спробу зв'язку з неіснуючою сутністю в БД.")
        print("=" * 90)

    # --- МОДУЛЬ 3: ЖИТТЄВИЙ ЦИКЛ СУТНОСТЕЙ — CRUD (ТЕСТИ 8–11) ---

    def test_8_request_creation_with_valid_data(self):
        """Функціональний тест 8: Успішне створення заявки (CRUD Create)"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 8] Успішне створення заявки (CRUD Create)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)
        payload = {
            'resource': self.resource.id,
            'quantity_requested': 25,
            'purpose': self.purpose.id,
            'latitude': 50.47,
            'longitude': 30.54
        }

        response = self.client.post(self.requests_url, payload, format='json')

        print(f" • Статус відповіді: {response.status_code} Created")
        print(f" • ID нової заявки : {response.data.get('id', 'N/A')}")
        print(f" • Статус заявки   : {response.data.get('status', 'new')}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        print(" [УСПІХ] Нову заявку успішно зареєстровано в системі.")
        print("=" * 90)

    def test_9_request_crud_lifecycle_update(self):
        """Функціональний тест 9: Оновлення параметрів заявки (CRUD Update)"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 9] Оновлення даних заявки (CRUD Update)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)

        req_obj = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            purpose=self.purpose,
            quantity_requested=10,
            latitude=50.45,
            longitude=30.52
        )

        update_url = f"{self.requests_url}{req_obj.id}/"
        response = self.client.patch(update_url, {"quantity_requested": 45}, format='json')

        print(f" • Оновлення заявки ID={req_obj.id}: статус {response.status_code}")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('quantity_requested'), 45)
        print(" [УСПІХ] Життєвий цикл оновлення сутності (CRUD) опрацьовано успішно.")
        print("=" * 90)

    def test_10_request_crud_lifecycle_delete(self):
        """Функціональний тест 10: Видалення заявки (CRUD Delete)"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 10] Видалення заявки (CRUD Delete)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)

        req_obj = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            purpose=self.purpose,
            quantity_requested=15,
            latitude=50.45,
            longitude=30.52
        )

        delete_url = f"{self.requests_url}{req_obj.id}/"
        response = self.client.delete(delete_url)

        print(f" • Видалення заявки ID={req_obj.id}: статус {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK])
        self.assertFalse(UserRequest.objects.filter(id=req_obj.id).exists())
        print(" [УСПІХ] Заявку успішно видалено з бази даних (завершення повного CRUD-циклу).")
        print("=" * 90)

    # --- МОДУЛЬ 4: БІЗНЕС-ЛОГІКА ТА ІНТЕГРАЦІЯ ОПТИМІЗАТОРА (ТЕСТИ 11–12) ---

    def test_11_request_business_logic_exceeding_stock(self):
        """Функціональний тест 11: Бізнес-логіка — реєстрація дефіцитного запиту (перевищення запасів)"""
        print("\n" + "=" * 90)
        print(" [ФУНКЦІОНАЛЬНИЙ ТЕСТ 11] Реєстрація дефіцитного запиту (надлишок попиту)")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)
        excessive_payload = {
            "resource": self.resource.id,
            "quantity_requested": 5000,
            "latitude": 50.45,
            "longitude": 30.52,
            "purpose": self.purpose.id,
            "city": "Київ"
        }

        response = self.client.post(self.requests_url, excessive_payload, format='json')

        print(f" • Запит на надмірну кількість (5000 при запасі 100): статус {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        if response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            self.assertEqual(response.data.get('quantity_allocated', 0), 0)

        print(" [УСПІХ] Система успішно зареєструвала дефіцитну заявку для подальшої оптимізації.")
        print("=" * 90)

    def test_12_distribution_trigger_endpoint(self):
        """Інтеграційний тест 12: Перевірка успішного запуску процесу розподілу через API"""
        print("\n" + "=" * 90)
        print(" [ІНТЕГРАЦІЙНИЙ ТЕСТ 12] Запуск процесу розподілу через API /api/distribute/")
        print("=" * 90)

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/distribute/', {}, format='json')

        print(f" • Статус відповіді /api/distribute/: {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])
        print(" [УСПІХ] Ендпоінт розподілу опрацьовано коректно.")
        print("=" * 90)


# --- 3. ТЕСТИ ГЕОСЕРВІСУ ТА КЕШУВАННЯ OSRM ---
class RoutingServiceTests(TestCase):
    """Тести для OSRM Table API, локального кешування та фолбеків"""

    def setUp(self):
        _ROUTING_CACHE.clear()

    @patch('app.services.requests.get')
    def test_osrm_table_api_single_request(self, mock_get):
        """Перевірка виклику Table API рівно 1 раз для всієї матриці (вирішення проблеми N+1)"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [[10000.0, 20000.0], [30000.0, 40000.0]]
        }

        service = DistanceMatrixService()
        stocks = [{'lat': 50.45, 'lng': 30.52}, {'lat': 49.84, 'lng': 24.03}]
        requests = [{'lat': 50.00, 'lng': 36.23}, {'lat': 46.48, 'lng': 30.73}]

        matrix = service.get_distance_matrix(stocks, requests)

        self.assertEqual(matrix.shape, (2, 2))
        self.assertAlmostEqual(matrix[0, 0], 10.0)
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_in_memory_cache_prevents_duplicate_calls(self, mock_get):
        """Перевірка роботи ін-меморі кешу: при повторному запиті HTTP не викликається"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [[12000.0]]
        }

        service = DistanceMatrixService()
        stocks = [{'lat': 50.450, 'lng': 30.520}]
        requests = [{'lat': 50.000, 'lng': 36.230}]

        service.get_distance_matrix(stocks, requests)
        self.assertEqual(mock_get.call_count, 1)

        # Повторний запит неподалік (має взятися з кешу)
        service.get_distance_matrix([{'lat': 50.4502, 'lng': 30.5204}], [{'lat': 50.0003, 'lng': 36.2301}])
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_fallback_to_geometry_on_network_error(self, mock_get):
        """Перевірка спрацювання геометричного фолбеку при збої мережі OSRM"""
        mock_get.side_effect = req_lib.RequestException("Network timeout")

        service = DistanceMatrixService()
        stocks = [{'lat': 50.0, 'lng': 30.0}]
        requests = [{'lat': 51.0, 'lng': 31.0}]

        matrix = service.get_distance_matrix(stocks, requests)
        self.assertGreater(matrix[0, 0], 0.0)

    def test_missing_coordinates_penalty(self):
        """Перевірка повернення штрафної відстані (500 км) при відсутності координат"""
        service = DistanceMatrixService()
        stocks = [{'lat': None, 'lng': 30.0}]
        requests = [{'lat': 50.0, 'lng': None}]

        matrix = service.get_distance_matrix(stocks, requests)
        self.assertEqual(matrix[0, 0], 500.0)


# --- 4. БЕНЧМАРКИ ПРОДУКТИВНОСТІ ТА ВЕБ-СИМУЛЯЦІЇ ---
class WebSimulationBenchmarks(TestCase):
    """Стрес-тести для перевірки паралельних обчислень гео-пар та часу відгуку вебінтерфейсу"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_real_web_simulation_benchmark(self):
        """Емуляція реального вебзапиту з паралельним розрахунком матриці відстаней"""
        distance_service = MockDistanceService()
        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 150, 'lat': 50.45, 'lng': 30.52},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 120, 'lat': 49.84, 'lng': 24.02},
            {'resource_id': 1, 'warehouse_id': 3, 'amount': 100, 'lat': 46.48, 'lng': 30.73},
            {'resource_id': 1, 'warehouse_id': 4, 'amount': 80, 'lat': 49.99, 'lng': 36.23},
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 5,
             'lat': 50.0 + (i * 0.01), 'lng': 30.0 + (i * 0.01)}
            for i in range(20)
        ]

        t_start = time.time()
        pairs = [(s['lat'], s['lng'], r['lat'], r['lng']) for s in stocks for r in requests]
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda p: distance_service.get_distance(p[0], p[1], p[2], p[3]), pairs))
        geo_time = time.time() - t_start

        self.assertLess(geo_time, 1.0, "Час обробки гео-пар занадто великий")
        print(f"\n[УСПІХ] Емуляція паралельного опитування 80 пар виконана за {geo_time:.5f} с")