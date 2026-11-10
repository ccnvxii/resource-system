import unittest
import numpy as np

from app.optimizer.distribute import (
    discretize_with_greedy_remainders,
    pivot_step,
    simplex_solve,
    calculate_distribution
)


class BaseMathematicalTestCase(unittest.TestCase):
    """Базовий тестовий клас зі стандартизованим форматуванням виводу українською."""

    def log_test_header(self, group_num, test_num, test_name, description):
        print(f"\n======================================================================")
        print(f" ГРУПА {group_num} | ТЕСТ {test_num}: {test_name}")
        print(f" ОПИС: {description}")
        print(f"----------------------------------------------------------------------")

    def log_results(self, inputs, expected, actual, status="УСПІШНО"):
        print(f" [Вхідні дані] : {inputs}")
        print(f" [Очікувано]   : {expected}")
        print(f" [Отримано]    : {actual}")
        print(f" [СТАТУС]      : {status} ")
        print(f"======================================================================")


class TestDiscretizationAlgorithm(BaseMathematicalTestCase):
    """Група 1: Тестування алгоритму цілочисельної дискретизації та фільтрації float-шуму."""

    def test_discretize_floor_and_greedy_remainders(self):
        self.log_test_header(
            1, 1,
            "test_discretize_floor_and_greedy_remainders",
            "Округлення плану та жадібний розподіл залишків за пріоритетом."
        )
        stocks = [{'amount': 5}]
        requests = [{'amount_needed': 3, 'priority': 9.0}, {'amount_needed': 3, 'priority': 5.0}]
        exact_dist = np.array([[2.4, 2.4]])

        actual = discretize_with_greedy_remainders(exact_dist, stocks, requests)
        expected = np.array([[3, 2]])

        np.testing.assert_array_equal(actual, expected)
        self.log_results("Склад: [5], Заявки: [3 (пріор. 9), 3 (пріор. 5)]", "Розподілено: [[3, 2]]",
                         f"Розподілено: {actual.tolist()}")

    def test_discretize_epsilon_tolerance(self):
        self.log_test_header(
            1, 2,
            "test_discretize_epsilon_tolerance",
            "Дискретизація: Ігнорування мікроскопічних похибок float (val < 0.001)."
        )
        stocks = [{'amount': 10}]
        requests = [{'amount_needed': 10, 'priority': 5.0}]
        exact_dist = np.array([[1e-9]])

        allocated = discretize_with_greedy_remainders(exact_dist, stocks, requests)
        expected = np.array([[0]])

        np.testing.assert_array_equal(allocated, expected)
        self.log_results(
            inputs="Точний план з шумом float: [[1e-9]]",
            expected="Розподілено: [[0]] (Фільтрація епсилон-похибки)",
            actual=f"Розподілено: {allocated.tolist()}"
        )


class TestSimplexCoreOperations(BaseMathematicalTestCase):
    """Група 2: Тестування атомарних математичних операцій Симплекс-методу."""

    def test_pivot_step_valid(self):
        self.log_test_header(
            2, 3,
            "test_pivot_step_valid",
            "Перевірка елементарного перетворення Гаусса-Жордана (Pivot Step)."
        )
        tableau = np.array([
            [2.0, 1.0, 1.0, 0.0, 10.0],
            [1.0, 2.0, 0.0, 1.0, 8.0],
            [-3.0, -2.0, 0.0, 0.0, 0.0]
        ], dtype=float)

        pivot_step(tableau, pivot_row=0, pivot_col=0)

        self.assertAlmostEqual(tableau[0, 0], 1.0)
        self.assertAlmostEqual(tableau[2, -1], 15.0)
        self.log_results("Розв'язковий рядок: 0, Стовпець: 0", "Таблиця[2,-1] = 15.0", f"Таблиця[2,-1] = {tableau[2, -1]}")

    def test_pivot_step_zero_division(self):
        self.log_test_header(
            2, 4,
            "test_pivot_step_zero_division",
            "Генерація виключення ZeroDivisionError при нульовому розв'язувальному елементі."
        )
        tableau = np.array([[0.0, 1.0, 5.0]], dtype=float)
        with self.assertRaises(ZeroDivisionError):
            pivot_step(tableau, pivot_row=0, pivot_col=0)
        self.log_results("Розв'язковий елемент = 0.0", "ZeroDivisionError", "Успішно перехоплено")


