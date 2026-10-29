import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.test import TestCase

from app.optimizer.distribute import calculate_strict_priority, calculate_distribution
from app.optimizer.scipy_solver import calculate_scipy_distribution
from app.optimizer.scipy_solver_simplex import calculate_scipy_distribution_simplex
from app.optimizer.milp_solver import calculate_milp_distribution


# --- ЕДИНА СТРУКТУРА МЕТОДІВ ДЛЯ БЕНЧМАРКІВ ---
BENCHMARK_METHODS = [
    ('NumPy М-метод',     calculate_distribution),
    ('SciPy Simplex',     calculate_scipy_distribution_simplex),
    ('SciPy HiGHS',       calculate_scipy_distribution),
    ('MILP (C++ HiGHS)',  calculate_milp_distribution),
]


class MockDistanceService:
    """Мок-сервіс для імітації логістичних відстаней OSRM у тестах"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 15.0

    def get_distance_matrix(self, sources, destinations):
        import numpy as np
        return np.full((len(sources), len(destinations)), 15.0)


def run_isolated_web_simulation(solver_func, stocks, requests):
    """Окрема глобальна функція: ізольований запуск веб-симуляції з паралельним розрахунком 80 відстаней"""
    distance_service = MockDistanceService()
    t_start = time.time()

    # 1. Етап гео-розподілу (паралельний опрос матриці відстаней для кожної пари Склад-Заявка)
    pairs = [(s['lat'], s['lng'], r['lat'], r['lng']) for s in stocks for r in requests]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda p: distance_service.get_distance(p[0], p[1], p[2], p[3]), pairs))

    t_after_geo = time.time()
    geo_time = t_after_geo - t_start

    # 2. Етап чистої математичної оптимізації
    solver_func(requests, stocks)

    t_end = time.time()
    math_time = t_end - t_after_geo
    total_time = t_end - t_start

    return total_time, geo_time, math_time


class TriageUnitTest(TestCase):
    """Окремий тестовий клас для перевірки механізму стратегічного тріажу (Strict Priority)"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_strict_priority_lexicographical_sorting(self):
        """Тест 1: Жорстка пріоритезація стратегічних ресурсів (Стратегічний Тріаж)"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 1] Жорстка пріоритезація стратегічних ресурсів (Стратегічний Тріаж)")
        print("=" * 80)

        mock_stocks = [{'resource_id': 1, 'warehouse_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 101, 'resource_id': 1, 'priority': 5.0, 'amount_needed': 10, 'lat': 50.1, 'lng': 30.1},
            {'id': 102, 'resource_id': 1, 'priority': 10.0, 'amount_needed': 10, 'lat': 50.5, 'lng': 30.5},
        ]

        plan = calculate_strict_priority(requests, mock_stocks)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 102)
        self.assertEqual(plan[0]['amount'], 10)
        print(" [УСПІХ] Весь запас 100% віддано високопріоритетній заявці (P=10.0)!")
        print("=" * 80)


class OptimizationBenchmarks(TestCase):
    """Комплексний порівняльний бенчмарк алгоритмів оптимізації та стрес-тести"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_compare_all_approaches_clean(self):
        """Тест 2: Попозиційний та порівняльний аналіз для актуальних методів із вирівняною таблицею"""
        print("\n" + "=" * 140)
        print(" [ТЕСТ 2] Повне порівняння: NumPy М-метод vs SciPy Simplex vs SciPy HiGHS vs C++ MILP")
        print("=" * 140)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 50, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 30, 'lat': 50.5, 'lng': 30.5},
        ]

        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6, 'lat': 50.1 + (i * 0.01),
             'lng': 30.1}
            for i in range(20)
        ]

        # Виконання всіх методів через загальний список
        results = {}
        for name, func in BENCHMARK_METHODS:
            t0 = time.time()
            results[name] = {
                'plan': func(requests, stocks),
                'time': time.time() - t0
            }

        def get_speed_label(t_base, t_curr):
            if t_curr <= 0:
                return "миттєво"
            if t_base >= t_curr:
                ratio = t_base / max(t_curr, 1e-6)
                return f"{ratio:4.1f}x швидший"
            else:
                ratio = t_curr / max(t_base, 1e-6)
                return f"{ratio:5.1f}x повільніший"

        numpy_time = results['NumPy М-метод']['time']

        # Вивід верхньої зведеної таблиці часу
        print(f"  {'МЕТРИКА':<22} | {'ВЛАСНИЙ М-МЕТОД':<18} | {'SciPy SIMPLEX':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18}")
        print("  -----------------------+--------------------+------------------+-----------------+--------------------")
        print(f"  {'Час виконання (сек)':<22} | {numpy_time:16.5f} с | {results['SciPy Simplex']['time']:14.5f} с | {results['SciPy HiGHS']['time']:13.5f} с | {results['MILP (C++ HiGHS)']['time']:16.5f} с")
        print(f"  {'Динамічний аналіз':<22} | {'BASELINE (1x)':<18} | {get_speed_label(numpy_time, results['SciPy Simplex']['time']):<16} | {get_speed_label(numpy_time, results['SciPy HiGHS']['time']):<15} | {get_speed_label(numpy_time, results['MILP (C++ HiGHS)']['time']):<18}")
        print("=" * 140)

        # Вивід нижньої попозиційної таблиці
        print("\n --- ПОПОЗИЦІЙНИЙ РОЗПОДІЛ ПО ОДИНИЦЯХ (СКЛАД 1 + СКЛАД 2 = ВСЬОГО / ПОТРЕБА) ---")
        print(f" {'ID':<4} | {'Пріор.':<6} | {'Потреб.':<7} | {'NumPy М-метод':<16} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18}")
        print(" " + "-" * 95)

        for req in requests:
            r_id = req['id']
            prio = req['priority']
            dem = req['amount_needed']

            def get_split(plan):
                w1 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 1)
                w2 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 2)
                return int(w1), int(w2), int(w1 + w2)

            splits = {}
            cols = {}
            for name, _ in BENCHMARK_METHODS:
                w1, w2, tot = get_split(results[name]['plan'])
                splits[name] = (w1, w2, tot)
                cols[name] = f"{w1}+{w2}={tot} ({tot / dem * 100:2.0f}%)"

            print(f" {r_id:<4} | {prio:<6.1f} | {dem:<7} | {cols['NumPy М-метод']:<16} | {cols['SciPy Simplex']:<16} | {cols['SciPy HiGHS']:<15} | {cols['MILP (C++ HiGHS)']:<18}")

        print(" " + "-" * 95)
        self.assertEqual(sum(i['amount'] for i in results['NumPy М-метод']['plan']), 80)
        self.assertEqual(sum(i['amount'] for i in results['SciPy HiGHS']['plan']), 80)
        print(" [УСПІХ] Поштучне порівняльне тестування по всіх методах виконано успішно!")
        print("=" * 140)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_time_scaling_benchmark(self):
        """Тест 3: Математичний аналіз зростання часу виконання залежно від кількості заявок (N = 10, 50, 100, 200)"""
        print("\n" + "=" * 140)
        print(" [ТЕСТ 3] МАТЕМАТИЧНИЙ АНАЛІЗ ЗРОСТАННЯ ЧАСУ: Тестування на різній кількості заявок")
        print("=" * 140)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 500, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 300, 'lat': 50.5, 'lng': 30.5},
        ]

        test_scales = [10, 50, 100, 200]
        benchmark_data = {name: [] for name, _ in BENCHMARK_METHODS}

        print(f" {'КІЛЬКІСТЬ ЗАЯВОК (N)':<20} | {'NumPy М-метод':<18} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18}")
        print(" ---------------------+--------------------+------------------+-----------------+--------------------")

        for n_req in test_scales:
            reqs_scale = [
                {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6,
                 'lat': 50.1 + (i * 0.001), 'lng': 30.1}
                for i in range(n_req)
            ]

            row_times = []
            for name, func in BENCHMARK_METHODS:
                t0 = time.time()
                func(reqs_scale, stocks)
                t_exec = time.time() - t0
                benchmark_data[name].append(t_exec)
                row_times.append(t_exec)

            print(f" N = {n_req:<17d} | {row_times[0]:14.5f} с   | {row_times[1]:12.5f} с   | {row_times[2]:11.5f} с   | {row_times[3]:14.5f} с")

        print("=" * 140)

        print("\n --- МАТЕМАТИЧНИЙ АНАЛІЗ ЗРОСТАННЯ (Коефіцієнт збільшення часу) ---")
        for method_name, times in benchmark_data.items():
            growth_factor = times[-1] / max(times[0], 1e-6)
            print(f" • {method_name:<20}: час зріс у {growth_factor:6.1f} разів.")
        print("=" * 140)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_real_web_simulation_benchmark(self):
        """Тест 4: Емуляція реального веб-запиту (4 склади, 20 заявок + ізольований паралельний розрахунок)"""
        print("\n" + "=" * 140)
        print(" [ТЕСТ 4] ЕМУЛЯЦІЯ РЕАЛЬНОГО ВЕБ-СЕРВОРУ (4 склади, 20 заявок)")
        print("=" * 140)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 150, 'lat': 50.45, 'lng': 30.52},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 120, 'lat': 49.84, 'lng': 24.02},
            {'resource_id': 1, 'warehouse_id': 3, 'amount': 100, 'lat': 46.48, 'lng': 30.73},
            {'resource_id': 1, 'warehouse_id': 4, 'amount': 80, 'lat': 49.99, 'lng': 36.23},
        ]

        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 5, 'lat': 50.0 + (i * 0.01),
             'lng': 30.0 + (i * 0.01)}
            for i in range(20)
        ]

        print(f" {'АЛГОРИТМ':<22} | {'ЗАГАЛЬНИЙ ЧАС У ВЕБІ':<22} | {'ЧАС ГЕО-СЕРВІСУ (80 пар)':<25} | {'ЧАС МАТ. ОПТИМІЗАТОРУ':<22}")
        print(" -----------------------+------------------------+---------------------------+------------------------")

        for name, func in BENCHMARK_METHODS:
            total_t, geo_t, math_t = run_isolated_web_simulation(func, stocks, requests)
            print(f" {name:<22} | {total_t:18.5f} с    | {geo_t:21.5f} с             | {math_t:18.5f} с")

        print("=" * 140)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_extreme_np_hard_scaling(self):
        """Тест 5: Екстремальний стрес-тест макромасштабу (40 складів, 400 заявок)"""
        print("\n" + "=" * 120)
        print(" [ТЕСТ 5] ЕКСТРЕМАЛЬНИЙ NP-HARD: Гібридний метод vs C++ HiGHS MILP (40 складів, 400 заявок)")
        print("=" * 120)

        stocks = [
            {'resource_id': 1, 'warehouse_id': w + 1, 'amount': 250, 'lat': 50.0 + (w * 0.01), 'lng': 30.0}
            for w in range(40)
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 10, 'lat': 50.1 + (i * 0.0005),
             'lng': 30.1}
            for i in range(400)
        ]

        print(f" Умови стрес-тесту: Складів = 40, Заявок = 400 (Змінних = {len(stocks) * len(requests)})")
        print(" Запуск обчислення...")

        t0 = time.time()
        calculate_scipy_distribution(requests, stocks)
        hybrid_time = time.time() - t0

        t0 = time.time()
        calculate_milp_distribution(requests, stocks)
        milp_time = time.time() - t0

        ratio = hybrid_time / max(milp_time, 1e-6) if hybrid_time > milp_time else milp_time / max(hybrid_time, 1e-6)
        conclusion = f"MILP швидший у {ratio:.1f} разів" if milp_time < hybrid_time else f"Гібрид швидший у {ratio:.1f} разів"

        print(f"  Час SciPy HiGHS (Гібрид LP + Жадібне округлення) : {hybrid_time:.5f} с")
        print(f"  Час C++ HiGHS MILP (Точний розв'язок)           : {milp_time:.5f} с")
        print(f"  Динамічний висновок                             : {conclusion}")
        print("=" * 120)


