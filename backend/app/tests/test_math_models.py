"""
МАТЕМАТИЧНІ МОДЕЛІ: приоритет заявки, справедливий розподіл (Fairness), жорсткий розподіл (Тріаж).

Кожен тест перевіряє одну групу властивостей. Оформлення для звіту:
перший рядок докстрінга класу - категорія, методи test_NN - порядкові номери, перший рядок докстрінга - назва.
Використовуються лише власні реалізації алгоритмів.
"""
import math
import random
import unittest
from datetime import timedelta
from unittest.mock import patch

import numpy as np
from django.test import TestCase
from django.utils import timezone

from app import priority_refresh
from app.models import RequestPurpose, Resource, UserRequest
from django.contrib.auth.models import User
from app.optimizer.distribute import (
    calculate_distribution, calculate_strict_priority, discretize_with_greedy_remainders,
    pivot_step, simplex_solve,
)
from app.tests.helpers import (
    EuclidRouting, FakeFront, FlatRouting, allocated_by_request, check_invariants, random_instance,
)
from app.utils import (
    calculate_front_multiplier, calculate_request_priority, calculate_time_multiplier, priority_to_display,
)

KM_PER_DEG_LAT = 111.19
FRONT_POINT = (50.0, 36.0)


def point_at_km(km):
    """Точка рівно на km кілометрів південніше від точки фронту."""
    return FRONT_POINT[0] - km / KM_PER_DEG_LAT, FRONT_POINT[1]


def day(n):
    return timezone.now().date() + timedelta(days=n)


