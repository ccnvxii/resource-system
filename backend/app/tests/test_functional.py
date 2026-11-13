"""
ФУНКЦІОНАЛЬНЕ ТЕСТУВАННЯ (API системи).

Категорії: автентифікація та акаунти, відновлення пароля, CRUD довідників і складу,
заявки (валідація, життєвий цикл, ліміти, права), розподіл ресурсів, інтеграція з Новою Поштою.
Оформлення для звіту: перший рядок докстрінга класу - категорія, test_NN - номер, докстрінг - назва.
"""
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app.models import (
    Category, DistributionItem, DistributionPlan, RequestPurpose, Resource, Stock, Unit, UserProfile, UserRequest,
    Warehouse,
)
from app.tests.helpers import FakeFront
from app.tests.mock_services import MockDistanceService


class FunctionalBase(APITestCase):
    """Спільні дані: адміністратор, підтверджений користувач, довідники, один склад."""

    def setUp(self):
        cache.clear()  # лічильники обмеження частоти не переходять між тестами
        UserRequest.objects.all().delete()
        Stock.objects.all().delete()
        self.today = timezone.now().date()
        self.admin = User.objects.create_user('ft_admin', email='ft_admin@example.com', password='Str0ng-Pass-77', is_staff=True)
        self.user = User.objects.create_user('ft_user', email='ft_user@example.com', password='Str0ng-Pass-77')
        UserProfile.objects.create(user=self.user, is_approved=True)
        self.other = User.objects.create_user('ft_other', email='ft_other@example.com', password='Str0ng-Pass-77')
        UserProfile.objects.create(user=self.other, is_approved=True)

        self.unit, _ = Unit.objects.get_or_create(name='ft-шт')
        self.cat, _ = Category.objects.get_or_create(slug='ft-cat', defaults={'name': 'FT', 'criticality': 0.7})
        self.p_hi, _ = RequestPurpose.objects.get_or_create(code='ft_hi', defaults={'name': 'Високий', 'weight': 1.0})
        self.p_lo, _ = RequestPurpose.objects.get_or_create(code='ft_lo', defaults={'name': 'Низький', 'weight': 0.2})
        self.regular = Resource.objects.create(name='FT звичайний', unit=self.unit, category=self.cat, max_per_request=100)
        self.strategic = Resource.objects.create(name='FT стратегічний', unit=self.unit, category=self.cat, is_strategic=True)
        self.wh = Warehouse.objects.create(name='FT склад', location='Київ', latitude=50.0, longitude=30.0)

    def req_payload(self, qty=10, days=5, **extra):
        data = {
            'resource': self.regular.id, 'quantity_requested': qty, 'purpose': self.p_hi.id,
            'city': 'Київ', 'warehouse_address': 'Відділення 1', 'warehouse_ref': 'ADDRESS_DELIVERY',
            'due_date': str(self.today + timedelta(days=days)),
        }
        data.update(extra)
        return data

    def make_request(self, owner=None, resource=None, qty=10, purpose=None, days=5, **kw):
        return UserRequest.objects.create(
            user=owner or self.user, resource=resource or self.regular, quantity_requested=qty,
            purpose=purpose or self.p_hi, due_date=self.today + timedelta(days=days), status='new',
            latitude=50.1, longitude=30.1, city='Київ', **kw)


