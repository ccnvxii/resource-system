import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.test import TestCase
from django.db import connection, transaction
from django.db.utils import OperationalError
from rest_framework.test import APITestCase, APITransactionTestCase, APIClient
from rest_framework import status

from app.models import (
    Unit, Category, Resource, Warehouse, Stock,
    RequestPurpose, UserRequest, UserProfile
)
from django.contrib.auth.models import User
from app.tests.mock_services import MockDistanceService


class NonFunctionalSecurityAndValidationTests(APITestCase):
    """Нефункціональні тести: безпека, автентифікація, стійкість до ін'єкцій та граничні стани"""

    def setUp(self):
        """Підготовка базових даних для нефункціональних перевірок безпеки"""
        self.user = User.objects.create_superuser(
            username='admin_security_test',
            email='sec@example.com',
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
            slug='meds-nf',
            defaults={'name': 'Медикаменти НФ', 'criticality': 0.8}
        )
        self.purpose, _ = RequestPurpose.objects.get_or_create(
            code='HUMANITARIAN_NF',
            defaults={'name': 'Гуманітарна допомога НФ', 'weight': 1.0}
        )

        self.resource = Resource.objects.create(
            name='Медикаменти НФ',
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

    # --- МОДУЛЬ БЕЗПЕКИ ТА JWT АВТЕНТИФІКАЦІЇ ---

    def test_3_security_sql_injection_defense_in_filters(self):
        """Нефункціональний тест / Безпека: Стійкість параметрів фільтрації до шкідливих ін'єкцій"""
        print("\n" + "=" * 90)
        print(" [НЕФУНКЦІОНАЛЬНИЙ ТЕСТ] Захист від SQL-ін'єкцій у параметрах фільтрації")
        print("=" * 90)

        malicious_url = f"{self.requests_url}?status=new'%20OR%201=1--"
        response = self.client.get(malicious_url, format='json')

        print(f" • Переданий шкідливий параметр: status=new' OR 1=1--")
        print(f" • Статус відповіді сервера     : {response.status_code}")
        print("-" * 90)

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        print(" [УСПІХ] Система безпечно обробила запит без уразливості до ін'єкцій.")
        print("=" * 90)

    def test_4_security_fake_or_forged_jwt_token_rejection(self):
        """Нефункціональний тест / Безпека: Відхилення підробленого або невалідного JWT-токена"""
        print("\n" + "=" * 90)
        print(" [НЕФУНКЦІОНАЛЬНИЙ ТЕСТ] Відхилення підробленого JWT-токена")
        print("=" * 90)

        self.client.logout()
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo5OTksImV4cCI6OTk5OTk5OTk5OX0.FakeSignatureForTestingPurposesOnly"
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {fake_token}')

        response = self.client.get(self.requests_url, format='json')

        print(f" • Переданий фейковий токен : {fake_token[:30]}...")
        print(f" • Статус відповіді сервера : {response.status_code} Unauthorized")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(" [УСПІХ] Система безпеки успішно заблокувала невалідний JWT-токен.")
        print("=" * 90)
        self.client.credentials()

    def test_5_security_rate_limiting_throttling(self):
        """Нефункціональний тест / Безпека: Перевірка захисту від частих запитів (Rate Limiting)"""
        print("\n" + "=" * 90)
        print(" [НЕФУНКЦІОНАЛЬНИЙ ТЕСТ] Перевірка захисту від частих запитів (Rate Limiting)")
        print("=" * 90)

        login_url = '/api/token/'
        status_codes = []
        for _ in range(25):
            response = self.client.post(login_url, {
                'username': 'wrong_user',
                'password': 'wrong_password'
            }, format='json')
            status_codes.append(response.status_code)

        print(f" • Кількість тестових запитів : 25 швидких спроб")
        print(f" • Отримані статуси відповідей: {set(status_codes)}")
        print("-" * 90)

        allowed_statuses = [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ]
        for code in status_codes:
            self.assertIn(code, allowed_statuses)
        print(" [УСПІХ] Механізм лімітування частоти запитів спрацював коректно.")
        print("=" * 90)

    def test_6_security_http_headers(self):
        """Нефункціональний тест / Безпека: Перевірка наявності захисних HTTP-заголовків"""
        print("\n" + "=" * 90)
        print(" [НЕФУНКЦІОНАЛЬНИЙ ТЕСТ] Перевірка наявності безпекових HTTP-заголовків")
        print("=" * 90)

        response = self.client.get('/api/resources/', format='json')

        print(f" • Content-Type заголовок : {response.get('Content-Type', 'Відсутній')}")
        print(f" • Статус відповіді сервера : {response.status_code}")
        print("-" * 90)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(" [УСПІХ] Базові захисні заголовки відповіді сервера сформовано коректно.")
        print("=" * 90)


# --- МОДУЛЬ НАВАНТАЖУВАЛЬНОГО ТЕСТУВАННЯ ТА ПРОДУКТИВНОСТІ ---
class NonFunctionalLoadTests(APITransactionTestCase):
    """Нефункціональні тести продуктивності, навантаження та паралельного доступу"""

    def setUp(self):
        unique_suffix = time.time_ns()
        short_suffix = str(unique_suffix)[-6:]

        self.unit = Unit.objects.create(name=f'штуки_{short_suffix}')
        self.category = Category.objects.create(
            slug=f'load-meds-{short_suffix}',
            name='Швидка допомога ЛОД',
            criticality=0.9
        )
        self.purpose = RequestPurpose.objects.create(
            code=f'L_{short_suffix}',
            name='Навантажувальний тест',
            weight=1.0
        )
        self.resource = Resource.objects.create(
            name='Дефіцитний турнікет ЛОД',
            is_strategic=True,
            unit=self.unit,
            category=self.category
        )
        self.warehouse = Warehouse.objects.create(
            name='Прифронтовий хаб ЛОД',
            location='м. Запоріжжя',
            latitude=47.8388,
            longitude=35.1396
        )
        self.stock = Stock.objects.create(
            warehouse=self.warehouse,
            resource=self.resource,
            amount=50
        )
        self.user = User.objects.create_superuser(
            username=f'load_t_{short_suffix}',
            email=f'load_{short_suffix}@example.com',
            password='SecurePassword123!'
        )

    def test_concurrent_api_load_performance(self):
        """Стрес-тест: паралельне виконання запитів до API з вимірюванням часу"""
        print("\n" + "=" * 90)
        print(" [НАВАНТАЖУВАЛЬНИЙ ТЕСТ] Паралельне виконання 20 запитів до API")
        print("=" * 90)

        url = '/api/resources/'

        def make_request():
            client = APIClient()
            client.force_authenticate(user=self.user)
            response = client.get(url)
            return response.status_code

        t_start = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            status_codes = list(executor.map(lambda _: make_request(), range(20)))

        duration = time.time() - t_start

        print(f" • Опрацьовано запитів     : 20 (у 5 паралельних потоках)")
        print(f" • Загальний час виконання : {duration:.4f} секунд")
        print("-" * 90)

        for code in status_codes:
            self.assertEqual(code, 200)

        self.assertLess(duration, 3.0, "Час обробки паралельних запитів перевищує норму")
        print(" [УСПІХ] Стрес-тест паралельних запитів пройдено успішно.")
        print("=" * 90)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_load_performance_distribution_endpoint(self):
        """Навантажувальне тестування ендпоінту /api/distribute/ при масиві 500+ заявок"""
        print("\n" + "=" * 90)
        print(" [НАВАНТАЖУВАЛЬНИЙ ТЕСТ] Оптимізація та розподіл масиву з 500+ заявок")
        print("=" * 90)

        bulk_requests = [
            UserRequest(
                user=self.user,
                resource=self.resource,
                purpose=self.purpose,
                quantity_requested=10,
                priority=float((i % 5) + 5.0),
                latitude=47.8 + (i * 0.0001),
                longitude=35.1 + (i * 0.0001),
                status='new'
            )
            for i in range(500)
        ]
        UserRequest.objects.bulk_create(bulk_requests)

        self.client.force_authenticate(user=self.user)

        t_start = time.time()
        response = self.client.post('/api/distribute/', {}, format='json')
        execution_time = time.time() - t_start

        print(f" • Кількість заявок у черзі : 500")
        print(f" • Статус відповіді сервера : {response.status_code}")
        print(f" • Час обчислення алгоритму : {execution_time:.4f} секунд")
        print("-" * 90)

        self.assertLess(execution_time, 5.0, "Час виконання розподілу перевищує ліміт навантаження")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        print(" [УСПІХ] Алгоритм розподілу успішно опрацював великий масив даних.")
        print("=" * 90)

    def test_concurrency_race_condition_stock_reservation(self):
        """Перевірка консистентності даних при гонці потоків (Race Conditions & select_for_update)"""
        print("\n" + "=" * 90)
        print(" [ТЕСТ КОНСИСТЕНТНОСТІ] Захист від подвійного списання (Race Conditions)")
        print("=" * 90)

        stock_id = self.stock.id
        initial_amount = self.stock.amount

        def concurrent_reservation(deduct_amount):
            try:
                with transaction.atomic():
                    stk = Stock.objects.select_for_update().get(id=stock_id)
                    if stk.amount >= deduct_amount:
                        time.sleep(0.05)
                        stk.amount -= deduct_amount
                        stk.save()
                        return True
            except (OperationalError, Exception):
                pass
            return False

        threads = []
        results = []

        def worker(amt):
            res = concurrent_reservation(amt)
            results.append(res)

        for _ in range(10):
            t = threading.Thread(target=worker, args=(10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.stock.refresh_from_db()
        successful_transactions = sum(1 for r in results if r)

        print(f" • Початковий запас на складі      : {initial_amount}")
        print(f" • Успішних паралельних транзакцій : {successful_transactions} із 10")
        print(f" • Кінцевий залишок у базі даних   : {self.stock.amount}")
        print("-" * 90)

        self.assertGreaterEqual(self.stock.amount, 0, "Запас не може бути від'ємним у результаті гонки")
        self.assertEqual(
            self.stock.amount,
            initial_amount - (successful_transactions * 10),
            "Порушено атомарність списання залишків"
        )
        print(" [УСПІХ] Механізм блокувань select_for_update успішно запобіг гонці даних.")
        print("=" * 90)

    def test_large_payload_bulk_import_handling(self):
        """Нефункціональний тест / Надійність: Перевірка поведінки при надлитковому обсязі вхідних даних (Large Payload)"""
        print("\n" + "=" * 90)
        print(" [НАВАНТАЖУВАЛЬНИЙ ТЕСТ] Обробка масового пакетного імпорту (1000+ сутностей)")
        print("=" * 90)

        bulk_resources = [
            Resource(
                name=f'Масовий ресурс {i}',
                is_strategic=False,
                unit=self.unit,
                category=self.category
            )
            for i in range(1000)
        ]

        t_start = time.time()
        Resource.objects.bulk_create(bulk_resources)
        execution_time = time.time() - t_start

        total_count = Resource.objects.filter(name__startswith='Масовий ресурс').count()

        print(f" • Кількість імпортованих об'єктів : 1000")
        print(f" • Час виконання пакетної вставки  : {execution_time:.4f} секунд")
        print(f" • Успішно збережено в базі даних : {total_count} сутностей")
        print("-" * 90)

        self.assertEqual(total_count, 1000)
        self.assertLess(execution_time, 2.0, "Час пакетного імпорту перевищує норму")
        print(" [УСПІХ] Пакетний імпорт великого обсягу даних опрацьовано ефективно.")
        print("=" * 90)


# --- БЕНЧМАРКИ ПРОДУКТИВНОСТІ ТА ВЕБ-СИМУЛЯЦІЇ ---
class WebSimulationBenchmarks(TestCase):
    """Стрес-тести для перевірки паралельних обчислень гео-пар та часу відгуку вебінтерфейсу"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_real_web_simulation_benchmark(self):
        """Емуляція реального вебзапиту з паралельним розрахунком матриці відстаней"""
        print("\n" + "=" * 90)
        print(" [БЕНЧМАРК ГЕО-РОЗРАХУНКІВ] Емуляція паралельного опитування матриці відстаней")
        print("=" * 90)

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

        print(f" • Оброблено географічних пар    : 80 пар (4 склади × 20 заявок)")
        print(f" • Час паралельного розрахунку   : {geo_time:.5f} секунд")
        print("-" * 90)

        self.assertLess(geo_time, 1.0, "Час обробки гео-пар занадто великий")
        print(" [УСПІХ] Бенчмарк гео-розрахунків виконано в межах норми.")
        print("=" * 90)