@patch('app.utils.GeoFrontService', FakeFront)
class PriorityModelTests(TestCase):
    """Пріоритет заявки"""

    def test_01_time_multiplier(self):
        """Часовий множник: -5 % за день, межі [0.5; 1.0], порожній і некоректний строк"""
        self.assertEqual(calculate_time_multiplier(day(0)), 1.0)
        self.assertEqual(calculate_time_multiplier(day(-3)), 1.0)
        for days, expected in ((1, 0.95), (5, 0.75), (9, 0.55), (10, 0.5), (11, 0.5), (365, 0.5)):
            self.assertAlmostEqual(calculate_time_multiplier(day(days)), expected, places=6)
        self.assertEqual(calculate_time_multiplier(None), 0.5)
        self.assertEqual(calculate_time_multiplier('не-дата'), 0.5)
        iso = (timezone.now().date() + timedelta(days=5)).strftime('%Y-%m-%d')
        self.assertAlmostEqual(calculate_time_multiplier(iso), 0.75, places=6)
        values = [calculate_time_multiplier(day(d)) for d in range(30)]
        self.assertTrue(all(a >= b for a, b in zip(values, values[1:])))     # ближчий строк - не менш терміновий

    def test_02_geo_multiplier_zones(self):
        """Геомножник: бойова, прифронтова зона та тил, значення за замовчуванням"""
        self.assertEqual(calculate_front_multiplier(None, None), 0.15)
        self.assertEqual(calculate_front_multiplier('abc', 'def'), 0.15)
        self.assertAlmostEqual(calculate_front_multiplier(*FRONT_POINT), 1.0, places=3)
        for km in (20, 60, 95):                                                # бойова зона: експонента
            self.assertAlmostEqual(calculate_front_multiplier(*point_at_km(km)), math.exp(-km / 120.0), places=2)
        for km in (110, 150, 215):                                             # прифронтова: константа
            self.assertAlmostEqual(calculate_front_multiplier(*point_at_km(km)), 0.45, places=3)
        self.assertAlmostEqual(calculate_front_multiplier(*point_at_km(250)), 0.33 * math.exp(-30 / 150.0), places=2)
        self.assertEqual(calculate_front_multiplier(*point_at_km(2000)), 0.15)  # тил: нижня межа
        values = [calculate_front_multiplier(*point_at_km(km)) for km in (0, 30, 80, 150, 260, 400, 1000)]
        self.assertTrue(all(a >= b - 1e-9 for a, b in zip(values, values[1:])))
        self.assertTrue(all(0.0 <= v <= 1.0 for v in values))

        class Empty(FakeFront):
            points = []
        with patch('app.utils.GeoFrontService', Empty):
            self.assertEqual(calculate_front_multiplier(50.0, 36.0), 0.15)    # лінія фронту недоступна

    def test_03_priority_formula(self):
        """Зведена формула: вагові коефіцієнти, ручний розрахунок, захищений діапазон"""
        self.assertAlmostEqual(calculate_request_priority(1.0, 1.0, *FRONT_POINT, day(0), 0), 1.0, places=3)
        lat, lon = point_at_km(150)                                            # k_geo = 0.45, k_time = 0.75
        expected = 0.35 * 0.8 + 0.25 * 0.75 + 0.25 * 0.45 + 0.15 * 0.6 - 0.02
        self.assertAlmostEqual(calculate_request_priority(0.8, 0.6, lat, lon, day(5), 2), round(expected, 3), places=3)
        self.assertGreater(calculate_request_priority(1.0, 0.5, lat, lon, day(5), 0),
                           calculate_request_priority(0.6, 0.5, lat, lon, day(5), 0))   # вага призначення
        self.assertEqual((priority_to_display(0.22), priority_to_display(0.65), priority_to_display(1.0)), (2.2, 6.5, 10.0))
        self.assertEqual((priority_to_display(0.1), priority_to_display(0.03), priority_to_display(None)), (1.0, 1.0, 1.0))   # нижня межа 1
        for purpose in (0.0, 0.5, 1.0):
            for km in (0, 150, 1000):
                for days in (-5, 0, 7, 100):
                    for ext in (0, 3, 20):
                        la, lo = point_at_km(km)
                        p = calculate_request_priority(purpose, purpose, la, lo, day(days), ext)
                        self.assertTrue(0.1 <= p <= 1.0, (purpose, km, days, ext, p))

    def test_04_deadline_and_extension_effect(self):
        """Строк і продовження: ближчий дедлайн підвищує пріоритет, продовження знижує (штраф до 0.05)"""
        lat, lon = point_at_km(150)
        near = calculate_request_priority(0.5, 0.5, lat, lon, day(1), 0)
        far = calculate_request_priority(0.5, 0.5, lat, lon, day(9), 0)
        self.assertGreater(near, far)
        base = calculate_request_priority(0.5, 0.5, lat, lon, day(3), 0)
        one = calculate_request_priority(0.5, 0.5, lat, lon, day(3), 1)
        many = calculate_request_priority(0.5, 0.5, lat, lon, day(3), 50)
        self.assertLess(one, base)
        self.assertAlmostEqual(base - many, 0.05, places=3)

    def test_05_daily_priority_refresh(self):
        """Щодобове оновлення пріоритетів: масово, раз на добу, лише близькі дедлайни та активні заявки"""
        priority_refresh._last_refresh_date = None
        UserRequest.objects.all().delete()  # ізоляція від демонстраційних заявок засіву
        user = User.objects.create_user('pr_user', email='pr@example.com', password='x')
        resource, purpose = Resource.objects.first(), RequestPurpose.objects.first()

        def make(days, status='new'):
            return UserRequest.objects.create(
                user=user, resource=resource, quantity_requested=5, purpose=purpose,
                due_date=day(days), status=status)

        near, far, done = make(3), make(30), make(1)
        UserRequest.objects.filter(pk__in=[near.pk, far.pk, done.pk]).update(priority=0.01)
        UserRequest.objects.filter(pk=done.pk).update(status='done')

        self.assertEqual(priority_refresh.refresh_stale_priorities(), 1)      # лише близька активна заявка
        near.refresh_from_db(), far.refresh_from_db(), done.refresh_from_db()
        self.assertNotEqual(near.priority, 0.01)
        self.assertEqual((far.priority, done.priority), (0.01, 0.01))
        UserRequest.objects.filter(pk=near.pk).update(priority=0.01)
        self.assertEqual(priority_refresh.refresh_stale_priorities(), 0)      # вже виконано сьогодні
        self.assertEqual(priority_refresh.refresh_stale_priorities(force=True), 1)