class TestSimplexSolver(BaseMathematicalTestCase):
    """Група 3: Тестування всіх станів розв'язувача задач лінійного програмування."""

    def test_simplex_solve_optimal_standard_lp(self):
        self.log_test_header(
            3, 5,
            "test_simplex_solve_optimal_standard_lp",
            "Пошук оптимуму для стандартної задачі ЛП (Максимізація)."
        )
        A = np.array([[1.0, 1.0], [1.0, -1.0]])
        b = np.array([4.0, 2.0])
        c_min = np.array([-3.0, -2.0])
        sense = ['<=', '<=']

        status, res_x = simplex_solve(A, b, c_min, sense)

        self.assertEqual(status, 'optimal')
        self.log_results("Max Z = 3*x0 + 2*x1", "Оптимум: x0=3.0, x1=1.0",
                         f"Статус: {status}, Розв'язок: x0={res_x[0]:.2f}, x1={res_x[1]:.2f}")

    def test_simplex_solve_infeasible(self):
        self.log_test_header(
            3, 6,
            "test_simplex_solve_infeasible",
            "Реакція симплекс-методу на несумісну систему обмежень (x >= 5, x <= 2)."
        )
        A = np.array([[1.0], [1.0]])
        b = np.array([5.0, 2.0])
        c_min = np.array([-1.0])
        sense = ['>=', '<=']

        status, res_x = simplex_solve(A, b, c_min, sense)

        self.assertEqual(status, 'infeasible')
        self.assertIsNone(res_x)
        self.log_results("Обмеження: x >= 5 ТА x <= 2", "Статус: infeasible, План: None",
                         f"Статус: {status}, План: {res_x}")

    def test_simplex_solve_unbounded(self):
        self.log_test_header(
            3, 7,
            "test_simplex_solve_unbounded",
            "Реакція симплекс-методу на необмежену задачу (Max Z = x0)."
        )
        A = np.array([[1.0, -1.0]])
        b = np.array([2.0])
        c_min = np.array([-1.0, 0.0])
        sense = ['<=']

        status, res_x = simplex_solve(A, b, c_min, sense)

        self.assertEqual(status, 'unbounded')
        self.assertIsNone(res_x)
        self.log_results("Максимізація Z = x0 за умови x0 - x1 <= 2", "Статус: unbounded, План: None",
                         f"Статус: {status}, План: {res_x}")

    def test_simplex_solve_iteration_limit(self):
        self.log_test_header(
            3, 8,
            "test_simplex_solve_iteration_limit",
            "Перевірка ліміту ітерацій Симплекс-методу (захист від зациклення через max_iters=1)."
        )
        A = np.array([[1.0, 1.0], [2.0, 1.0]])
        b = np.array([4.0, 5.0])
        c_min = np.array([-3.0, -2.0])
        sense = ['<=', '<=']

        status, res_x = simplex_solve(A, b, c_min, sense, max_iters=1)

        self.assertEqual(status, 'iteration_limit_reached')
        self.assertIsNone(res_x)
        self.log_results("Складна задача ЛП з max_iters=1", "Статус: iteration_limit_reached, План: None",
                         f"Статус: {status}, План: {res_x}")

    def test_simplex_solve_degeneracy(self):
        self.log_test_header(
            3, 9,
            "test_simplex_solve_degeneracy",
            "Перевірка стійкості Симплекс-методу при виродженні базису (Degeneracy / Ratio Tie)."
        )
        A = np.array([[1.0, 0.0], [0.5, 1.0]])
        b = np.array([2.0, 1.0])
        c_min = np.array([-2.0, -1.0])
        sense = ['<=', '<=']

        status, res_x = simplex_solve(A, b, c_min, sense)

        self.assertEqual(status, 'optimal')
        self.log_results("Вироджені обмеження ЛП з рівністю співвідношень", "Статус: optimal",
                         f"Статус: {status}, Розв'язок: {res_x}")


