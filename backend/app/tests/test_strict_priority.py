import unittest
import numpy as np

# Припускаємо, що функції імпортовані з вашого модуля
from app.optimizer.distribute import calculate_strict_priority

class DummyRoutingService:
    """Фіктивний сервіс маршрутизації для детермінованих тестів відстаней."""
    def get_distance(self, lat1, lng1, lat2, lng2):
        if lat1 is None or lat2 is None:
            return 10.0
        return float(np.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2))


class TestCalculateStrictPriority(unittest.TestCase):
    """Набір юнит-тестів для перевірки алгоритму жорсткого розподілу (Triage)."""

    def setUp(self):
        self.routing_service = DummyRoutingService()

    def log_test_header(self, test_name, description):
        print(f"\n======================================================================")
        print(f" ЖОРСТКИЙ РОЗПОДІЛ (TRIAGE) | ТЕСТ: {test_name}")
        print(f" ОПИС: {description}")
        print(f"----------------------------------------------------------------------")

    def log_results(self, inputs, expected, actual, status="УСПІШНО"):
        print(f" [Вхідні дані] : {inputs}")
        print(f" [Очікувано]   : {expected}")
        print(f" [Отримано]    : {actual}")
        print(f" [СТАТУС]      : {status} ")
        print(f"======================================================================")

    def test_basic_full_allocation_by_priority(self):
        desc = "Перевірка базового розподілу: пріоритет 10 обробляється раніше за пріоритет 5 в умовах дефіциту."
        self.log_test_header("test_basic_full_allocation_by_priority", desc)

        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 5, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            {'id': 101, 'resource_id': 'res_1', 'priority': 5, 'amount_needed': 5, 'lat': 1.0, 'lng': 1.0},
            {'id': 102, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 5, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 102)
        self.assertEqual(plan[0]['amount'], 5.0)
        self.assertEqual(plan[0]['warehouse_id'], 'wh_1')

        self.log_results(
            inputs="Склад: 1 шт. (запас 5), Заявки: №101 (пріор. 5, потреба 5), №102 (пріор. 10, потреба 5)",
            expected="План містить 1 елемент для заявки №102 з обсягом 5.0",
            actual=f"План містить {len(plan)} елемент(и), обрано заявку №{plan[0]['request_id']} з обсягом {plan[0]['amount']}"
        )

    def test_distance_based_selection_for_full_candidates(self):
        desc = "Перевірка вибору найближчого складу, коли декілька складів мають достатньо ресурсу."
        self.log_test_header("test_distance_based_selection_for_full_candidates", desc)

        stocks = [
            {'warehouse_id': 'wh_far', 'resource_id': 'res_1', 'amount': 20, 'lat': 10.0, 'lng': 10.0},
            {'warehouse_id': 'wh_close', 'resource_id': 'res_1', 'amount': 20, 'lat': 1.0, 'lng': 1.0},
        ]
        requests = [
            {'id': 201, 'resource_id': 'res_1', 'priority': 8, 'amount_needed': 5, 'lat': 0.0, 'lng': 0.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['warehouse_id'], 'wh_close')
        self.assertEqual(plan[0]['amount'], 5.0)

        self.log_results(
            inputs="Склади: wh_far (10.0, 10.0), wh_close (1.0, 1.0). Заявка №201 (потреба 5)",
            expected="Виділення зі складу wh_close (як найближчого)",
            actual=f"Виділено зі складу {plan[0]['warehouse_id']} обсягом {plan[0]['amount']}"
        )

    def test_partial_allocation_across_warehouses(self):
        desc = "Перевірка розподілу з кількох складів, якщо на одному складі недостатньо ресурсу."
        self.log_test_header("test_partial_allocation_across_warehouses", desc)

        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 3, 'lat': 1.0, 'lng': 1.0},
            {'warehouse_id': 'wh_2', 'resource_id': 'res_1', 'amount': 5, 'lat': 2.0, 'lng': 2.0},
        ]
        requests = [
            {'id': 301, 'resource_id': 'res_1', 'priority': 9, 'amount_needed': 6, 'lat': 0.0, 'lng': 0.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        total_allocated = sum(item['amount'] for item in plan)
        self.assertEqual(total_allocated, 6.0)
        self.assertEqual(len(plan), 2)

        warehouses_used = [item['warehouse_id'] for item in plan]
        self.log_results(
            inputs="Склади: wh_1 (3 од.), wh_2 (5 од.). Заявка №301 (потреба 6 од.)",
            expected="Загальний обсяг виділення = 6.0 з кількох складів",
            actual=f"Загальний обсяг = {total_allocated}, задіяні склади: {warehouses_used}"
        )

    def test_min_quantum_threshold_rejection(self):
        desc = "Перевірка відсіювання заявки, якщо загальний доступний запас менший за min_quantum."
        self.log_test_header("test_min_quantum_threshold_rejection", desc)

        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 1, 'lat': 1.0, 'lng': 1.0},
        ]
        requests = [
            {'id': 401, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 10, 'lat': 0.0, 'lng': 0.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)
        self.assertEqual(len(plan), 0)

        self.log_results(
            inputs="Склад: wh_1 (запас 1). Заявка №401 (потреба 10, min_quantum > 1)",
            expected="План порожній ([]), оскільки запас менший за мінімальний квант",
            actual=f"Отримано план: {plan}"
        )

    def test_no_common_resources(self):
        desc = "Перевірка поведінки, коли ресурси в заявках і на складах не збігаються."
        self.log_test_header("test_no_common_resources", desc)

        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_A', 'amount': 10, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            {'id': 501, 'resource_id': 'res_B', 'priority': 10, 'amount_needed': 5, 'lat': 0.0, 'lng': 0.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)
        self.assertEqual(plan, [])

        self.log_results(
            inputs="Склад має ресурс 'res_A', заявка запитує 'res_B'",
            expected="План порожній ([]), відсутній спільний ресурс",
            actual=f"Отримано план: {plan}"
        )

    def test_same_priority_distance_tie_breaker(self):
        """Перевірка сортування за відстанню при однакових пріоритетах (однаковий пріоритет 10)."""
        stocks = [
            {'warehouse_id': 'wh_center', 'resource_id': 'res_1', 'amount': 5, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            # Заявка 601 далі від складу (координати 5,5)
            {'id': 601, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 5, 'lat': 5.0, 'lng': 5.0},
            # Заявка 602 ближче до складу (координати 1,1)
            {'id': 602, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 5, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 602)  # Ближча заявка має отримати ресурс першою
        self.log_results(
            inputs=" jednakoviy пріор. 10. Заявка №601 (далі), Заявка №602 (ближче). Запас: 5",
            expected="Виділення ресурсу ближчій заявці №602",
            actual=f"Ресурс виділено заявці №{plan[0]['request_id']}"
        )

    def test_priority_fall_down_when_high_priority_rejected_by_quantum(self):
        """Перевірка переходу циклу до нижчих пріоритетів, коли вищий пріоритет відсіяно через min_quantum."""
        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 3, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            # Пріоритет 7 (нижчий), потреба 3 (min_quantum = 1)
            {'id': 701, 'resource_id': 'res_1', 'priority': 7, 'amount_needed': 3, 'lat': 1.0, 'lng': 1.0},
            # Пріоритет 10 (вищий), але потреба 20 (min_quantum = 5 > запасу 3 -> відсів)
            {'id': 702, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 20, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 701)
        self.assertEqual(plan[0]['amount'], 3.0)
        self.log_results(
            inputs="Запас: 3. Пріор. 10 (потреба 20, квант 5 -> відсів), Пріор. 7 (потреба 3, квант 1)",
            expected="Заявка №702 відсіяна через min_quantum, ресурс перейшов до заявки №701",
            actual=f"Ресурс виділено заявці №{plan[0]['request_id']} обсягом {plan[0]['amount']}"
        )

    def test_large_demand_quantum_scaling(self):
        """Перевірка розрахунку мін. кванту для великих партій (demand > 50)."""
        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 100, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            {'id': 801, 'resource_id': 'res_1', 'priority': 9, 'amount_needed': 80, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)
        total_allocated = sum(item['amount'] for item in plan)

        self.assertEqual(total_allocated, 80.0)
        self.log_results(
            inputs="Великий обсяг замовлення: demand = 80, запас = 100",
            expected="Успішне виділення 80.0 з урахуванням квантування для великих партій",
            actual=f"Виділено загалом: {total_allocated}"
        )

    def test_priority_fall_down_to_lower_levels(self):
        """Перевірка переходу циклу до нижчих пріоритетів, коли вищий пріоритет повністю вичерпує запас."""
        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 5, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            # Пріоритет 7 (нижчий), запитує 5
            {'id': 701, 'resource_id': 'res_1', 'priority': 7, 'amount_needed': 5, 'lat': 1.0, 'lng': 1.0},
            # Пріоритет 10 (вищий), запитує 5 (повністю забирає склад 5)
            {'id': 702, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 5, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        # Оскільки заявка 702 має вищий пріоритет (10), вона забирає всі 5 одиниць.
        # Заявка 701 (пріоритет 7) залишається без ресурсу, бо склад спорожнів.
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 702)
        self.log_results(
            inputs="Пріор. 10 (потреба 5), Пріор. 7 (потреба 5). Запас: 5",
            expected="Високий пріоритет 10 забирає весь запас, пріоритет 7 отримує 0",
            actual=f"Ресурс виділено заявці №{plan[0]['request_id']} (пріор. 10)"
        )

    def test_priority_fall_down_and_satisfy_both(self):
        """Перевірка переходу циклу до нижчого пріоритету, коли запасів достатньо для кількох рівнів."""
        stocks = [
            {'warehouse_id': 'wh_1', 'resource_id': 'res_1', 'amount': 10, 'lat': 0.0, 'lng': 0.0}
        ]
        requests = [
            # Пріоритет 7, потреба 4
            {'id': 703, 'resource_id': 'res_1', 'priority': 7, 'amount_needed': 4, 'lat': 1.0, 'lng': 1.0},
            # Пріоритет 10, потреба 4
            {'id': 704, 'resource_id': 'res_1', 'priority': 10, 'amount_needed': 4, 'lat': 1.0, 'lng': 1.0},
        ]

        plan = calculate_strict_priority(requests, stocks, self.routing_service)

        # Очікуємо, що задовольняться обидві заявки (спочатку 704, потім цикл опуститься до 7 і задовольнить 703)
        self.assertEqual(len(plan), 2)
        satisfied_ids = {item['request_id'] for item in plan}
        self.assertEqual(satisfied_ids, {703, 704})

        self.log_results(
            inputs="Запас: 10. Заявки: №704 (пріор. 10, потр. 4), №703 (пріор. 7, потр. 4)",
            expected="Ресурс послідовно виділено обом заявкам (цикл опустився до пріор. 7)",
            actual=f"Успішно задоволено заявки з ID: {list(satisfied_ids)}"
        )


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" СТАРТ ТЕСТУВАННЯ ЖОРСТКОГО РОЗПОДІЛУ (TRIAGE)")
    print("=" * 70)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateStrictPriority))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(" ПІДСУМОК ТЕСТУВАННЯ TRIAGE:")
    print(f" Проведено тестів : {result.testsRun}")
    print(f" Успішно          : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" Помилок/Збоїв    : {len(result.failures) + len(result.errors)}")
    print("=" * 70 + "\n")