class FairDistributionTests(unittest.TestCase):
    """Справедливий розподіл (Fairness)"""

    @staticmethod
    def _stock(amount, wid=1, lat=50.0, lng=30.0, res=1):
        return {'warehouse_id': wid, 'resource_id': res, 'amount': amount, 'lat': lat, 'lng': lng}

    @staticmethod
    def _req(rid, need, prio, lat=50.1, lng=30.1, res=1):
        return {'id': rid, 'resource_id': res, 'amount_needed': need, 'priority': prio, 'lat': lat, 'lng': lng}

    def _run(self, requests, stocks, routing=None):
        return allocated_by_request(calculate_distribution(requests, stocks, routing_service=routing or FlatRouting()))

    def test_01_simplex_core(self):
        """Симплекс-метод: опорний крок, оптимум, неприпустима та необмежена задачі, ліміт ітерацій"""
        tableau = np.array([[2.0, 1.0, 1.0, 0.0, 10.0], [1.0, 2.0, 0.0, 1.0, 8.0], [-3.0, -2.0, 0.0, 0.0, 0.0]])
        pivot_step(tableau, pivot_row=0, pivot_col=0)
        self.assertAlmostEqual(tableau[0, 0], 1.0)
        self.assertAlmostEqual(tableau[2, -1], 15.0)
        with self.assertRaises(ZeroDivisionError):
            pivot_step(np.array([[0.0, 1.0, 5.0]]), pivot_row=0, pivot_col=0)

        status, x = simplex_solve(np.array([[1.0, 1.0], [1.0, -1.0]]), np.array([4.0, 2.0]),
                                  np.array([-3.0, -2.0]), ['<=', '<='])
        self.assertEqual(status, 'optimal')
        self.assertAlmostEqual(x[0], 3.0, places=6)
        self.assertAlmostEqual(x[1], 1.0, places=6)
        self.assertEqual(simplex_solve(np.array([[1.0], [1.0]]), np.array([5.0, 2.0]), np.array([-1.0]), ['>=', '<='])[0], 'infeasible')
        self.assertEqual(simplex_solve(np.array([[1.0, -1.0]]), np.array([2.0]), np.array([-1.0, 0.0]), ['<='])[0], 'unbounded')
        self.assertEqual(simplex_solve(np.array([[1.0, 1.0], [2.0, 1.0]]), np.array([4.0, 5.0]),
                                       np.array([-3.0, -2.0]), ['<=', '<='], max_iters=1)[0], 'iteration_limit_reached')
        self.assertEqual(simplex_solve(np.array([[1.0, 0.0], [0.5, 1.0]]), np.array([2.0, 1.0]),
                                       np.array([-2.0, -1.0]), ['<=', '<='])[0], 'optimal')    # виродження

    def test_02_discretization(self):
        """Дискретизація: цілі частки, жадібний розподіл залишків за пріоритетом, фільтрація шуму"""
        actual = discretize_with_greedy_remainders(
            np.array([[2.4, 2.4]]), [{'amount': 5}],
            [{'amount_needed': 3, 'priority': 0.9}, {'amount_needed': 3, 'priority': 0.5}])
        np.testing.assert_array_equal(actual, np.array([[3, 2]]))
        noise = discretize_with_greedy_remainders(np.array([[1e-9]]), [{'amount': 10}], [{'amount_needed': 10, 'priority': 0.5}])
        np.testing.assert_array_equal(noise, np.array([[0]]))

    def test_03_priority_proportionality(self):
        """Пропорційність пріоритетам: рівні пріоритети - порівну, різні - пропорційно вазі"""
        got = self._run([self._req(1, 10, 0.5), self._req(2, 10, 0.5, 50.2, 30.2)], [self._stock(10)])
        self.assertEqual((got[1], got[2]), (5.0, 5.0))
        got = self._run([self._req(1, 10, 0.9), self._req(2, 10, 0.3, 50.2, 30.2)], [self._stock(12)])
        self.assertEqual((got[1], got[2]), (9.0, 3.0))                           # відношення 9:3
        got = self._run([self._req(1, 10, 1.0), self._req(2, 10, 0.2, 50.2, 30.2)], [self._stock(10)])
        self.assertGreater(got[1], got[2])
        got = self._run([self._req(1, 20, 0.8), self._req(2, 5, 0.4, 50.2, 30.2)], [self._stock(15)])
        self.assertEqual(sum(got.values()), 15.0)

    def test_04_boundary_cases(self):
        """Граничні випадки: нульова потреба, нульовий запас, крайній дефіцит, надлишок, порожній вхід"""
        got = self._run([self._req(1, 0, 1.0), self._req(2, 5, 0.5, 50.2, 30.2)], [self._stock(10)])
        self.assertEqual(got.get(1, 0.0), 0.0)
        self.assertEqual(got[2], 5.0)
        self.assertEqual(calculate_distribution([self._req(1, 10, 1.0)], [self._stock(0)], routing_service=FlatRouting()), [])
        got = self._run([self._req(i, 10, 0.5, 50 + i / 10, 30) for i in (1, 2, 3)], [self._stock(1)])
        self.assertEqual(sum(got.values()), 1.0)                                  # одна одиниця на трьох
        self.assertEqual(sum(self._run([self._req(1, 10, 0.5)], [self._stock(10000)]).values()), 10)
        self.assertEqual(sum(self._run([self._req(1, 4, 0.5), self._req(2, 4, 0.5, 50.2, 30.2)], [self._stock(15)]).values()), 8.0)
        self.assertEqual(calculate_distribution([], [], routing_service=FlatRouting()), [])
        self.assertEqual(self._run([self._req(1, 4, 0.5), self._req(2, 4, 0.5, 50.2, 30.2)], [self._stock(4)]), {1: 2.0, 2: 2.0})

    def test_05_logistics_second_stage(self):
        """Логістика (етап 2): найближчий склад, бонус за повне виконання, пріоритет важливіший за відстань"""
        class NearFar:
            def get_distance(self, *a):
                return 5.0

            def get_distance_matrix(self, s, d):
                return np.array([[5.0], [50.0]])

        plan = calculate_distribution([self._req(1, 5, 0.5, 50.0, 30.0)],
                                      [self._stock(10, 1, 50.05, 30.05), self._stock(10, 2, 50.5, 30.5)], routing_service=NearFar())
        self.assertEqual([p['warehouse_id'] for p in plan], [1])                  # обрано ближчий склад

        plan = calculate_distribution([self._req(1, 10, 0.5, 50.0, 30.0)],
                                      [self._stock(5, 1, 50.1, 30.1), self._stock(10, 2, 50.1, 30.1)], routing_service=FlatRouting())
        self.assertEqual([(p['warehouse_id'], p['amount']) for p in plan], [(2, 10.0)])   # один склад закриває замовлення

        class Tradeoff:
            def get_distance(self, *a):
                return 1.0

            def get_distance_matrix(self, s, d):
                return np.array([[50.0, 1.0]])

        got = self._run([self._req(1, 5, 1.0, 50.5, 30.5), self._req(2, 5, 0.2, 50.01, 30.01)], [self._stock(5)], Tradeoff())
        self.assertGreater(got[1], got.get(2, 0))                                  # далека, але пріоритетна заявка

    def test_06_multi_resource_and_multi_warehouse(self):
        """Кілька ресурсів і складів: ресурси незалежні, весь запас розподіляється"""
        stocks = [self._stock(10, 1, res=1), self._stock(5, 1, res=2)]
        got = self._run([self._req(1, 10, 0.8, res=1), self._req(2, 5, 0.4, res=2)], stocks)
        self.assertEqual((got[1], got[2]), (10.0, 5.0))
        stocks = [self._stock(6, 1), self._stock(4, 2, 50.1, 30.1)]
        reqs = [self._req(1, 5, 1.0, 50.05, 30.05), self._req(2, 5, 0.6, 50.08, 30.08), self._req(3, 5, 0.2, 50.12, 30.12)]
        self.assertEqual(sum(self._run(reqs, stocks, EuclidRouting()).values()), 10.0)

    def test_07_protection_against_inflated_demand(self):
        """Захист від завищення: потреба обмежена запасом, дефіцит розподіляється за пріоритетом"""
        got = self._run([self._req(1, 10, 0.5), self._req(2, 10000, 0.5, 50.2, 30.2)], [self._stock(10)])
        self.assertEqual(sum(got.values()), 10)
        self.assertLessEqual(abs(got[1] - got[2]), 2)                              # завищена заявка не забирає більше

    def test_08_large_queue_and_solver_failure(self):
        """Велика черга та збій розв'язувача: план не порожній; при збої ресурс пропускається з попередженням"""
        stocks, requests = _big(250)
        plan = calculate_distribution(requests, stocks, routing_service=FlatRouting(), own_solver_max_requests=10 ** 9)
        self.assertTrue(plan, 'раніше ліміт ітерацій симплексу давав порожній план')
        check_invariants(self, plan, stocks, requests)
        self.assertAlmostEqual(sum(i['amount'] for i in plan), sum(s['amount'] for s in stocks), delta=1.0)

        # Черга понад поріг: розв'язує HiGHS (власний симплекс не викликається), підсумок збігається з власним
        stocks, requests = _big(40)
        own = calculate_distribution(requests, stocks, routing_service=FlatRouting(), own_solver_max_requests=10 ** 9)
        with patch('app.optimizer.distribute.simplex_solve', side_effect=AssertionError('власний симплекс не мав викликатися')):
            highs = calculate_distribution(requests, stocks, routing_service=FlatRouting(), own_solver_max_requests=20)
        check_invariants(self, highs, stocks, requests)
        self.assertEqual(round(sum(i['amount'] for i in highs)), round(sum(i['amount'] for i in own)))

        # Збій на першому ресурсі (велика задача): він пропускається, другий ресурс розподіляється як зазвичай
        from app.optimizer import distribute as dist
        real_solver = dist.simplex_solve

        def flaky(A, b, c, sense, max_iters=500):
            return ('iteration_limit_reached', None) if A.shape[1] > 50 else real_solver(A, b, c, sense, max_iters)

        stocks, requests = _big(30)
        stocks.append({'resource_id': 2, 'warehouse_id': 99, 'amount': 10, 'lat': 50.0, 'lng': 30.0})
        requests += [{'id': 1000, 'resource_id': 2, 'amount_needed': 4, 'priority': 0.5, 'lat': 50.1, 'lng': 30.1},
                     {'id': 1001, 'resource_id': 2, 'amount_needed': 4, 'priority': 0.5, 'lat': 50.2, 'lng': 30.2}]
        warnings = []
        with patch('app.optimizer.distribute.simplex_solve', side_effect=flaky):
            plan = calculate_distribution(requests, stocks, routing_service=FlatRouting(), warnings=warnings)
        self.assertEqual(warnings, [{'resource_id': 1, 'status': 'iteration_limit_reached'}])
        self.assertTrue(plan)
        self.assertEqual({p['request_id'] for p in plan}, {1000, 1001})           # ресурс 1 не розподілено
        check_invariants(self, plan, stocks, requests)

    def test_09_invariants_and_determinism(self):
        """Інваріанти на випадкових даних: не більше запасу та потреби, детермінований результат"""
        rng = random.Random(2024)
        for _ in range(25):
            stocks, requests = random_instance(rng)
            plan = calculate_distribution(requests, stocks, routing_service=FlatRouting())
            check_invariants(self, plan, stocks, requests)
        stocks, requests = random_instance(random.Random(7))
        self.assertEqual(calculate_distribution(requests, stocks, routing_service=FlatRouting()),
                         calculate_distribution(requests, stocks, routing_service=FlatRouting()))