class TestMathematicalDistributionLogic(BaseMathematicalTestCase):
    """Група 4: Тестування математичних властивостей моделі справедливого розподілу (Equity LP + Stage 2)."""

    def test_calculate_distribution_equal_priority_proportionality(self):
        self.log_test_header(
            4, 10,
            "test_calculate_distribution_equal_priority_proportionality",
            "Справедливість: Рівномірний розподіл 50/50 при однакових пріоритетах у дефіциті."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertEqual(alloc_1, 5.0)
        self.assertEqual(alloc_2, 5.0)
        self.log_results("Склад: 10, Заявка 1 (пріор. 5): 10, Заявка 2 (пріор. 5): 10", "Заявка 1 = 5.0, Заявка 2 = 5.0",
                         f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}")

    def test_calculate_distribution_exact_priority_ratio(self):
        self.log_test_header(
            4, 11,
            "test_calculate_distribution_exact_priority_ratio",
            "Справедливість: Точне дотримання пропорцій вагових коефіцієнтів 9:3."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 12, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 9.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 10, 'priority': 3.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertEqual(alloc_1, 9.0)
        self.assertEqual(alloc_2, 3.0)
        self.log_results("Склад: 12, Заявка 1 (пріор. 9), Заявка 2 (пріор. 3)", "Заявка 1 = 9.0, Заявка 2 = 3.0 (Пропорція 3:1)",
                         f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}")

    def test_calculate_distribution_scarcity_equity(self):
        self.log_test_header(
            4, 12,
            "test_calculate_distribution_scarcity_equity",
            "Розподіл в умовах жорсткого дефіциту з урахуванням пріоритетів (Equity-модель)."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 10.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 10, 'priority': 2.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertGreater(alloc_1, alloc_2)
        self.log_results("Склад: 10, Заявка 1 (пріор. 10): 10, Заявка 2 (пріор. 2): 10", "Виділення_1 > Виділення_2",
                         f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}")

    def test_calculate_distribution_zero_demand_bounds(self):
        self.log_test_header(
            4, 13,
            "test_calculate_distribution_zero_demand_bounds",
            "Граничні умови: Обробка заявок з нульовою потребою або пріоритетом."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 0, 'priority': 10.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 5, 'priority': 5.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertEqual(alloc_1, 0.0)
        self.assertEqual(alloc_2, 5.0)
        self.log_results("Заявка 1 (потреба 0, пріор. 10), Заявка 2 (потреба 5, пріор. 5)", "Заявка 1 = 0.0, Заявка 2 = 5.0",
                         f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}")

    def test_calculate_distribution_stage2_logistic_minimization(self):
        self.log_test_header(
            4, 14,
            "test_calculate_distribution_stage2_logistic_minimization",
            "Тестування Етапу 2: Вибір ближчого складу за однакового рівня справедливості Z."
        )
        requests = [{'id': 1, 'resource_id': 1, 'amount_needed': 5, 'priority': 5.0, 'lat': 50.0, 'lng': 30.0}]
        stocks = [
            {'warehouse_id': 1, 'resource_id': 1, 'amount': 10, 'lat': 50.05, 'lng': 30.05},
            {'warehouse_id': 2, 'resource_id': 1, 'amount': 10, 'lat': 50.50, 'lng': 30.50}
        ]

        class MockLogisticDist:
            def get_distance(self, lat1, lng1, lat2, lng2):
                if lat1 == 50.05: return 5.0
                return 50.0

            def get_distance_matrix(self, s, r):
                return np.array([[5.0], [50.0]])

        plan = calculate_distribution(requests, stocks, routing_service=MockLogisticDist())
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['warehouse_id'], 1)
        self.log_results("2 склади (С1 на 5км, С2 на 50км), потреба 5", "ID складу = 1",
                         f"Обрано ID складу = {plan[0]['warehouse_id']}")

    def test_calculate_distribution_full_order_bonus(self):
        self.log_test_header(
            4, 15,
            "test_calculate_distribution_full_order_bonus",
            "Тестування Етапу 2: Перевага складу з 100% виконанням заявки (full_order_bonus)."
        )
        requests = [{'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.0, 'lng': 30.0}]
        stocks = [
            {'warehouse_id': 1, 'resource_id': 1, 'amount': 5, 'lat': 50.1, 'lng': 30.1},
            {'warehouse_id': 2, 'resource_id': 1, 'amount': 10, 'lat': 50.1, 'lng': 30.1}
        ]

        class EqualDistanceService:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=EqualDistanceService())
        alloc_wh2 = sum(item['amount'] for item in plan if item['warehouse_id'] == 2)
        self.assertEqual(alloc_wh2, 10.0)
        self.assertEqual(len(plan), 1)
        self.log_results("Склад 1: 5, Склад 2: 10, Потреба: 10, Відстані рівні",
                         "Повне виділення зі Складу 2 (бонус +0.01)",
                         f"Виділено {alloc_wh2} з ID складу = {plan[0]['warehouse_id']}")

    def test_absolute_surplus_handling(self):
        self.log_test_header(
            4, 16,
            "test_absolute_surplus_handling",
            "Граничні умови: Абсолютний профіцит ресурсів."
        )
        mock_stocks = [{'resource_id': 1, 'warehouse_id': 1, 'amount': 10000, 'lat': 50.0, 'lng': 30.0}]
        mock_reqs = [{'id': 1, 'resource_id': 1, 'priority': 5.0, 'amount_needed': 10, 'lat': 50.1, 'lng': 30.1}]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(mock_reqs, mock_stocks, routing_service=MockDist())
        total_given = sum(item['amount'] for item in plan)
        self.assertEqual(total_given, 10)
        self.log_results("Склад: 10000, Потреба: 10", "Загалом виділено: 10", f"Загалом виділено: {total_given}")

    def test_calculate_distribution_multi_resource_independence(self):
        self.log_test_header(
            4, 17,
            "test_calculate_distribution_multi_resource_independence",
            "Мультиресурсний батч: Незалежне розв'язання задач для двох різних ресурсів."
        )
        stocks = [
            {'warehouse_id': 1, 'resource_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0},
            {'warehouse_id': 1, 'resource_id': 2, 'amount': 5, 'lat': 50.0, 'lng': 30.0}
        ]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 8.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 2, 'amount_needed': 5, 'priority': 4.0, 'lat': 50.1, 'lng': 30.1}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        self.assertEqual(len(plan), 2)
        total_res1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        total_res2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertEqual(total_res1, 10.0)
        self.assertEqual(total_res2, 5.0)
        self.log_results("Батч з Рес 1 (10 од.) та Рес 2 (5 од.)", "Рес 1 = 10.0, Рес 2 = 5.0",
                         f"Виділено Рес 1: {total_res1}, Рес 2: {total_res2}")

    def test_calculate_distribution_complex_multi_warehouse(self):
        self.log_test_header(
            4, 18,
            "test_calculate_distribution_complex_multi_warehouse",
            "Складна розподільча мережа: 2 склади × 3 заявники з частковим дефіцитом."
        )
        stocks = [
            {'warehouse_id': 1, 'resource_id': 1, 'amount': 6, 'lat': 50.0, 'lng': 30.0},
            {'warehouse_id': 2, 'resource_id': 1, 'amount': 4, 'lat': 50.1, 'lng': 30.1}
        ]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 5, 'priority': 10.0, 'lat': 50.05, 'lng': 30.05},
            {'id': 2, 'resource_id': 1, 'amount_needed': 5, 'priority': 6.0, 'lat': 50.08, 'lng': 30.08},
            {'id': 3, 'resource_id': 1, 'amount_needed': 5, 'priority': 2.0, 'lat': 50.12, 'lng': 30.12}
        ]

        class MockDistMatrix:
            def get_distance(self, *args): return 5.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 5.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDistMatrix())
        total_allocated = sum(item['amount'] for item in plan)

        self.assertEqual(total_allocated, 10.0)
        self.log_results("2 Склади (Запас=10), 3 Заявки (Потреба=15)",
                         "Загалом виділено = 10.0 (Повне вичерпання запасів)",
                         f"Загалом виділено = {total_allocated}")

    def test_calculate_distribution_exact_zero_stock(self):
        self.log_test_header(
            4, 19,
            "test_calculate_distribution_exact_zero_stock",
            "Граничні умови: Нульові запаси на складах (Stock = 0)."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 0, 'lat': 50.0, 'lng': 30.0}]
        requests = [{'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 10.0, 'lat': 50.1, 'lng': 30.1}]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        self.assertEqual(plan, [])
        self.log_results("Склад: 0, Потреба: 10", "Порожній план []", f"План: {plan}")

    def test_calculate_distribution_tie_breaking_same_priority(self):
        self.log_test_header(
            4, 20,
            "test_calculate_distribution_tie_breaking_same_priority",
            "Справедливість: Детермінований розподіл при однакових пріоритетах і кількостях."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 4, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 5, 'priority': 5.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 5, 'priority': 5.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertEqual(alloc_1, 2.0)
        self.assertEqual(alloc_2, 2.0)
        self.log_results("Склад: 4, Заявка 1 (пріор. 5), Заявка 2 (пріор. 5)", "Виділення_1 = 2.0, Виділення_2 = 2.0",
                         f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}")

    def test_calculate_distribution_extreme_scarcity(self):
        self.log_test_header(
            4, 21,
            "test_calculate_distribution_extreme_scarcity",
            "Екстремальний дефіцит: 1 одиниця ресурсу на 3 рівноцінні заявки."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 1, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.2, 'lng': 30.2},
            {'id': 3, 'resource_id': 1, 'amount_needed': 10, 'priority': 5.0, 'lat': 50.3, 'lng': 30.3}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        total_allocated = sum(item['amount'] for item in plan)

        self.assertEqual(total_allocated, 1.0)
        self.log_results("Склад: 1, 3 Рівні заявки", "Загалом виділено = 1.0", f"Загалом виділено = {total_allocated}")

    def test_calculate_distribution_priority_vs_distance_tradeoff(self):
        self.log_test_header(
            4, 22,
            "test_calculate_distribution_priority_vs_distance_tradeoff",
            "Лексикографічний пріоритет: Перевага справедливості (Етап 1) над відстанню (Етап 2)."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 5, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 5, 'priority': 10.0, 'lat': 50.5, 'lng': 30.5},
            {'id': 2, 'resource_id': 1, 'amount_needed': 5, 'priority': 2.0, 'lat': 50.01, 'lng': 30.01}
        ]

        class TradeoffDistService:
            def get_distance(self, lat1, lng1, lat2, lng2):
                if lat2 == 50.5: return 50.0
                return 1.0

            def get_distance_matrix(self, s, r):
                return np.array([[50.0, 1.0]])

        plan = calculate_distribution(requests, stocks, routing_service=TradeoffDistService())
        alloc_1 = sum(item['amount'] for item in plan if item['request_id'] == 1)
        alloc_2 = sum(item['amount'] for item in plan if item['request_id'] == 2)

        self.assertGreater(alloc_1, alloc_2)
        self.log_results(
            inputs="Заявка 1 (Пріор. 10, Відст. 50км), Заявка 2 (Пріор. 2, Відст. 1км), Склад: 5",
            expected="Виділення Заявки 1 > Заявки 2 (Пріоритет переважає відстань)",
            actual=f"Заявка 1 отримала: {alloc_1}, Заявка 2 отримала: {alloc_2}"
        )

    def test_calculate_distribution_mixed_priority_and_demand(self):
        self.log_test_header(
            4, 23,
            "test_calculate_distribution_mixed_priority_and_demand",
            "Справедливість: Балансування при різних пріоритетах та різному обсязі попиту."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 15, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 20, 'priority': 8.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 5, 'priority': 4.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        total_allocated = sum(item['amount'] for item in plan)

        self.assertEqual(total_allocated, 15.0)
        self.log_results(
            inputs="Склад: 15, Заявка 1 (Потреба 20, Пріор. 8), Заявка 2 (Потреба 5, Пріор. 4)",
            expected="Загалом виділено = 15.0 (Повне вичерпання запасів)",
            actual=f"Загалом виділено = {total_allocated}"
        )

    def test_calculate_distribution_mild_surplus(self):
        self.log_test_header(
            4, 24,
            "test_calculate_distribution_mild_surplus",
            "Граничні умови: М'який профіцит (запас перевищує сумарний попит)."
        )
        stocks = [{'warehouse_id': 1, 'resource_id': 1, 'amount': 15, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'amount_needed': 4, 'priority': 5.0, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'amount_needed': 4, 'priority': 5.0, 'lat': 50.2, 'lng': 30.2}
        ]

        class MockDist:
            def get_distance(self, *args): return 10.0
            def get_distance_matrix(self, s, r): return np.full((len(s), len(r)), 10.0)

        plan = calculate_distribution(requests, stocks, routing_service=MockDist())
        total_allocated = sum(item['amount'] for item in plan)

        self.assertEqual(total_allocated, 8.0)
        self.log_results(
            inputs="Склад: 15, Загальна потреба: 8",
            expected="Загалом виділено = 8.0 (100% задоволення всіх заявок)",
            actual=f"Загалом виділено = {total_allocated}"
        )


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" СТАРТ ТЕСТУВАННЯ МАТЕМАТИЧНОЇ МОДЕЛІ (24 ТЕСТИ У 4 ГРУПАХ)")
    print("=" * 70)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestDiscretizationAlgorithm))
    suite.addTests(loader.loadTestsFromTestCase(TestSimplexCoreOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestSimplexSolver))
    suite.addTests(loader.loadTestsFromTestCase(TestMathematicalDistributionLogic))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(" ПІДСУМОК ТЕСТУВАННЯ:")
    print(f" Проведено тестів : {result.testsRun}")
    print(f" Успішно          : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" Помилок/Збоїв    : {len(result.failures) + len(result.errors)}")
    print("=" * 70 + "\n")