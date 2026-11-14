"""
НЕФУНКЦІОНАЛЬНЕ ТЕСТУВАННЯ.

Категорії: безпека, стійкість до відмов зовнішніх сервісів, продуктивність і масштабування, паралельний доступ.
Оформлення для звіту: перший рядок докстрінга класу - категорія, test_NN - номер, докстрінг - назва.
Використовуються лише власні реалізації алгоритмів (без SciPy).
"""
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase, APITransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from app.models import (
    Category, Resource, RequestPurpose, Stock, Unit, UserProfile, UserRequest, Warehouse,
)
from app.optimizer.distribute import calculate_distribution, calculate_strict_priority
from app.services import DistanceMatrixService, GeoFrontService, _ROUTING_CACHE
from app.tests.helpers import FakeFront, FlatRouting, make_instance
from app.tests.mock_services import MockDistanceService
from app.utils import calculate_front_multiplier


# ======================================================================================
# 1. БЕЗПЕКА
# ======================================================================================
@patch('app.utils.GeoFrontService', FakeFront)
class SecurityTests(APITestCase):
    """Безпека"""

    PASSWORD = 'Str0ng-Pass-77'

    def setUp(self):
        cache.clear()  # лічильники обмеження частоти не переходять між тестами
        self.volunteer = User.objects.create_user('sec_vol', email='sec_vol@example.com', password=self.PASSWORD)
        UserProfile.objects.create(user=self.volunteer, is_approved=True)
        self.other = User.objects.create_user('sec_oth', email='sec_oth@example.com', password=self.PASSWORD)
        UserProfile.objects.create(user=self.other, is_approved=True)
        self.admin = User.objects.create_user('sec_adm', email='sec_adm@example.com', password=self.PASSWORD, is_staff=True)
        unit, _ = Unit.objects.get_or_create(name='sec-шт')
        cat, _ = Category.objects.get_or_create(slug='sec-cat', defaults={'name': 'Sec', 'criticality': 0.5})
        self.resource = Resource.objects.create(name='Sec ресурс', unit=unit, category=cat)
        self.purpose, _ = RequestPurpose.objects.get_or_create(code='sec_p', defaults={'name': 'Sec', 'weight': 0.5})

    def _header(self, user):
        resp = self.client.post('/api/token/', {'username': user.username, 'password': self.PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        return {'HTTP_AUTHORIZATION': f"Bearer {resp.data['access']}"}

    def _request_payload(self, **extra):
        data = {'resource': self.resource.id, 'quantity_requested': 5, 'purpose': self.purpose.id, 'city': 'Київ',
                'warehouse_address': 'Відділення 1', 'warehouse_ref': 'ADDRESS_DELIVERY',
                'due_date': str(timezone.now().date() + timedelta(days=5))}
        data.update(extra)
        return data

    def test_01_rate_limiting(self):
        """Обмеження частоти запитів: вхід, реєстрація та відновлення пароля (захист від перебору)"""
        codes = [self.client.post('/api/token/', {'username': 'x', 'password': 'y'}, format='json').status_code for _ in range(25)]
        self.assertEqual(codes[0], status.HTTP_401_UNAUTHORIZED)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, codes)
        self.assertGreaterEqual(codes.index(status.HTTP_429_TOO_MANY_REQUESTS), 15)   # легітимні спроби не блокуються передчасно
        for url, payload in (('/api/password-reset/', {'email': 'a@example.com'}), ('/api/register/', {'username': 'a'})):
            cache.clear()
            codes = [self.client.post(url, payload, format='json').status_code for _ in range(25)]
            self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, codes, url)
        cache.clear()
        for _ in range(5):
            self.client.post('/api/token/', {'username': 'x', 'password': 'y'}, format='json')
        ok = self.client.post('/api/token/', {'username': 'sec_vol', 'password': self.PASSWORD}, format='json')
        self.assertEqual(ok.status_code, 200)                                          # нижче ліміту вхід працює

    def test_02_http_headers(self):
        """Захисні HTTP-заголовки, JSON як тип вмісту, відсутність витоку стеку помилок"""
        resp = self.client.get('/api/resources/')
        self.assertEqual(resp['X-Content-Type-Options'], 'nosniff')
        self.assertIn(resp['X-Frame-Options'], ('DENY', 'SAMEORIGIN'))
        self.assertIn('Referrer-Policy', resp)
        self.assertTrue(resp['Content-Type'].startswith('application/json'))
        err = self.client.get('/api/requests/not-a-number/')
        self.assertNotIn('Traceback', err.content.decode('utf-8', 'ignore'))

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_03_access_control(self):
        """Контроль доступу: волонтер і анонім не мають адміністративних можливостей"""
        header = self._header(self.volunteer)                                          # реальний JWT, а не force_authenticate
        self.assertEqual(self.client.post('/api/distribute/', {}, format='json', **header).status_code, 403)
        self.assertEqual(self.client.get('/api/users/', **header).status_code, 403)
        self.assertEqual(self.client.get('/api/logs/', **header).status_code, 403)
        wh = {'name': 'X', 'location': 'Y', 'latitude': 1, 'longitude': 1}
        self.assertEqual(self.client.post('/api/warehouses/', wh, format='json', **header).status_code, 403)
        for url in ('/api/requests/', '/api/distribute/', '/api/stocks/add_resource/'):
            self.assertEqual(self.client.post(url, {}, format='json').status_code, 401)  # без входу

    def test_04_input_attacks(self):
        """Атаки на вхідні дані: XSS-навантаження, SQL-ін'єкції, надвеликі та некоректні дані"""
        header = self._header(self.volunteer)
        xss = '<script>alert("xss")</script>'
        created = self.client.post('/api/requests/', self._request_payload(city=xss, warehouse_address=xss), format='json', **header)
        self.assertEqual(created.status_code, 201, created.data)
        resp = self.client.get('/api/requests/', **header)
        self.assertTrue(resp['Content-Type'].startswith('application/json'))           # не HTML: браузер не виконає
        self.assertEqual(resp['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(resp.data[0]['city'], xss)

        admin_header = self._header(self.admin)
        for url in ("/api/requests/?status=new'%20OR%201=1--", '/api/requests/1%20OR%201=1/',
                    '/api/resources/?name=%27%3B%20DROP%20TABLE%20app_resource%3B--'):
            self.assertIn(self.client.get(url, **admin_header).status_code, (200, 400, 404))
        self.assertTrue(Resource.objects.exists())                                       # таблиця на місці
        big = self.client.post('/api/requests/', self._request_payload(city='А' * 100_000), format='json', **header)
        self.assertEqual(big.status_code, 400)
        broken = self.client.post('/api/requests/', data='{"resource": ', content_type='application/json', **header)
        self.assertEqual(broken.status_code, 400)

    def test_05_mass_assignment(self):
        """Масове присвоєння полів: службові поля заявки та права при реєстрації ігноруються"""
        header = self._header(self.volunteer)
        resp = self.client.post('/api/requests/', self._request_payload(
            priority=999, status='done', quantity_allocated=500, user=self.other.id), format='json', **header)
        self.assertEqual(resp.status_code, 201, resp.data)
        req = UserRequest.objects.get(id=resp.data['id'])
        self.assertEqual((req.user_id, req.status, req.quantity_allocated), (self.volunteer.id, 'new', 0))
        self.assertLessEqual(req.priority, 1.0)                                          # обчислено, а не взято з тіла
        self.client.patch(f'/api/requests/{req.id}/', {'status': 'done', 'quantity_allocated': 5}, format='json', **header)
        req.refresh_from_db()
        self.assertEqual((req.status, req.quantity_allocated), ('new', 0))

        reg = self.client.post('/api/register/', {
            'username': 'evil@example.com', 'email': 'evil@example.com', 'password': self.PASSWORD,
            'first_name': 'E', 'last_name': 'U', 'phone': '+380671234567', 'organization': 'X',
            'is_staff': True, 'is_superuser': True, 'is_approved': True}, format='json')
        self.assertEqual(reg.status_code, 201)
        evil = User.objects.get(email='evil@example.com')
        self.assertEqual((evil.is_staff, evil.is_superuser, evil.profile.is_approved), (False, False, False))

    def test_06_jwt_lifetime_and_validity(self):
        """JWT: обмежений строк дії, відхилення простроченого, підробленого та токена видаленого/неактивного користувача"""
        self.assertLessEqual(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'], timedelta(days=1))
        self.assertLessEqual(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'], timedelta(days=7))

        def get(token):
            return self.client.get('/api/requests/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code

        self.assertEqual(get(str(AccessToken.for_user(self.volunteer))), 200)
        expired = AccessToken.for_user(self.volunteer)
        expired.set_exp(from_time=timezone.now() - timedelta(days=3), lifetime=timedelta(days=1))
        self.assertEqual(get(str(expired)), 401)
        old_refresh = RefreshToken.for_user(self.volunteer)
        old_refresh.set_exp(from_time=timezone.now() - timedelta(days=30), lifetime=timedelta(days=7))
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': str(old_refresh)}, format='json').status_code, 401)
        fresh = self.client.post('/api/token/refresh/', {'refresh': str(RefreshToken.for_user(self.volunteer))}, format='json')
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(get(str(RefreshToken.for_user(self.volunteer))), 401)           # refresh не замінює access

        import jwt
        forged = jwt.encode({'user_id': self.admin.id, 'token_type': 'access', 'jti': 'x',
                             'exp': int((timezone.now() + timedelta(days=1)).timestamp())},
                            'not-the-server-secret-key-0123456789abcdef', algorithm='HS256')
        self.assertEqual(get(forged), 401)
        deleted_token = str(AccessToken.for_user(self.other))
        self.other.delete()
        self.assertEqual(get(deleted_token), 401)
        inactive_token = str(AccessToken.for_user(self.volunteer))
        self.volunteer.is_active = False
        self.volunteer.save()
        self.assertEqual(get(inactive_token), 401)

    def test_07_password_policy(self):
        """Політика паролів: слабкі відхиляються, надійний приймається, пароль зберігається лише у вигляді хеша"""
        def register(password, email):
            return self.client.post('/api/register/', {
                'username': email, 'email': email, 'password': password, 'first_name': 'Ім', 'last_name': 'Пр',
                'phone': '+380671234567', 'organization': 'Org'}, format='json')

        for i, weak in enumerate(('short1', '12345678', 'password', 'qwerty123', '1111111111')):
            resp = register(weak, f'weak{i}@example.com')
            self.assertEqual(resp.status_code, 400, f'{weak!r} має бути відхилено')
            self.assertIn('password', resp.data)
        good = register('Gl0b@l-Ukr-2026', 'good@example.com')
        self.assertEqual(good.status_code, 201)
        self.assertNotIn('password', good.data)
        stored = User.objects.get(email='good@example.com').password
        self.assertNotIn('Gl0b@l-Ukr-2026', stored)
        self.assertTrue(stored.startswith(('pbkdf2_', 'argon2', 'bcrypt')))


# ======================================================================================
# 2. СТІЙКІСТЬ ДО ВІДМОВ ЗОВНІШНІХ СЕРВІСІВ
# ======================================================================================
class ResilienceTests(APITestCase):
    """Стійкість до відмов зовнішніх сервісів"""

    SOURCES = [{'lat': 50.45, 'lng': 30.52}, {'lat': 49.84, 'lng': 24.03}]
    DESTS = [{'lat': 48.46, 'lng': 35.04}, {'lat': 46.48, 'lng': 30.73}, {'lat': 50.0, 'lng': 36.2}]

    def setUp(self):
        cache.clear()
        _ROUTING_CACHE.clear()

    def _assert_finite(self, matrix):
        self.assertEqual(matrix.shape, (2, 3))
        self.assertTrue((matrix > 0).all() and matrix.max() < 5000)

    def test_01_osrm_unavailable(self):
        """OSRM недоступний (мережа, таймаут, помилка сервера, не JSON): резервний геометричний розрахунок відстаней"""
        for effect in (requests.exceptions.ConnectionError('лежить'), requests.exceptions.Timeout('таймаут')):
            _ROUTING_CACHE.clear()
            with patch('app.services.requests.get', side_effect=effect):
                self._assert_finite(DistanceMatrixService().get_distance_matrix(self.SOURCES, self.DESTS))
        _ROUTING_CACHE.clear()
        with patch('app.services.requests.get') as get:
            bad = MagicMock(status_code=500)
            bad.json.side_effect = ValueError('не JSON')
            get.return_value = bad
            self._assert_finite(DistanceMatrixService().get_distance_matrix(self.SOURCES, self.DESTS))
        _ROUTING_CACHE.clear()
        with patch('app.services.requests.get', side_effect=requests.exceptions.ConnectionError('лежить')):
            self.assertTrue(0 < DistanceMatrixService().get_distance(50.45, 30.52, 49.84, 24.03) < 2000)

    def test_02_osrm_normal_operation(self):
        """OSRM працює: один запит на всю матрицю, кеш не дублює виклики, штраф за відсутні координати"""
        with patch('app.services.requests.get') as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {'code': 'Ok', 'distances': [[10000.0, 20000.0], [30000.0, 40000.0]]}
            matrix = DistanceMatrixService().get_distance_matrix(
                [{'lat': 50.45, 'lng': 30.52}, {'lat': 49.84, 'lng': 24.03}], [{'lat': 50.0, 'lng': 36.23}, {'lat': 46.48, 'lng': 30.73}])
            self.assertEqual((matrix.shape, get.call_count), ((2, 2), 1))
            self.assertAlmostEqual(matrix[0, 0], 10.0)
        _ROUTING_CACHE.clear()
        with patch('app.services.requests.get') as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {'code': 'Ok', 'distances': [[12000.0]]}
            service = DistanceMatrixService()
            service.get_distance_matrix([{'lat': 50.450, 'lng': 30.520}], [{'lat': 50.000, 'lng': 36.230}])
            service.get_distance_matrix([{'lat': 50.4502, 'lng': 30.5204}], [{'lat': 50.0003, 'lng': 36.2301}])
            self.assertEqual(get.call_count, 1)                                          # друга пара взята з кешу
        penalty = DistanceMatrixService().get_distance_matrix([{'lat': None, 'lng': 30.0}], [{'lat': 50.0, 'lng': None}])
        self.assertEqual(penalty[0, 0], 500.0)

    def test_03_arcgis_unavailable(self):
        """ArcGIS (лінія фронту) недоступний: резервні точки, геомножник залишається коректним"""
        with patch('app.services.requests.get', side_effect=requests.exceptions.ConnectionError('ArcGIS лежить')):
            points = GeoFrontService().get_front_line_points()
            self.assertTrue(points and all(len(p) == 2 for p in points))
            self.assertTrue(0.15 <= calculate_front_multiplier(50.0, 36.0) <= 1.0)
        with patch('app.services.requests.get') as get:
            get.return_value = MagicMock(status_code=503)
            self.assertTrue(GeoFrontService().get_front_line_points())
            empty = MagicMock(status_code=200)
            empty.json.return_value = {'features': []}
            get.return_value = empty
            self.assertTrue(GeoFrontService().get_front_line_points())

    @patch('app.services.time.sleep', lambda *_: None)
    def test_04_nova_poshta_unavailable(self):
        """Нова Пошта недоступна: порожні списки замість помилок сервера (мережа, success=false, не JSON)"""
        user = User.objects.create_user('np_res', email='np_res@example.com', password='x')
        UserProfile.objects.create(user=user, is_approved=True)
        self.client.force_authenticate(user)
        calls = (('get_cities', {'search': 'Київ'}), ('get_warehouses', {'city_ref': 'abc'}), ('get_streets', {'city_ref': 'abc', 'search': 'Со'}))
        with patch('app.services.requests.post', side_effect=requests.exceptions.ConnectionError('НП лежить')):
            for action, extra in calls:
                resp = self.client.post('/api/novaposhta/', {'action': action, **extra}, format='json')
                self.assertEqual((resp.status_code, resp.data), (200, []))
        with patch('app.services.requests.post') as post:
            answer = MagicMock()
            answer.json.return_value = {'success': False, 'data': [], 'errors': ['bad key']}
            post.return_value = answer
            self.assertEqual(self.client.post('/api/novaposhta/', {'action': 'get_cities', 'search': 'К'}, format='json').data, [])
            answer.json.side_effect = ValueError('не JSON')
            self.assertEqual(self.client.post('/api/novaposhta/', {'action': 'get_warehouses', 'city_ref': 'a'}, format='json').status_code, 200)

    def test_05_distribution_during_outages(self):
        """Розподіл виконується повністю, коли недоступні і OSRM, і ArcGIS"""
        UserRequest.objects.all().delete()
        Stock.objects.all().delete()
        admin = User.objects.create_user('res_admin', email='res_admin@example.com', password='x', is_staff=True)
        owner = User.objects.create_user('res_owner', email='res_owner@example.com', password='x')
        UserProfile.objects.create(user=owner, is_approved=True)
        unit, _ = Unit.objects.get_or_create(name='res-шт')
        cat, _ = Category.objects.get_or_create(slug='res-cat', defaults={'name': 'Res', 'criticality': 0.6})
        purpose, _ = RequestPurpose.objects.get_or_create(code='res_p', defaults={'name': 'Res', 'weight': 0.8})
        regular = Resource.objects.create(name='Res звичайний', unit=unit, category=cat)
        strategic = Resource.objects.create(name='Res стратегічний', unit=unit, category=cat, is_strategic=True)
        warehouses = [Warehouse.objects.create(name='Res 1', location='Київ', latitude=50.45, longitude=30.52),
                      Warehouse.objects.create(name='Res 2', location='Львів', latitude=49.84, longitude=24.03)]
        for w in warehouses:
            Stock.objects.create(warehouse=w, resource=regular, amount=20)
            Stock.objects.create(warehouse=w, resource=strategic, amount=10)
        down = requests.exceptions.ConnectionError('все лежить')
        with patch('app.services.requests.get', side_effect=down):
            for res in (regular, strategic):
                for i in range(3):
                    UserRequest.objects.create(
                        user=owner, resource=res, quantity_requested=15, purpose=purpose, city='Харків',
                        latitude=49.99 + i * 0.1, longitude=36.23, due_date=timezone.now().date() + timedelta(days=3 + i))
            self.client.force_authenticate(admin)
            resp = self.client.post('/api/distribute/', {'strategy': 'hybrid'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertGreater(len(resp.data['items']), 0)
        self.assertTrue(all(s.amount >= 0 for s in Stock.objects.all()))


# ======================================================================================
# 3. ПРОДУКТИВНІСТЬ І МАСШТАБУВАННЯ
# ======================================================================================
def loglog_slope(sizes, times):
    t0, t1 = max(times[0], 1e-4), max(times[-1], 1e-4)
    return math.log(t1 / t0) / math.log(sizes[-1] / sizes[0])


def print_curve(title, sizes, times, limits):
    print(f"\n{'=' * 78}\n [КРИВА МАСШТАБУВАННЯ] {title}\n{'=' * 78}")
    print(f" {'Заявок':>8} | {'Час, с':>10} | {'Ліміт, с':>9}")
    for n, t in zip(sizes, times):
        print(f" {n:>8} | {t:>10.3f} | {limits[n]:>9}")
    print(f" Показник степеня k (t ~ n^k): {loglog_slope(sizes, times):.2f}\n{'=' * 78}")


class PerformanceTests(TestCase):
    """Продуктивність і масштабування"""

    TRIAGE_SIZES, TRIAGE_LIMITS = (50, 100, 200, 500), {50: 1, 100: 1, 200: 1, 500: 2}
    FAIR_SIZES, FAIR_LIMITS = (25, 50, 100, 200), {25: 2, 50: 3, 100: 6, 200: 20}

    @staticmethod
    def _measure(func, sizes):
        times = []
        for n in sizes:
            stocks, requests_ = make_instance(n)
            t0 = time.perf_counter()
            plan = func(requests_, stocks)
            times.append(time.perf_counter() - t0)
            assert plan, f'порожній план на {n} заявках'
        return times

    def test_01_strict_priority_scaling(self):
        """Крива масштабування Тріажу: 50 / 100 / 200 / 500 заявок"""
        times = self._measure(lambda r, s: calculate_strict_priority(r, s, FlatRouting()), self.TRIAGE_SIZES)
        print_curve('Жорсткий розподіл (Тріаж)', self.TRIAGE_SIZES, times, self.TRIAGE_LIMITS)
        for n, t in zip(self.TRIAGE_SIZES, times):
            self.assertLess(t, self.TRIAGE_LIMITS[n], f'Тріаж на {n} заявках: {t:.2f} с')
        self.assertLess(loglog_slope(self.TRIAGE_SIZES, times), 2.5)

    def test_02_fair_distribution_scaling(self):
        """Крива масштабування Fairness (симплекс): 25 / 50 / 100 / 200 заявок"""
        times = self._measure(lambda r, s: calculate_distribution(r, s, routing_service=FlatRouting(), own_solver_max_requests=10 ** 9), self.FAIR_SIZES)
        print_curve('Справедливий розподіл (симплекс)', self.FAIR_SIZES, times, self.FAIR_LIMITS)
        for n, t in zip(self.FAIR_SIZES, times):
            self.assertLess(t, self.FAIR_LIMITS[n], f'Fairness на {n} заявках: {t:.2f} с')
        self.assertLess(loglog_slope(self.FAIR_SIZES, times), 3.0)

    def test_03_strict_vs_fair_speed(self):
        """Порівняння швидкості режимів на 200 заявках: Тріаж швидший за Fairness"""
        stocks, reqs = make_instance(200)
        t0 = time.perf_counter()
        calculate_strict_priority(reqs, stocks, FlatRouting())
        strict = time.perf_counter() - t0
        t0 = time.perf_counter()
        calculate_distribution(reqs, stocks, routing_service=FlatRouting(), own_solver_max_requests=10 ** 9)
        fair = time.perf_counter() - t0
        print(f"\n Порівняння часу на 200 заявках: Тріаж {strict:.3f} с | Fairness {fair:.3f} с")
        self.assertLess(strict, fair)

    def test_04_bulk_database_insert(self):
        """Пакетна вставка 1000 записів у БД виконується швидко"""
        unit, _ = Unit.objects.get_or_create(name='bulk-шт')
        cat, _ = Category.objects.get_or_create(slug='bulk-cat', defaults={'name': 'Bulk', 'criticality': 0.5})
        t0 = time.perf_counter()
        Resource.objects.bulk_create([Resource(name=f'Масовий ресурс {i}', unit=unit, category=cat) for i in range(1000)])
        elapsed = time.perf_counter() - t0
        self.assertEqual(Resource.objects.filter(name__startswith='Масовий ресурс').count(), 1000)
        self.assertLess(elapsed, 2.0)


# ======================================================================================
# 4. ПАРАЛЕЛЬНИЙ ДОСТУП
# ======================================================================================
@patch('app.utils.GeoFrontService', FakeFront)
@patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
class ConcurrencyTests(APITransactionTestCase):
    """Паралельний доступ"""

    def setUp(self):
        cache.clear()
        UserRequest.objects.all().delete()
        Stock.objects.all().delete()
        self.admin = User.objects.create_user('cc_admin', email='cc_admin@example.com', password='x', is_staff=True)
        self.user = User.objects.create_user('cc_user', email='cc_user@example.com', password='x')
        UserProfile.objects.create(user=self.user, is_approved=True)
        unit, _ = Unit.objects.get_or_create(name='cc-шт')
        cat, _ = Category.objects.get_or_create(slug='cc-cat', defaults={'name': 'Cc', 'criticality': 0.9})
        self.purpose, _ = RequestPurpose.objects.get_or_create(code='cc_p', defaults={'name': 'Cc', 'weight': 1.0})
        self.resource = Resource.objects.create(name='Cc ресурс', unit=unit, category=cat, max_per_request=100)
        self.wh = Warehouse.objects.create(name='Cc склад', location='м.', latitude=50, longitude=30)

    @staticmethod
    def _in_thread(user, func):
        client = APIClient()
        client.force_authenticate(user)
        try:
            return func(client)
        finally:
            connection.close()  # закриваємо з'єднання потоку, щоб тестова БД видалялася без помилок

    def test_01_parallel_reads(self):
        """20 паралельних читань API у 5 потоках без помилок і за прийнятний час"""
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as pool:
            codes = list(pool.map(lambda _: self._in_thread(self.admin, lambda c: c.get('/api/resources/').status_code), range(20)))
        self.assertTrue(all(c == 200 for c in codes))
        self.assertLess(time.perf_counter() - t0, 3.0)

    def test_02_parallel_distribution_never_oversells(self):
        """Паралельні запуски розподілу: склад не йде в мінус, виділене збігається зі списаним"""
        stock = Stock.objects.create(warehouse=self.wh, resource=self.resource, amount=100)
        for _ in range(5):
            UserRequest.objects.create(
                user=self.admin, resource=self.resource, purpose=self.purpose, quantity_requested=40, latitude=50.1,
                longitude=30.1, due_date=timezone.now().date() + timedelta(days=5), status='new')
        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(lambda _: self._in_thread(
                self.admin, lambda c: c.post('/api/distribute/', {'strategy': 'fairness'}, format='json').status_code), range(4)))
        self.assertTrue(set(codes) <= {200, 201, 423}, codes)
        self.assertIn(201, codes)
        stock.refresh_from_db()
        allocated = sum(UserRequest.objects.values_list('quantity_allocated', flat=True))
        self.assertGreaterEqual(stock.amount, 0)
        self.assertEqual(allocated, 100 - stock.amount)
        for r in UserRequest.objects.all():
            self.assertLessEqual(r.quantity_allocated, r.quantity_requested)

    def test_03_parallel_creation_respects_user_limit(self):
        """Паралельне створення заявок не обходить ліміт кількості на користувача"""
        payload = {'resource': self.resource.id, 'quantity_requested': 20, 'purpose': self.purpose.id, 'city': 'Київ',
                   'warehouse_address': 'Відділення 1', 'warehouse_ref': 'ADDRESS_DELIVERY',
                   'due_date': str(timezone.now().date() + timedelta(days=5))}
        with ThreadPoolExecutor(max_workers=10) as pool:
            codes = list(pool.map(lambda _: self._in_thread(
                self.user, lambda c: c.post('/api/requests/', payload, format='json').status_code), range(10)))
        total = sum(UserRequest.objects.filter(user=self.user).values_list('quantity_requested', flat=True))
        self.assertLessEqual(total, 100, f'ліміт 100 обійдено: {total} ({codes})')
        self.assertEqual(codes.count(201), total // 20)
