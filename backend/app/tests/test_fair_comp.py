import time
from unittest.mock import patch
from django.test import TestCase
import numpy as np

from app.optimizer.distribute import calculate_distribution
from app.optimizer.scipy_solver import calculate_scipy_distribution

BENCHMARK_METHODS = [
    ('Власний NumPy М-метод (Ваш)', calculate_distribution),
    ('Еталонний SciPy HiGHS', calculate_scipy_distribution),
]


class MockDistanceService:
    """Мок-сервіс для стабільних логістичних відстаней у бенчмарках"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 15.0

    def get_distance_matrix(self, sources, destinations):
        return np.full((len(sources), len(destinations)), 15.0)


class FairModelComparisonBenchmark(TestCase):
    """
    Порівняльний бенчмарк власної реалізації моделі справедливого розподілу (Equity LP)
    з еталоном (SciPy HiGHS) для аналізу в дипломній роботі.
    """

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    def test_compare_equity_model_with_benchmark(self):
        """Порівняльний бенчмарк: Час виконання, попозиційний розподіл та транспортні витрати"""
        print("\n" + "=" * 110)
        print(" [БЕНЧМАРК] Порівняння власної матмоделі справедливого розподілу з еталоном (SciPy HiGHS)")
        print("=" * 110)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 50, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 30, 'lat': 50.5, 'lng': 30.5},
        ]

        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6,
             'lat': 50.1 + (i * 0.01), 'lng': 30.1}
            for i in range(20)
        ]

        # Виконання методів
        results = {}
        for name, func in BENCHMARK_METHODS:
            t0 = time.time()
            plan = func(requests, stocks)
            exec_time = time.time() - t0
            total_allocated = sum(item['amount'] for item in plan)
            results[name] = {'plan': plan, 'time': exec_time, 'allocated': total_allocated}

        my_time = results['Власний NumPy М-метод (Ваш)']['time']
        scipy_time = results['Еталонний SciPy HiGHS']['time']

        # Функція для розрахунку сумарного транспортного плеча (відстань * обсяг)
        def calculate_transport_cost(plan):
            total_cost = 0.0
            for item in plan:
                # Використовуємо відстань з мок-сервісу (в середньому 15 км для пари)
                dist = 15.0 if item['warehouse_id'] == 1 else 18.0
                total_cost += item['amount'] * dist
            return total_cost

        my_cost = calculate_transport_cost(results['Власний NumPy М-метод (Ваш)']['plan'])
        scipy_cost = calculate_transport_cost(results['Еталонний SciPy HiGHS']['plan'])

        # Зведена таблиця продуктивності
        print(f" {'МЕТРИКА':<32} | {'ВЛАСНИЙ М-МЕТОД (ВАШ)':<26} | {'ЕТАЛОН SciPy HiGHS':<20}")
        print(" " + "-" * 32 + "+" + "-" * 28 + "+" + "-" * 22)
        print(f" {'Час виконання (сек)':<32} | {my_time:20.5f} с        | {scipy_time:17.5f} с")
        print(
            f" {'Загалом задоволено попиту':<32} | {results['Власний NumPy М-метод (Ваш)']['allocated']:20.1f} од.      | {results['Еталонний SciPy HiGHS']['allocated']:17.1f} од.")
        print(f" {'Сумарне транспортне плечо (од·км)':<32} | {my_cost:20.1f} км     | {scipy_cost:17.1f} км")
        print("=" * 110)

        # Попозиційний аналіз
        print("\n --- ПОПОЗИЦІЙНИЙ РОЗПОДІЛ ПО ОДИНИЦЯХ (ПОТРЕБА = 6 од. на заявку загалом 120) ---")
        print(f" {'ID':<4} | {'Пріор.':<6} | {'Власний метод (Склад 1+2)':<26} | {'SciPy HiGHS (Склад 1+2)':<25}")
        print(" " + "-" * 70)

        for req in requests:
            r_id = req['id']
            prio = req['priority']

            def get_split(plan):
                w1 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 1)
                w2 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 2)
                return int(w1), int(w2), int(w1 + w2)

            my_w1, my_w2, my_tot = get_split(results['Власний NumPy М-метод (Ваш)']['plan'])
            sci_w1, sci_w2, sci_tot = get_split(results['Еталонний SciPy HiGHS']['plan'])

            my_str = f"{my_w1}+{my_w2}={my_tot} ({my_tot / 6 * 100:2.0f}%)"
            sci_str = f"{sci_w1}+{sci_w2}={sci_tot} ({sci_tot / 6 * 100:2.0f}%)"

            print(f" {r_id:<4} | {prio:<6.1f} | {my_str:<26} | {sci_str:<25}")

        print(" " + "-" * 70)

        # Аналіз пріоритетів
        def get_prio_fulfillment(plan, target_prio):
            allocs = [
                sum(i['amount'] for i in plan if i['request_id'] == req['id'])
                for req in requests if req['priority'] == target_prio
            ]
            return (sum(allocs) / (len(allocs) * 6)) * 100

        my_prio9 = get_prio_fulfillment(results['Власний NumPy М-метод (Ваш)']['plan'], 9.0)
        sci_prio9 = get_prio_fulfillment(results['Еталонний SciPy HiGHS']['plan'], 9.0)

        my_prio5 = get_prio_fulfillment(results['Власний NumPy М-метод (Ваш)']['plan'], 5.0)
        sci_prio5 = get_prio_fulfillment(results['Еталонний SciPy HiGHS']['plan'], 5.0)

        print(f"\n [АНАЛІЗ ЯКОСТІ РОЗПОДІЛУ ЗА ПРІОРИТЕТАМИ]")
        print(f" • Забезпечення топ-пріоритету (P=9.0): Власний = {my_prio9:.1f}% | SciPy = {sci_prio9:.1f}%")
        print(f" • Забезпечення низького пріоритету (P=5.0): Власний = {my_prio5:.1f}% | SciPy = {sci_prio5:.1f}%")
        print("=" * 110)

        # Перевірки Assert
        self.assertEqual(results['Власний NumPy М-метод (Ваш)']['allocated'], 80)
        self.assertEqual(results['Еталонний SciPy HiGHS']['allocated'], 80)
        self.assertEqual(my_prio9, 100.0)
        print(" [УСПІХ] Розширений бенчмарк з транспортними витратами завершено успішно!")
        print("=" * 110)