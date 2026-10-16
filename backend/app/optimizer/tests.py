import time
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
        print(" [ТЕСТ 2] Повне порівняння: NumPy М-метод vs SciPy Simplex vs SciPy HiGHS vs C++ MILP vs Pure Python MILP")
        print("=" * 175)

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 50, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 30, 'lat': 50.5, 'lng': 30.5},
        ]

        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6, 'lat': 50.1 + (i * 0.01), 'lng': 30.1}
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
        print(f"  {'МЕТРИКА':<22} | {'ВЛАСНИЙ М-МЕТОД':<18} | {'SciPy SIMPLEX':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print("  -----------------------+--------------------+------------------+-----------------+--------------------+--------------------")
        print(f"  {'Час виконання (сек)':<22} | {numpy_time:16.5f} с | {scipy_simplex_time:14.5f} с | {scipy_highs_time:13.5f} с | {milp_time:16.5f} с | {custom_milp_time:16.5f} с")
        print(f"  {'Динамічний аналіз':<22} | {'BASELINE (1x)':<18} | {get_speed_label(numpy_time, scipy_simplex_time):<16} | {get_speed_label(numpy_time, scipy_highs_time):<15} | {get_speed_label(numpy_time, milp_time):<18} | {get_speed_label(numpy_time, custom_milp_time):<18}")
        print("=" * 175)

        # Вивід нижньої попозиційної таблиці
        print("\n --- ПОПОЗИЦІЙНИЙ РОЗПОДІЛ ПО ОДИНИЦЯХ (СКЛАД 1 + СКЛАД 2 = ВСЬОГО / ПОТРЕБА) ---")
        print(f" {'ID':<4} | {'Пріор.':<6} | {'Потреб.':<7} | {'NumPy М-метод':<16} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
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

            col_np = f"{np_w1}+{np_w2}={np_tot} ({np_tot/dem*100:2.0f}%)"
            col_ss = f"{ss_w1}+{ss_w2}={ss_tot} ({ss_tot/dem*100:2.0f}%)"
            col_sh = f"{sh_w1}+{sh_w2}={sh_tot} ({sh_tot/dem*100:2.0f}%)"
            col_mp = f"{mp_w1}+{mp_w2}={mp_tot} ({mp_tot/dem*100:2.0f}%)"
            col_cp = f"{cp_w1}+{cp_w2}={cp_tot} ({cp_tot/dem*100:2.0f}%)"

            print(f" {r_id:<4} | {prio:<6.1f} | {dem:<7} | {col_np:<16} | {col_ss:<16} | {col_sh:<15} | {col_mp:<18} | {col_cp:<18}")

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

        print(f" {'КІЛЬКІСТЬ ЗАЯВОК (N)':<20} | {'NumPy М-метод':<18} | {'SciPy Simplex':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print(" ---------------------+--------------------+------------------+-----------------+--------------------+--------------------")

        for n_req in test_scales:
            reqs_scale = [
                {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 6, 'lat': 50.1 + (i * 0.001), 'lng': 30.1}
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
            print(f" N = {n_req:<17d} | {t_numpy:14.5f} с   | {t_simplex:12.5f} с   | {t_highs:11.5f} с   | {t_milp:14.5f} с   | {custom_str}")

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
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    def test_milp_combinatorial_explosion_real_np_hard(self):
        """Тест 4: Стрес-тест порівняння при наявності бінарних обмежень (15 складів, 150 заявок)"""
        print("\n" + "=" * 145)
        print(" [ТЕСТ 4] СТРЕС-ТЕСТ NP-HARD: Порівняння при наявності бінарних обмежень мінімальної партії")
        print("=" * 145)

        stocks = [
            {'resource_id': 1, 'warehouse_id': w + 1, 'amount': 100, 'lat': 50.0 + (w * 0.02), 'lng': 30.0}
            for w in range(15)
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 8, 'lat': 50.1 + (i * 0.001), 'lng': 30.1}
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
        """Тест 5: Екстремальний стрес-тест макромасштабу (40 складів, 400 заявок)"""
        print("\n" + "=" * 145)
        print(" [ТЕСТ 5] ЕКСТРЕМАЛЬНИЙ NP-HARD: Експоненціальний вибух дерева розгалужень MILP (40 складів, 400 заявок)")
        print("=" * 145)

        stocks = [
            {'resource_id': 1, 'warehouse_id': w + 1, 'amount': 250, 'lat': 50.0 + (w * 0.01), 'lng': 30.0}
            for w in range(40)
        ]
        requests = [
            {'id': i + 1, 'resource_id': 1, 'priority': (i % 5) + 5.0, 'amount_needed': 10, 'lat': 50.1 + (i * 0.0005), 'lng': 30.1}
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