def _big(n):
    from app.tests.helpers import make_instance
    return make_instance(n)


class StrictDistributionTests(unittest.TestCase):
    """Жорсткий розподіл (Тріаж)"""

    def setUp(self):
        self.router = EuclidRouting()

    @staticmethod
    def _stock(wid, amount, lat=0.0, lng=0.0, res='r'):
        return {'warehouse_id': wid, 'resource_id': res, 'amount': amount, 'lat': lat, 'lng': lng}

    @staticmethod
    def _req(rid, need, prio, lat=1.0, lng=1.0, res='r'):
        return {'id': rid, 'resource_id': res, 'amount_needed': need, 'priority': prio, 'lat': lat, 'lng': lng}

    def _plan(self, requests, stocks):
        return calculate_strict_priority(requests, stocks, self.router)

    def test_01_priority_order(self):
        """Порядок за пріоритетом: вищий пріоритет обслуговується першим, решта - з залишку"""
        plan = self._plan([self._req(1, 5, 0.5), self._req(2, 5, 1.0)], [self._stock('w', 5)])
        self.assertEqual([p['request_id'] for p in plan], [2])                      # дефіцит: лише вищий пріоритет
        plan = self._plan([self._req(1, 4, 0.7), self._req(2, 4, 1.0)], [self._stock('w', 10)])
        self.assertEqual({p['request_id'] for p in plan}, {1, 2})                   # вистачає обом
        plan = self._plan([self._req(1, 10, 0.5, 1, 1), self._req(2, 6, 0.5, 1, 1)], [self._stock('w', 10)])
        self.assertEqual((plan[0]['request_id'], plan[0]['amount']), (2, 6.0))      # рівні пріоритет і відстань - менша потреба

    def test_02_distance_and_warehouses(self):
        """Вибір складів: найближчий повний склад, часткова видача з кількох, перехід до наступного складу"""
        plan = self._plan([self._req(1, 5, 0.8, 0, 0)], [self._stock('far', 20, 10, 10), self._stock('close', 20, 1, 1)])
        self.assertEqual([(p['warehouse_id'], p['amount']) for p in plan], [('close', 5.0)])
        plan = self._plan([self._req(1, 6, 0.9, 0, 0)], [self._stock('a', 3, 1, 1), self._stock('b', 5, 2, 2)])
        self.assertEqual(sum(p['amount'] for p in plan), 6.0)
        self.assertEqual(len(plan), 2)
        plan = self._plan([self._req(1, 5, 0.9, 0.1, 0.1), self._req(2, 5, 0.8, 0.1, 0.1)],
                          [self._stock('near', 5, 0, 0), self._stock('far', 5, 10, 10)])
        self.assertEqual({p['request_id']: p['warehouse_id'] for p in plan}, {1: 'near', 2: 'far'})
        plan = self._plan([self._req(601, 5, 1.0, 5, 5), self._req(602, 5, 1.0, 1, 1)], [self._stock('c', 5)])
        self.assertEqual([p['request_id'] for p in plan], [602])                    # рівний пріоритет - ближча заявка

    def test_03_minimum_quantum(self):
        """Мінімальна порція: відсів надто малих виділень, масштабування для великих потреб"""
        self.assertEqual(self._plan([self._req(1, 10, 1.0)], [self._stock('w', 1)]), [])
        plan = self._plan([self._req(701, 3, 0.7), self._req(702, 20, 1.0)], [self._stock('w', 3)])
        self.assertEqual([(p['request_id'], p['amount']) for p in plan], [(701, 3.0)])   # вищий пріоритет відсіяно
        plan = self._plan([self._req(1, 80, 0.9)], [self._stock('w', 100)])
        self.assertEqual(sum(p['amount'] for p in plan), 80.0)

    def test_04_boundary_and_multi_resource(self):
        """Граничні випадки: немає спільних ресурсів, нульовий запас, незалежність ресурсів"""
        self.assertEqual(self._plan([self._req(1, 5, 1.0, res='B')], [self._stock('w', 10, res='A')]), [])
        self.assertEqual(self._plan([self._req(1, 5, 0.9)], [self._stock('w', 0)]), [])
        plan = self._plan([self._req(1, 5, 0.9, res='A'), self._req(2, 5, 0.1, res='B')],
                          [self._stock('a', 5, res='A'), self._stock('b', 5, res='B')])
        self.assertEqual({p['request_id'] for p in plan}, {1, 2})

    def test_05_invariants_and_top_priority(self):
        """Інваріанти на випадкових даних, детермінованість, найвищий пріоритет закривається повністю"""
        rng = random.Random(99)
        for _ in range(25):
            stocks, requests = random_instance(rng)
            check_invariants(self, self._plan(requests, stocks), stocks, requests)
        stocks, requests = random_instance(random.Random(5))
        self.assertEqual(self._plan(requests, stocks), self._plan(requests, stocks))
        rng = random.Random(11)
        for _ in range(20):
            supply = rng.randint(20, 60)
            reqs = [self._req(i, rng.randint(1, supply), i / 10) for i in range(1, 6)]
            plan = self._plan(reqs, [self._stock('w', supply)])
            top = next(r for r in reqs if r['priority'] == 0.5)
            self.assertEqual(sum(p['amount'] for p in plan if p['request_id'] == top['id']), top['amount_needed'])