@patch('app.utils.GeoFrontService', FakeFront)
class AuthenticationTests(FunctionalBase):
    """Автентифікація та акаунти"""

    def _register(self, email='new_user@example.com', password='Str0ng-Pass-77'):
        return self.client.post('/api/register/', {
            'username': email, 'email': email, 'password': password, 'first_name': 'Іван', 'last_name': 'Петренко',
            'phone': '+380671234567', 'organization': 'Підрозділ 1'}, format='json')

    def _login(self, username, password='Str0ng-Pass-77'):
        return self.client.post('/api/token/', {'username': username, 'password': password}, format='json')

    def test_01_jwt_login_and_refresh(self):
        """Вхід за логіном і паролем, отримання та оновлення JWT, відхилення неправильного пароля"""
        resp = self._login('ft_user')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        refreshed = self.client.post('/api/token/refresh/', {'refresh': resp.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn('access', refreshed.data)
        self.assertEqual(self._login('ft_user', 'Wrong-Pass-1').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_02_registration_and_admin_approval(self):
        """Реєстрація, блокування входу до підтвердження, вхід після підтвердження адміністратором"""
        self.assertEqual(self._register().status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='new_user@example.com')
        self.assertFalse(user.profile.is_approved)
        blocked = self._login('new_user@example.com')
        self.assertEqual(blocked.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(blocked.data.get('code'), 'not_approved')
        user.profile.is_approved = True
        user.profile.save()
        self.assertEqual(self._login('new_user@example.com').status_code, status.HTTP_200_OK)

    def test_03_registration_validation(self):
        """Валідація реєстрації: повторний email (без урахування регістру), некоректний формат, адмін входить без підтвердження"""
        self.assertEqual(self._register('dup@example.com').status_code, status.HTTP_201_CREATED)
        self.assertEqual(self._register('DUP@example.com').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._register('abc').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._login('ft_admin').status_code, status.HTTP_200_OK)


class PasswordResetTests(FunctionalBase):
    """Відновлення пароля"""

    URL = '/api/password-reset/'

    def _code(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def test_01_full_flow(self):
        """Повний сценарій: код на пошту, перевірка коду, зміна пароля, одноразовість коду"""
        self.assertEqual(self.client.post(self.URL, {'email': 'ft_user@example.com'}, format='json').status_code, 200)
        self.assertEqual(mail.outbox[-1].to, ['ft_user@example.com'])
        code = self._code()
        verify = self.client.post(self.URL + 'verify/', {'email': 'ft_user@example.com', 'code': code}, format='json')
        self.assertEqual(verify.status_code, 200)                                  # перевірка не «спалює» код
        done = self.client.post(self.URL + 'confirm/', {'email': 'ft_user@example.com', 'code': code,
                                                         'new_password': 'BrandNewPass123'}, format='json')
        self.assertEqual(done.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass123'))
        again = self.client.post(self.URL + 'confirm/', {'email': 'ft_user@example.com', 'code': code,
                                                          'new_password': 'AnotherPass123'}, format='json')
        self.assertEqual(again.status_code, 400)

    def test_02_protection_scenarios(self):
        """Захисні сценарії: некоректний email, невідомий акаунт, невірний код та ліміт спроб, слабкий пароль, пауза між запитами"""
        self.assertEqual(self.client.post(self.URL, {'email': 'not-an-email'}, format='json').status_code, 400)
        unknown = self.client.post(self.URL, {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(unknown.status_code, 200)                                 # однакова відповідь, лист не надсилається
        self.assertEqual(len(mail.outbox), 0)

        self.client.post(self.URL, {'email': 'ft_user@example.com'}, format='json')
        self.assertEqual(self.client.post(self.URL, {'email': 'ft_user@example.com'}, format='json').status_code, 429)
        code = self._code()
        weak = self.client.post(self.URL + 'confirm/', {'email': 'ft_user@example.com', 'code': code, 'new_password': '123'}, format='json')
        self.assertEqual(weak.status_code, 400)
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(5):
            bad = self.client.post(self.URL + 'confirm/', {'email': 'ft_user@example.com', 'code': wrong, 'new_password': 'BrandNewPass123'}, format='json')
            self.assertEqual(bad.status_code, 400)
        late = self.client.post(self.URL + 'confirm/', {'email': 'ft_user@example.com', 'code': code, 'new_password': 'BrandNewPass123'}, format='json')
        self.assertEqual(late.status_code, 400)                                    # після 5 спроб навіть правильний код не діє
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Str0ng-Pass-77'))

    def test_03_mail_failure_is_reported(self):
        """Збій поштового сервера: зрозуміла помилка 503, повтор можливий одразу"""
        with patch('django.core.mail.send_mail', side_effect=OSError('smtp down')):
            resp = self.client.post(self.URL, {'email': 'ft_user@example.com'}, format='json')
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(self.client.post(self.URL, {'email': 'ft_user@example.com'}, format='json').status_code, 200)


class ReferenceDataTests(FunctionalBase):
    """Довідники, склад та інтеграція з Новою Поштою"""

    def test_01_crud_via_api(self):
        """Створення, читання, зміна та видалення категорій, ресурсів і складів через API (адміністратор)"""
        self.client.force_authenticate(self.admin)
        cases = [
            ('/api/categories/', {'name': 'Нова категорія', 'slug': 'new-cat', 'criticality': 0.6}, {'criticality': 0.9}),
            ('/api/resources/', {'name': 'Новий ресурс', 'unit': self.unit.id, 'category': self.cat.id, 'is_strategic': False},
             {'is_strategic': True}),
            ('/api/warehouses/', {'name': 'Новий склад', 'location': 'Львів', 'latitude': 49.8, 'longitude': 24.0}, {'location': 'Одеса'}),
        ]
        for url, payload, change in cases:
            created = self.client.post(url, payload, format='json')
            self.assertEqual(created.status_code, 201, (url, created.data))
            item_url = f'{url}{created.data["id"]}/'
            self.assertEqual(self.client.get(item_url).status_code, 200)
            patched = self.client.patch(item_url, change, format='json')
            self.assertEqual(patched.status_code, 200)
            for key, value in change.items():
                self.assertEqual(patched.data[key], value)
            self.assertEqual(self.client.delete(item_url).status_code, 204)
            self.assertEqual(self.client.get(item_url).status_code, 404)
        for url in ('/api/units/', '/api/purposes/'):                                # довідники лише для читання
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.post(url, {}, format='json').status_code, 405)

    def test_02_reference_data_is_admin_only(self):
        """Права: звичайний користувач бачить довідники, але не може їх змінювати"""
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/resources/').status_code, 200)
        resp = self.client.post('/api/warehouses/', {'name': 'X', 'location': 'Y', 'latitude': 1, 'longitude': 1}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.client.get('/api/users/').status_code, 403)

    def test_03_stock_management(self):
        """Запаси: зміна кількості, поповнення (існуючий і новий склад), відхилення некоректних значень, видалення"""
        stock = Stock.objects.create(warehouse=self.wh, resource=self.regular, amount=10)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/stocks/{stock.id}/update_amount/', {'amount': 25}, format='json').status_code, 200)
        stock.refresh_from_db()
        self.assertEqual(stock.amount, 25)
        for bad in (-5, 'abc'):
            self.assertEqual(self.client.patch(f'/api/stocks/{stock.id}/update_amount/', {'amount': bad}, format='json').status_code, 400)

        add = self.client.post('/api/stocks/add_resource/', {'warehouse': self.wh.id, 'resource': self.regular.id, 'amount': 5}, format='json')
        self.assertEqual(add.status_code, 200)
        stock.refresh_from_db()
        self.assertEqual(stock.amount, 30)
        wh2 = Warehouse.objects.create(name='FT склад 2', location='Одеса', latitude=46.4, longitude=30.7)
        self.client.post('/api/stocks/add_resource/', {'warehouse': wh2.id, 'resource': self.regular.id, 'amount': 7}, format='json')
        self.assertEqual(Stock.objects.get(warehouse=wh2, resource=self.regular).amount, 7)
        self.assertEqual(self.client.post('/api/stocks/add_resource/', {'warehouse': self.wh.id}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/stocks/add_resource/', {'warehouse': self.wh.id, 'resource': self.regular.id, 'amount': -50}, format='json').status_code, 400)

        self.client.force_authenticate(self.user)                                    # права звичайного користувача
        self.assertEqual(self.client.patch(f'/api/stocks/{stock.id}/update_amount/', {'amount': 1}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/stocks/{stock.id}/').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'/api/stocks/{stock.id}/').status_code, 204)



    def test_04_nova_poshta_proxy(self):
        """Доступ лише для авторизованих, підтримка дій get_cities / get_warehouses / get_streets, відхилення невідомої дії"""
        self.assertEqual(self.client.post("/api/novaposhta/", {'action': 'get_cities'}, format='json').status_code, 401)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/novaposhta/", {'action': 'hack'}, format='json').status_code, 400)
        with patch('app.views.NovaPoshtaService') as svc:
            svc.return_value.get_cities.return_value = {'data': [{'Addresses': [{'Present': 'м. Київ', 'Ref': 'abc'}]}]}
            svc.return_value.get_warehouses.return_value = {'data': [{'Ref': 'w1', 'Description': 'Відділення №1'}]}
            svc.return_value.get_streets.return_value = {'data': [{'Addresses': [{'Present': 'вул. Соборна', 'Ref': 's1'}]}]}
            cities = self.client.post("/api/novaposhta/", {'action': 'get_cities', 'search': 'Київ'}, format='json')
            warehouses = self.client.post("/api/novaposhta/", {'action': 'get_warehouses', 'city_ref': 'abc'}, format='json')
            streets = self.client.post("/api/novaposhta/", {'action': 'get_streets', 'city_ref': 'abc', 'search': 'Соб'}, format='json')
        self.assertEqual(cities.data[0]['Present'], 'м. Київ')
        self.assertEqual(warehouses.data[0]['Description'], 'Відділення №1')
        self.assertEqual(streets.data[0]['Presentation'], 'вул. Соборна')


@patch('app.utils.GeoFrontService', FakeFront)
class RequestTests(FunctionalBase):
    """Заявки"""

    def test_01_validation(self):
        """Валідація: від'ємна кількість, неіснуючий ресурс, дата у минулому, надто довгий текст"""
        self.client.force_authenticate(self.user)
        for payload in (self.req_payload(qty=-15), self.req_payload(resource=999999),
                        self.req_payload(days=-2), self.req_payload(city='А' * 100_000)):
            self.assertEqual(self.client.post('/api/requests/', payload, format='json').status_code, 400, payload)

    def test_02_lifecycle_and_automatic_owner(self):
        """Життєвий цикл: створення (заявник визначається автоматично), зміна кількості та автопродовження, видалення"""
        self.client.force_authenticate(self.user)
        created = self.client.post('/api/requests/', self.req_payload(qty=25), format='json')
        self.assertEqual(created.status_code, 201)
        req = UserRequest.objects.get(id=created.data['id'])
        self.assertEqual((req.user_id, req.status, req.quantity_allocated), (self.user.id, 'new', 0))
        url = f'/api/requests/{req.id}/'
        patched = self.client.patch(url, {'quantity_requested': 45, 'auto_extend': False}, format='json')
        self.assertEqual((patched.data['quantity_requested'], patched.data['auto_extend']), (45, False))
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(UserRequest.objects.filter(id=req.id).exists())

    def test_03_quantity_limits(self):
        """Ліміти кількості: на одну заявку, сумарно по активних заявках, при збільшенні; адміністратор без обмежень"""
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/requests/', self.req_payload(qty=101), format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/requests/', self.req_payload(qty=60), format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/requests/', self.req_payload(qty=50), format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/requests/', self.req_payload(qty=40), format='json').status_code, 201)
        req = UserRequest.objects.filter(user=self.user).first()
        self.assertEqual(self.client.patch(f'/api/requests/{req.id}/', {'quantity_requested': 500}, format='json').status_code, 400)
        self.client.force_authenticate(self.admin)
        big = self.client.post('/api/requests/', self.req_payload(qty=5000, user=self.user.id), format='json')
        self.assertEqual(big.status_code, 201)

    def test_04_access_rights(self):
        """Права доступу: користувач бачить і змінює лише свої заявки, адміністратор - усі; термін лише продовжується"""
        mine, theirs = self.make_request(self.user), self.make_request(self.other)
        self.client.force_authenticate(self.user)
        ids = [r['id'] for r in self.client.get('/api/requests/').data]
        self.assertIn(mine.id, ids)
        self.assertNotIn(theirs.id, ids)
        self.assertEqual(self.client.patch(f'/api/requests/{theirs.id}/', {'quantity_requested': 5}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/requests/{theirs.id}/').status_code, 404)
        self.client.patch(f'/api/requests/{mine.id}/', {'user': self.other.id}, format='json')
        mine.refresh_from_db()
        self.assertEqual(mine.user_id, self.user.id)                                 # передати заявку іншому не можна
        shorter = self.client.patch(f'/api/requests/{mine.id}/', {'due_date': str(self.today + timedelta(days=1))}, format='json')
        self.assertEqual(shorter.status_code, 400)
        longer = self.client.patch(f'/api/requests/{mine.id}/', {'due_date': str(self.today + timedelta(days=9))}, format='json')
        self.assertEqual(longer.status_code, 200)
        self.client.force_authenticate(self.admin)
        ids = {r['id'] for r in self.client.get('/api/requests/').data}
        self.assertTrue({mine.id, theirs.id} <= ids)

    def test_05_unapproved_applicant_is_rejected(self):
        """Адміністратор не може створити заявку на непідтвердженого користувача"""
        pending = User.objects.create_user('ft_pending', email='ft_pending@example.com', password='x')
        UserProfile.objects.create(user=pending, is_approved=False)
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/requests/', self.req_payload(user=pending.id), format='json')
        self.assertEqual(resp.status_code, 403)


@patch('app.utils.GeoFrontService', FakeFront)
@patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
class DistributionTests(FunctionalBase):
    """Розподіл ресурсів"""

    URL = '/api/distribute/'

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.admin)

    def _stock(self, resource, amount):
        return Stock.objects.create(warehouse=self.wh, resource=resource, amount=amount)

    def _run(self, strategy=None):
        return self.client.post(self.URL, {} if strategy is None else {'strategy': strategy}, format='json')

    def _alloc(self, req):
        req.refresh_from_db()
        return req.quantity_allocated

    def test_01_fairness_applies_plan(self):
        """Fairness: застосування плану до складів і заявок, статуси «частково» та «виконано», збереження кількості"""
        stock = self._stock(self.regular, 10)
        a, b = self.make_request(qty=10), self.make_request(qty=10)
        resp = self._run('fairness')
        self.assertEqual(resp.status_code, 201)
        stock.refresh_from_db()
        self.assertEqual(self._alloc(a) + self._alloc(b), 10)
        self.assertEqual(stock.amount, 0)                                            # видане = початковий запас - залишок
        self.assertEqual(DistributionPlan.objects.count(), 1)
        self.assertEqual(DistributionItem.objects.count(), len(resp.data['items']))
        a.refresh_from_db()
        self.assertEqual(a.status, 'partial')
        Stock.objects.update(amount=50)
        UserRequest.objects.update(quantity_allocated=0, status='new', quantity_requested=10)
        self._run('fairness')
        a.refresh_from_db()
        self.assertEqual((a.quantity_allocated, a.status), (10, 'done'))

    def test_02_triage_and_hybrid_modes(self):
        """Тріаж і гібридний режим: жорсткий пріоритет для стратегічних ресурсів, справедливий розподіл для решти"""
        self._stock(self.regular, 10)
        self._stock(self.strategic, 10)
        reg_a, reg_b = self.make_request(qty=10), self.make_request(qty=10)
        st_top = self.make_request(resource=self.strategic, qty=10, purpose=self.p_hi)
        st_low = self.make_request(resource=self.strategic, qty=10, purpose=self.p_lo)
        self.assertEqual(self._run('hybrid').status_code, 201)
        self.assertEqual((self._alloc(reg_a), self._alloc(reg_b)), (5, 5))           # звичайний ресурс - порівну
        self.assertEqual((self._alloc(st_top), self._alloc(st_low)), (10, 0))        # стратегічний - за пріоритетом

        Stock.objects.update(amount=10)
        UserRequest.objects.update(quantity_allocated=0, status='new')
        self.assertEqual(self._run('triage').status_code, 201)                       # чистий Тріаж: і для звичайного
        self.assertEqual(self._alloc(reg_a) + self._alloc(reg_b), 10)
        self.assertTrue(self._alloc(reg_a) == 10 or self._alloc(reg_b) == 10)

        Stock.objects.update(amount=10)
        UserRequest.objects.update(quantity_allocated=0, status='new')
        self.assertEqual(self._run().status_code, 201)                               # режим за замовчуванням - гібридний
        self.assertEqual((self._alloc(reg_a), self._alloc(reg_b)), (5, 5))

    def test_03_repeated_run_and_empty_plan(self):
        """Повторний запуск розподіляє лише залишок; без запасів плану немає"""
        self.make_request(qty=5)
        empty = self._run('fairness')
        self.assertEqual(empty.status_code, 200)
        self.assertIn('message', empty.data)
        self.assertEqual(DistributionPlan.objects.count(), 0)
        UserRequest.objects.all().delete()
        stock = self._stock(self.regular, 4)
        req = self.make_request(qty=10)
        self._run('fairness')
        self.assertEqual(self._alloc(req), 4)
        stock.refresh_from_db()
        stock.amount = 20
        stock.save()
        self._run('fairness')
        req.refresh_from_db()
        self.assertEqual((req.quantity_allocated, req.status), (10, 'done'))
        stock.refresh_from_db()
        self.assertEqual(stock.amount, 14)

    def test_04_overdue_requests(self):
        """Прострочені заявки: без автопродовження - «протермінована», з автопродовженням - +5 днів і обслуговується"""
        self._stock(self.regular, 20)
        expired = self.make_request(qty=5, days=-2, auto_extend=False)
        extended = self.make_request(qty=5, days=-2, auto_extend=True)
        self.assertEqual(self._run('fairness').status_code, 201)
        expired.refresh_from_db(), extended.refresh_from_db()
        self.assertEqual((expired.status, expired.quantity_allocated), ('expired', 0))
        self.assertEqual(extended.due_date, self.today + timedelta(days=5))
        self.assertEqual((extended.extension_count, extended.quantity_allocated), (1, 5))

    def test_05_atomic_rollback_on_failure(self):
        """Атомарність: при збої оптимізатора відкочуються всі зміни (залишки, статуси, плани)"""
        stock = self._stock(self.regular, 10)
        overdue = self.make_request(qty=5, days=-2, auto_extend=False)
        ok = self.make_request(qty=5)
        with patch('app.views.calculate_distribution', side_effect=RuntimeError('збій оптимізатора')):
            resp = self._run('fairness')
        self.assertEqual(resp.status_code, status.HTTP_423_LOCKED)
        stock.refresh_from_db(), overdue.refresh_from_db(), ok.refresh_from_db()
        self.assertEqual((stock.amount, overdue.status, ok.quantity_allocated), (10, 'new', 0))
        self.assertEqual((DistributionPlan.objects.count(), DistributionItem.objects.count()), (0, 0))

    def test_06_audit_log(self):
        """Журнал розподілу: перелік операцій з деталями (звідки, куди, кому), доступ лише адміністратору"""
        self._stock(self.regular, 10)
        self.make_request(qty=10)
        plan_id = self._run('fairness').data['id']
        rows = self.client.get('/api/logs/').data
        rows = rows if isinstance(rows, list) else rows.get('results', [])
        self.assertTrue(rows)
        for field in ('plan_id', 'resource_name', 'warehouse_name', 'amount', 'user_full_name', 'city',
                      'quantity_requested', 'purpose_name'):
            self.assertIn(field, rows[0])
        self.assertEqual(rows[0]['plan_id'], plan_id)
        self.client.force_authenticate(self.user)
        self.assertIn(self.client.get('/api/logs/').status_code, (401, 403))
        self.assertEqual(self._run('fairness').status_code, 403)                     # запуск лише для адміністратора