class DistanceMatrixServiceTableApiTest(TestCase):
    """Тести для OSRM Table API та локального кешування (вирішення проблеми N+1)"""

    def setUp(self):
        from app.services import _ROUTING_CACHE
        _ROUTING_CACHE.clear()

    @patch('app.services.requests.get')
    def test_osrm_table_api_single_request_for_matrix(self, mock_get):
        """Перевірка: OSRM Table API викликається 1 раз для матриці замість N*M запитів, результат у км"""
        from app.services import DistanceMatrixService, _ROUTING_CACHE

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [
                [10000.0, 20000.0],
                [30000.0, 40000.0]
            ]
        }

        service = DistanceMatrixService()
        stocks = [
            {'lat': 50.4501, 'lng': 30.5234},
            {'lat': 49.8402, 'lng': 24.0305}
        ]
        requests = [
            {'lat': 50.0001, 'lng': 36.2301},
            {'lat': 46.4802, 'lng': 30.7302}
        ]

        matrix = service.get_distance_matrix(stocks, requests)

        self.assertEqual(matrix.shape, (2, 2))
        self.assertAlmostEqual(matrix[0, 0], 10.0)
        self.assertAlmostEqual(matrix[0, 1], 20.0)
        self.assertAlmostEqual(matrix[1, 0], 30.0)
        self.assertAlmostEqual(matrix[1, 1], 40.0)
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_in_memory_cache_prevents_duplicate_http_calls(self, mock_get):
        """Перевірка: при наявності даних у кеші HTTP-запити не виконуються взагалі (0 запитів)"""
        from app.services import DistanceMatrixService

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [[12000.0]]
        }

        service = DistanceMatrixService()
        stocks = [{'lat': 50.450, 'lng': 30.520}]
        requests = [{'lat': 50.000, 'lng': 36.230}]

        m1 = service.get_distance_matrix(stocks, requests)
        self.assertEqual(mock_get.call_count, 1)
        self.assertAlmostEqual(m1[0, 0], 12.0)

        stocks_near = [{'lat': 50.4502, 'lng': 30.5204}]
        requests_near = [{'lat': 50.0003, 'lng': 36.2301}]
        m2 = service.get_distance_matrix(stocks_near, requests_near)
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_fallback_to_geometry_when_osrm_fails(self, mock_get):
        """Перевірка: при збої мережі спрацьовує математичний геометричний фолбек"""
        import requests as req_lib
        from app.services import DistanceMatrixService

        mock_get.side_effect = req_lib.RequestException("OSRM server unreachable")

        service = DistanceMatrixService()
        stocks = [{'lat': 50.0, 'lng': 30.0}]
        requests = [{'lat': 51.0, 'lng': 31.0}]

        matrix = service.get_distance_matrix(stocks, requests)
        expected_dist = ((73.0**2 + 111.0**2)**0.5) * 1.25
        self.assertAlmostEqual(matrix[0, 0], expected_dist, places=2)

    def test_missing_coordinates_penalty(self):
        """Перевірка: відсутність координат повертає штрафні 500 км"""
        from app.services import DistanceMatrixService

        service = DistanceMatrixService()
        stocks = [{'lat': None, 'lng': 30.0}]
        requests = [{'lat': 50.0, 'lng': None}]

        matrix = service.get_distance_matrix(stocks, requests)
        self.assertEqual(matrix[0, 0], 500.0)

    def test_build_distance_matrix_delegates_to_matrix_service(self):
        """Перевірка: build_distance_matrix делегує виконання get_distance_matrix"""
        import numpy as np
        from app.optimizer.distribute import build_distance_matrix

        class SpyRoutingService:
            called = False
            def get_distance_matrix(self, stocks, requests):
                self.called = True
                return np.full((len(stocks), len(requests)), 42.0)

        spy = SpyRoutingService()
        res = build_distance_matrix([{'lat': 1, 'lng': 2}], [{'lat': 3, 'lng': 4}], spy)
        self.assertTrue(spy.called)
        self.assertEqual(res[0, 0], 42.0)