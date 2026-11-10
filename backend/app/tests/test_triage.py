import time
import random
import numpy as np
from django.test import TestCase
from unittest.mock import patch
from app.optimizer.distribute import calculate_strict_priority


class DetailedStressMockDistanceService:
    """Високоточний масштабований мок-сервіс для імітації географічно розподіленої мережі"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 12.5

    def get_distance_matrix(self, sources, destinations):
        n_stk, n_req = len(sources), len(destinations)
        np.random.seed(42)
        return np.random.uniform(3.0, 45.0, size=(n_stk, n_req))


def print_table(headers, rows):
    """Допоміжна функція для виведення результатів у вигляді охайних таблиць українською"""
    col_widths = [max(len(str(item)), len(header)) for header, item in zip(headers, rows[0])] if rows else [10] * len(
        headers)
    col_widths = [max(w, len(h)) for w, h in zip(col_widths, headers)]

    header_line = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    separator = "-+-".join("-" * w for w in col_widths)

    print("\n" + header_line)
    print(separator)
    for row in rows:
        print(" | ".join(f"{str(val):<{w}}" for val, w in zip(row, col_widths)))
    print()


class DeepComprehensiveTriageStressTests(TestCase):
    """Поглиблені стрес-тести, перевірка математичної точності та табличні звіти Тріажу (Розділ 6.1.2)"""

    def setUp(self):
        print("\n" + "=" * 80)
        print("[SETUP] Ініціалізація тестового середовища Тріаж-модуля...")
        print("=" * 80)

    @patch('app.optimizer.distribute.DistanceMatrixService', DetailedStressMockDistanceService)
    def test_strict_priority_accuracy_and_adequacy(self):
        """1. Тест точності та адекватності: абсолютний пріоритет в умовах жорсткого дефіциту"""
        print("\n--- ДЕТАЛЬНИЙ ТЕСТ №1: Точність ранжування за лексикографічним критерієм ---")

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 25, 'lat': 50.0, 'lng': 30.0}
        ]
        requests = [
            {'id': 101, 'resource_id': 1, 'priority': 3.5, 'amount_needed': 25, 'lat': 50.1, 'lng': 30.1},
            {'id': 102, 'resource_id': 1, 'priority': 9.9, 'amount_needed': 25, 'lat': 50.2, 'lng': 30.2},
            {'id': 103, 'resource_id': 1, 'priority': 7.0, 'amount_needed': 25, 'lat': 50.3, 'lng': 30.3},
        ]

        input_headers = ["ID заявки", "ID ресурсу", "Пріоритет", "Потреба"]
        input_rows = [[r['id'], r['resource_id'], r['priority'], r['amount_needed']] for r in requests]
        print(" [ ВХІДНІ ПАРАМЕТРИ ЗАЯВОК ]")
        print_table(input_headers, input_rows)

        stock_headers = ["ID складу", "Доступний запас", "Широта", "Довгота"]
        stock_rows = [[s['warehouse_id'], s['amount'], s['lat'], s['lng']] for s in stocks]
        print(" [ ВХІДНІ ПАРАМЕТРИ СКЛАДУ ]")
        print_table(stock_headers, stock_rows)

        t_start = time.time()
        plan = calculate_strict_priority(requests, stocks)
        exec_time = time.time() - t_start

        output_headers = ["ID заявки", "ID складу", "Виділено од.", "Координати отримувача (Lat/Lng)"]
        output_rows = [[p['request_id'], p['warehouse_id'], p['amount'], f"{p['recipient_lat']}, {p['recipient_lng']}"]
                       for p in plan]
        print(" [ РЕЗУЛЬТАТ РОЗПОДІЛУ (ФОРМУВАННЯ ПЛАНУ) ]")
        print_table(output_headers, output_rows)

        print(f" > Деталі виконання: опрацьовано заявки за {exec_time:.6f} сек. Кількість рядків плану: {len(plan)}")

        self.assertEqual(len(plan), 1, "Аномалія: план має містити рівно один рядок за умов повного дефіциту.")
        self.assertEqual(plan[0]['request_id'], 102, "Критична помилка: ресурс віддано заявці з меншим пріоритетом!")
        self.assertEqual(plan[0]['amount'], 25.0, "Помилка обсягу: виділена кількість не дорівнює запасу складу.")
        print("[УСПІХ] Перевірка точності та адекватності ранжування пройдена на 100%.")

    @patch('app.optimizer.distribute.DistanceMatrixService', DetailedStressMockDistanceService)
    def test_split_delivery_and_quantum_limits(self):
        """2. Тест стратегії розщепленого постачання (Split Delivery) та квантування партій"""
        print("\n--- ДЕТАЛЬНИЙ ТЕСТ №2: Розщеплене постачання та квантування партій ---")

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 15, 'lat': 49.0, 'lng': 24.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 15, 'lat': 52.0, 'lng': 32.0},
        ]
        requests = [
            {'id': 201, 'resource_id': 1, 'priority': 9.0, 'amount_needed': 30, 'lat': 50.4, 'lng': 30.5}
        ]

        print(" [ ВХІДНІ СКЛАДСЬКІ ЗАПАСИ ДЛЯ SPLIT DELIVERY ]")
        print_table(["ID складу", "Доступно од.", "Локація (Lat)"],
                    [[s['warehouse_id'], s['amount'], s['lat']] for s in stocks])

        print(" [ ВХІДНА КРИТИЧНА ЗАЯВКА ]")
        print_table(["ID заявки", "Потреба", "Пріоритет"],
                    [[requests[0]['id'], requests[0]['amount_needed'], requests[0]['priority']]])

        plan = calculate_strict_priority(requests, stocks)

        total_delivered = sum(item['amount'] for item in plan)
        print(" [ ДЕТАЛЬНИЙ ПЛАН РОЗПОДІЛУ (СТРАТЕГІЯ Б) ]")
        print_table(["ID заявки", "ID складу", "Доставлено од."],
                    [[p['request_id'], p['warehouse_id'], p['amount']] for p in plan])
        print(f" > Деталі виконання: Загальний обсяг доставленого ресурсу: {total_delivered} од. з 2 складів.")

        self.assertEqual(len(plan), 2, "Має сформуватися розщеплений план з двох складів")
        self.assertEqual(total_delivered, 30.0, "Запит повинен бути задоволений повністю за рахунок конкатенації.")
        print("[УСПІХ] Стратегія Б (Split Delivery) та квантування виконані бездоганно.")

    @patch('app.optimizer.distribute.DistanceMatrixService', DetailedStressMockDistanceService)
    def test_triage_stress_performance_scaling(self):
        """3. Високонавантажений стрес-тест: 500 заявок та 20 складів"""
        print("\n--- ДЕТАЛЬНИЙ СТРЕС-ТЕСТ №3: Масштабування та швидкодія (N=500 заявок) ---")

        n_warehouses = 20
        n_requests = 500

        stocks = [
            {'resource_id': 1, 'warehouse_id': w_id, 'amount': random.randint(200, 1000), 'lat': 47.0 + w_id * 0.1,
             'lng': 28.0 + w_id * 0.1}
            for w_id in range(n_warehouses)
        ]

        requests = [
            {'id': i + 5000, 'resource_id': 1, 'priority': float(random.randint(1, 10)),
             'amount_needed': random.randint(10, 50), 'lat': 47.5, 'lng': 28.5}
            for i in range(n_requests)
        ]

        total_stock = sum(s['amount'] for s in stocks)
        total_demand = sum(r['amount_needed'] for r in requests)

        t_start = time.time()
        plan = calculate_strict_priority(requests, stocks)
        execution_time = time.time() - t_start

        perf_headers = ["Параметр метрики", "Значення / Масштаб"]
        perf_rows = [
            ["Загальна кількість складів", n_warehouses],
            ["Загальна кількість заявок (N)", n_requests],
            ["Сумарний складський запас", total_stock],
            ["Сумарний запитуваний попит", total_demand],
            ["Згенеровано записів у плані", len(plan)],
            ["Час виконання (сек)", f"{execution_time:.5f} с"]
        ]
        print(" [ ЗВЕДЕНІ РЕЗУЛЬТАТИ СТРЕС-ТЕСТУ ПРОДУКТИВНОСТІ ]")
        print_table(perf_headers, perf_rows)

        self.assertLess(execution_time, 2.0, f"Стрес-тест провалено: час виконання перевищує 2.0 с")
        self.assertGreater(len(plan), 0, "Логістичний план не повинен залишатися порожнім")
        print("[УСПІХ] Стрес-тест масштабованості та продуктивності успішно пройдено.")

    @patch('app.optimizer.distribute.DistanceMatrixService', DetailedStressMockDistanceService)
    def test_mathematical_invariants_and_constraints(self):
        """4. Перевірка математичних інваріантів у вигляді зведеної таблиці балансу"""
        print("\n--- ДЕТАЛЬНИЙ ТЕСТ №4: Перевірка захисних інваріантів і обмежень моделі ---")

        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 100, 'lat': 50.0, 'lng': 30.0},
            {'resource_id': 1, 'warehouse_id': 2, 'amount': 150, 'lat': 51.0, 'lng': 31.0},
        ]
        # Додано явне вказівлення пріоритетів заявок для тесту інваріантів
        requests = [
            {'id': 1, 'resource_id': 1, 'priority': 10.0, 'amount_needed': 80, 'lat': 50.2, 'lng': 30.2},
            {'id': 2, 'resource_id': 1, 'priority': 6.0, 'amount_needed': 120, 'lat': 50.4, 'lng': 30.4},
            {'id': 3, 'resource_id': 1, 'priority': 2.0, 'amount_needed': 100, 'lat': 50.6, 'lng': 30.6},
        ]

        initial_stocks_map = {s['warehouse_id']: s['amount'] for s in stocks}
        plan = calculate_strict_priority(requests, stocks)

        allocated_per_warehouse = {}
        allocated_per_request = {}

        for item in plan:
            w_id = item['warehouse_id']
            r_id = item['request_id']
            amt = item['amount']

            allocated_per_warehouse[w_id] = allocated_per_warehouse.get(w_id, 0) + amt
            allocated_per_request[r_id] = allocated_per_request.get(r_id, 0) + amt

        wh_rows = [[w_id, initial_stocks_map[w_id], allocated_per_warehouse.get(w_id, 0),
                    initial_stocks_map[w_id] - allocated_per_warehouse.get(w_id, 0)] for w_id in initial_stocks_map]

        print(" [ ЗВЕДЕНИЙ БАЛАНС СКЛАДСЬКИХ ЗАПАСІВ ТА ІНВАРІАНТІВ ]")
        print_table(["ID складу", "Початковий запас", "Відвантажено", "Залишок"], wh_rows)

        # Таблиця балансу заявок тепер містить також стовпець пріоритету
        req_balance_rows = [[req['id'], req['priority'], req['amount_needed'], allocated_per_request.get(req['id'], 0)]
                            for req in requests]
        print(" [ БАЛАНС ЗАДОВОЛЕННЯ ЗАЯВОК ЗА ПРІОРИТЕТАМИ ]")
        print_table(["ID заявки", "Пріоритет", "Потреба", "Отримано"], req_balance_rows)

        for w_id, used_amt in allocated_per_warehouse.items():
            max_avail = initial_stocks_map[w_id]
            self.assertLessEqual(used_amt, max_avail, f"Порушення ліміту складу #{w_id}")

        for req in requests:
            r_id = req['id']
            given = allocated_per_request.get(r_id, 0)
            needed = req['amount_needed']
            self.assertLessEqual(given, needed, f"Порушення ліміту заявки #{r_id}")

        print("[УСПІХ] Математичні інваріанти цілісності та лімітів дотримано абсолютно.")

    @patch('app.optimizer.distribute.DistanceMatrixService', DetailedStressMockDistanceService)
    def test_boundary_and_null_states(self):
        """5. Додатковий тест: перевірка граничних умов та нульових станів"""
        print("\n--- ДЕТАЛЬНИЙ ТЕСТ №5: Перевірка граничних умов та нульових станів ---")

        plan_empty_req = calculate_strict_priority([], [{'resource_id': 1, 'warehouse_id': 1, 'amount': 10, 'lat': 50,
                                                         'lng': 30}])
        plan_empty_stocks = calculate_strict_priority(
            [{'id': 1, 'resource_id': 1, 'priority': 5, 'amount_needed': 10, 'lat': 50, 'lng': 30}], [])
        plan_all_empty = calculate_strict_priority([], [])

        boundary_rows = [
            ["Порожній список заявок", "Склади > 0 / Заявки = 0", str(plan_empty_req)],
            ["Порожній список складів", "Склади = 0 / Заявки > 0", str(plan_empty_stocks)],
            ["Повністю порожні масиви", "Склади = 0 / Заявки = 0", str(plan_all_empty)]
        ]
        print(" [ РЕЗУЛЬТАТИ ПЕРЕВІРКИ ГРАНИЧНИХ УМОВ ]")
        print_table(["Тип перевірки сценарію", "Вхідні умови", "Результат функції (План)"], boundary_rows)

        self.assertEqual(plan_empty_req, [], "При порожніх заявках план має бути порожнім")
        self.assertEqual(plan_empty_stocks, [], "При порожніх складах план має бути порожнім")
        self.assertEqual(plan_all_empty, [], "При нульових вхідних даних план має бути порожнім")

        print("[УСПІХ] Перевірка граничних умов та нульових станів виконана успішно.")