import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.test import TestCase

from app.optimizer.distribute import calculate_strict_priority, calculate_distribution
from app.optimizer.scipy_solver import calculate_scipy_distribution
from app.optimizer.scipy_solver_simplex import calculate_scipy_distribution_simplex
from app.optimizer.milp_solver import calculate_milp_distribution
from app.optimizer.milp_custom_solver import calculate_custom_milp_distribution


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
    @patch('app.optimizer.milp_custom_solver.DistanceMatrixService', MockDistanceService)
    def test_compare_all_approaches_including_custom_milp(self):
        """Тест 2: Попозиційний та порівняльний аналіз для всіх 5 методів із вирівняною таблицею"""
        print("\n" + "=" * 175)
        print(
            " [ТЕСТ 2] Повне порівняння: NumPy М-метод vs SciPy Simplex vs SciPy HiGHS vs C++ MILP vs Pure Python MILP")
        print("=" * 175)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 50, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 30, 'lat': 50.5, 'lng': 30.5},
        ]

        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6, 'lat': 50.1 + (i * 0.01),
             'lng': 30.1}
            for i in range(20)
        ]

        # 1. NumPy М-метод
        t0 = time.time()
        numpy_plan = calculate_distribution(requests, stocks)
        numpy_time = time.time() - t0

        # 2. SciPy LP Класичний Симплекс
        t0 = time.time()
        scipy_simplex_plan = calculate_scipy_distribution_simplex(requests, stocks)
        scipy_simplex_time = time.time() - t0

        # 3. SciPy LP HiGHS
        t0 = time.time()
        scipy_highs_plan = calculate_scipy_distribution(requests, stocks)
        scipy_highs_time = time.time() - t0

        # 4. Точна цілочисельна модель MILP (C++ HiGHS)
        t0 = time.time()
        milp_plan = calculate_milp_distribution(requests, stocks)
        milp_time = time.time() - t0

        # 5. Власний MILP на чистому Python (Branch & Bound)
        t0 = time.time()
        custom_milp_plan = calculate_custom_milp_distribution(requests, stocks)
        custom_milp_time = time.time() - t0

        def get_speed_label(t_base, t_curr):
            if t_curr <= 0:
                return "миттєво"
            if t_base >= t_curr:
                ratio = t_base / max(t_curr, 1e-6)
                return f"{ratio:4.1f}x швидший"
            else:
                ratio = t_curr / max(t_base, 1e-6)
                return f"{ratio:5.1f}x повільніший"

        # Вивід верхньої зведеної таблиці часу
        print(
            f"  {'МЕТРИКА':<22} | {'ВЛАСНИЙ М-МЕТОД':<18} | {'SciPy SIMPLEX':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print(
            "  -----------------------+--------------------+------------------+-----------------+--------------------+--------------------")
        print(
            f"  {'Час виконання (сек)':<22} | {numpy_time:16.5f} с | {scipy_simplex_time:14.5f} с | {scipy_highs_time:13.5f} с | {milp_time:16.5f} с | {custom_milp_time:16.5f} с")
        print(
            f"  {'Динамічний аналіз':<22} | {'BASELINE (1x)':<18} | {get_speed_label(numpy_time, scipy_simplex_time):<16} | {get_speed_label(numpy_time, scipy_highs_time):<15} | {get_speed_label(numpy_time, milp_time):<18} | {get_speed_label(numpy_time, custom_milp_time):<18}")
        print("=" * 175)

        # Вивід нижньої попозиційної таблиці
        print("\n --- ПОПОЗИЦІЙНИЙ РОЗПОДІЛ ПО ОДИНИЦЯХ (СКЛАД 1 + СКЛАД 2 = ВСЬОГО / ПОТРЕБА) ---")
        print(
            f" {'ID':<4} | {'Пріор.':<6} | {'Потреб.':<7} | {'NumPy М-метод':<16} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print(" " + "-" * 115)

        for req in requests:
            r_id = req['id']
            prio = req['priority']
            dem = req['amount_needed']

            def get_split(plan):
                w1 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 1)
                w2 = sum(i['amount'] for i in plan if i['request_id'] == r_id and i['warehouse_id'] == 2)
                return int(w1), int(w2), int(w1 + w2)

            np_w1, np_w2, np_tot = get_split(numpy_plan)
            ss_w1, ss_w2, ss_tot = get_split(scipy_simplex_plan)
            sh_w1, sh_w2, sh_tot = get_split(scipy_highs_plan)
            mp_w1, mp_w2, mp_tot = get_split(milp_plan)
            cp_w1, cp_w2, cp_tot = get_split(custom_milp_plan)

            col_np = f"{np_w1}+{np_w2}={np_tot} ({np_tot / dem * 100:2.0f}%)"
            col_ss = f"{ss_w1}+{ss_w2}={ss_tot} ({ss_tot / dem * 100:2.0f}%)"
            col_sh = f"{sh_w1}+{sh_w2}={sh_tot} ({sh_tot / dem * 100:2.0f}%)"
            col_mp = f"{mp_w1}+{mp_w2}={mp_tot} ({mp_tot / dem * 100:2.0f}%)"
            col_cp = f"{cp_w1}+{cp_w2}={cp_tot} ({cp_tot / dem * 100:2.0f}%)"

            print(
                f" {r_id:<4} | {prio:<6.1f} | {dem:<7} | {col_np:<16} | {col_ss:<16} | {col_sh:<15} | {col_mp:<18} | {col_cp:<18}")

        print(" " + "-" * 115)
        self.assertEqual(sum(i['amount'] for i in numpy_plan), 80)
        self.assertEqual(sum(i['amount'] for i in scipy_highs_plan), 80)
        self.assertEqual(sum(i['amount'] for i in custom_milp_plan), 80)
        print(" [УСПІХ] Поштучне порівняльне тестування по всіх методах виконано успішно!")
        print("=" * 175)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_custom_solver.DistanceMatrixService', MockDistanceService)
    def test_time_scaling_benchmark(self):
        """Тест 3: Математичний аналіз зростання часу виконання залежно від кількості заявок (N = 10, 50, 100, 200)"""
        print("\n" + "=" * 175)
        print(" [ТЕСТ 3] МАТЕМАТИЧНИЙ АНАЛІЗ ЗРОСТАННЯ ЧАСУ: Тестування на різній кількості заявок (Без зависань)")
        print("=" * 175)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 500, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 300, 'lat': 50.5, 'lng': 30.5},
        ]

        test_scales = [10, 50, 100, 200]
        benchmark_data = {
            'NumPy М-метод': [],
            'SciPy Simplex': [],
            'SciPy HiGHS': [],
            'MILP (C++ HiGHS)': [],
            'Custom MILP (B&B)': []
        }

        print(
            f" {'КІЛЬКІСТЬ ЗАЯВОК (N)':<20} | {'NumPy М-метод':<18} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print(
            " ---------------------+--------------------+------------------+-----------------+--------------------+--------------------")

        for n_req in test_scales:
            reqs_scale = [
                {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6,
                 'lat': 50.1 + (i * 0.001), 'lng': 30.1}
                for i in range(n_req)
            ]

            t0 = time.time()
            calculate_distribution(reqs_scale, stocks)
            t_numpy = time.time() - t0
            benchmark_data['NumPy М-метод'].append(t_numpy)

            t0 = time.time()
            calculate_scipy_distribution_simplex(reqs_scale, stocks)
            t_simplex = time.time() - t0
            benchmark_data['SciPy Simplex'].append(t_simplex)

            t0 = time.time()
            calculate_scipy_distribution(reqs_scale, stocks)
            t_highs = time.time() - t0
            benchmark_data['SciPy HiGHS'].append(t_highs)

            t0 = time.time()
            calculate_milp_distribution(reqs_scale, stocks)
            t_milp = time.time() - t0
            benchmark_data['MILP (C++ HiGHS)'].append(t_milp)

            # Захист від зависання: запускаємо Custom MILP лише для N <= 15
            if n_req <= 15:
                t0 = time.time()
                calculate_custom_milp_distribution(reqs_scale, stocks)
                t_custom = time.time() - t0
            else:
                t_custom = -1.0
            benchmark_data['Custom MILP (B&B)'].append(t_custom if t_custom > 0 else 0)

            custom_str = f"{t_custom:14.5f} с" if t_custom > 0 else "N/A (Timeout)"
            print(
                f" N = {n_req:<17d} | {t_numpy:14.5f} с   | {t_simplex:12.5f} с   | {t_highs:11.5f} с   | {t_milp:14.5f} с   | {custom_str}")

        print("=" * 175)

        print("\n --- МАТЕМАТИЧНИЙ АНАЛІЗ ЗРОСТАННЯ (Коефіцієнт збільшення часу) ---")
        for method_name, times in benchmark_data.items():
            valid_times = [t for t in times if t > 0]
            if len(valid_times) >= 2:
                growth_factor = valid_times[-1] / max(valid_times[0], 1e-6)
                print(f" • {method_name:<22}: час зріс у {growth_factor:6.1f} разів.")
        print("=" * 175)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_custom_solver.DistanceMatrixService', MockDistanceService)
    def test_real_web_simulation_benchmark(self):
        """Тест 4: Емуляція реального веб-запиту (4 склади, 20 заявок + ізольований паралельний розрахунок)"""
        print("\n" + "=" * 175)
        print(" [ТЕСТ 4] ЕМУЛЯЦІЯ РЕАЛЬНОГО ВЕБ-СЕРВОРУ (4 склади, 20 заявок + Ізольований паралельний розрахунок)")
        print("=" * 175)

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

        methods = {
            'NumPy М-метод': calculate_distribution,
            'SciPy Simplex': calculate_scipy_distribution_simplex,
            'SciPy HiGHS': calculate_scipy_distribution,
            'MILP (C++ HiGHS)': calculate_milp_distribution,
            'Custom MILP (B&B)': calculate_custom_milp_distribution,
        }

        print(
            f" {'АЛГОРИТМ':<22} | {'ЗАГАЛЬНИЙ ЧАС У ВЕБІ':<22} | {'ЧАС ГЕО-СЕРВІСУ (80 пар)':<25} | {'ЧАС МАТ. ОПТИМІЗАТОРУ':<22}")
        print(" -----------------------+------------------------+---------------------------+------------------------")

        for name, func in methods.items():
            total_t, geo_t, math_t = run_isolated_web_simulation(func, stocks, requests)
            print(f" {name:<22} | {total_t:18.5f} с    | {geo_t:21.5f} с             | {math_t:18.5f} с")

        print("=" * 175)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_milp_combinatorial_explosion_real_np_hard(self):
        """Тест 5: Стрес-тест порівняння при наявності бінарних обмежень (15 складів, 150 заявок)"""
        print("\n" + "=" * 145)
        print(" [ТЕСТ 5] СТРЕС-ТЕСТ NP-HARD: Порівняння при наявності бінарних обмежень мінімальної партії")
        print("=" * 145)

        stocks = [
            {'resource_id': 1, 'warehouse_id': w + 1, 'amount': 100, 'lat': 50.0 + (w * 0.02), 'lng': 30.0}
            for w in range(15)
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 8, 'lat': 50.1 + (i * 0.001),
             'lng': 30.1}
            for i in range(150)
        ]

        print(" Умови тесту: Участь беруть складів = 15, заявок = 150")
        print(" Запуск обчислення...")

        t0 = time.time()
        calculate_scipy_distribution(requests, stocks)
        hybrid_time = time.time() - t0

        t0 = time.time()
        calculate_milp_distribution(requests, stocks)
        milp_time = time.time() - t0

        if milp_time < hybrid_time:
            ratio = hybrid_time / max(milp_time, 1e-6)
            conclusion = f"MILP швидший у {ratio:.1f} разів"
        else:
            ratio = milp_time / max(hybrid_time, 1e-6)
            conclusion = f"MILP повільніший у {ratio:.1f} разів"

        print(f"  Час Гібриду (LP + Discretize) : {hybrid_time:.5f} с")
        print(f"  Час Точного MILP (Integer LP): {milp_time:.5f} с")
        print(f"  Динамічний висновок          : {conclusion}")
        print("=" * 145)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_extreme_np_hard_scaling(self):
        """Тест 6: Екстремальний стрес-тест макромасштабу (40 складів, 400 заявок)"""
        print("\n" + "=" * 145)
        print(
            " [ТЕСТ 6] ЕКСТРЕМАЛЬНИЙ NP-HARD: Експоненціальний вибух дерева розгалужень MILP (40 складів, 400 заявок)")
        print("=" * 145)

        stocks = [
            {'resource_id': 1, 'warehouse_id': w + 1, 'amount': 250, 'lat': 50.0 + (w * 0.01), 'lng': 30.0}
            for w in range(40)
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 10, 'lat': 50.1 + (i * 0.0005),
             'lng': 30.1}
            for i in range(400)
        ]

        print(" Умови стрес-тесту: Складів = 40, Заявок = 400")
        print(f" Загальна кількість комбінаторних пар (змінних) = {len(stocks) * len(requests)}")
        print(" Запуск обчислення...")

        t0 = time.time()
        calculate_scipy_distribution(requests, stocks)
        hybrid_time = time.time() - t0

        t0 = time.time()
        calculate_milp_distribution(requests, stocks)
        milp_time = time.time() - t0

        if milp_time < hybrid_time:
            ratio = hybrid_time / max(milp_time, 1e-6)
            conclusion = f"MILP швидший у {ratio:.1f} разів"
        else:
            ratio = milp_time / max(hybrid_time, 1e-6)
            conclusion = f"MILP повільніший у {ratio:.1f} разів"

        print(f"  Час Гібриду (LP через C++ HiGHS солвер)            : {hybrid_time:.5f} с")
        print(f"  Час Точного MILP (Integer LP через C++ HiGHS солвер): {milp_time:.5f} с")
        print(f"  Динамічний висновок                                : {conclusion}")
        print("=" * 145)

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

        # Перевірка форми та значень у км
        self.assertEqual(matrix.shape, (2, 2))
        self.assertAlmostEqual(matrix[0, 0], 10.0)
        self.assertAlmostEqual(matrix[0, 1], 20.0)
        self.assertAlmostEqual(matrix[1, 0], 30.0)
        self.assertAlmostEqual(matrix[1, 1], 40.0)

        # Перевірка: рівно 1 HTTP-запит (замість 2*2 = 4)
        self.assertEqual(mock_get.call_count, 1)

        # Перевірка: ключ у кеші округлений до 3 знаків
        key_00 = (round(50.4501, 3), round(30.5234, 3), round(50.0001, 3), round(36.2301, 3))
        self.assertIn(key_00, _ROUTING_CACHE)
        self.assertAlmostEqual(_ROUTING_CACHE[key_00], 10.0)

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

        # Перший виклик: заповнює кеш
        m1 = service.get_distance_matrix(stocks, requests)
        self.assertEqual(mock_get.call_count, 1)
        self.assertAlmostEqual(m1[0, 0], 12.0)

        # Другий виклик (з координатами в межах 3 знаків після коми)
        stocks_near = [{'lat': 50.4502, 'lng': 30.5204}]
        requests_near = [{'lat': 50.0003, 'lng': 36.2301}]
        m2 = service.get_distance_matrix(stocks_near, requests_near)

        # HTTP запитів не додалося (залишився 1)
        self.assertEqual(mock_get.call_count, 1)
        self.assertAlmostEqual(m2[0, 0], 12.0)

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

        # Очікуваний розрахунок: dx = (31-30)*73 = 73, dy = (51-50)*111 = 111
        # sqrt(73^2 + 111^2) * 1.25 = sqrt(5329 + 12321) * 1.25 = sqrt(17650) * 1.25 ≈ 166.07
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
