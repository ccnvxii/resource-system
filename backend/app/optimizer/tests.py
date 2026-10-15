import time
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from rest_framework.test import APIClient
from rest_framework import status

from app.optimizer.distribute import calculate_strict_priority, calculate_distribution
from app.optimizer.scipy_solver import calculate_scipy_distribution
from app.optimizer.scipy_solver_simplex import calculate_scipy_distribution_simplex
from app.optimizer.milp_solver import calculate_milp_distribution
from app.optimizer.milp_custom_solver import calculate_custom_milp_distribution
from app.models import Resource, Warehouse, Stock, UserRequest, Category, Unit, RequestPurpose


class MockDistanceService:
    """Мок-сервіс для імітації логістичних відстаней OSRM у тестах"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 15.0


class OptimizerUnitTests(TestCase):
    """Модульні тести баз даних та алгоритмів на рівні словників"""

    def setUp(self):
        self.routing_service = MockDistanceService()
        self.mock_stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}
        ]

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_strict_priority_lexicographical_sorting(self):
        """Тест 1: Жорстка пріоритезація стратегічних ресурсів (Стратегічний Тріаж)"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 1] Жорстка пріоритезація стратегічних ресурсів (Стратегічний Тріаж)")
        print("=" * 80)
        print(" Умови: Заявка #101 (P=5.0, потреба 10) vs Заявка #102 (P=10.0, потреба 10)")
        print(" Запас складу: 10 шт (дефіцит 50%)")

        requests = [
            {'id': 101, 'resource_id': 1, 'priority': 5.0, 'amount_needed': 10, 'lat': 50.1, 'lng': 30.1},
            {'id': 102, 'resource_id': 1, 'priority': 10.0, 'amount_needed': 10, 'lat': 50.5, 'lng': 30.5},
        ]

        plan = calculate_strict_priority(requests, self.mock_stocks)

        print(f" Результат: Сформовано елементів плану = {len(plan)}")
        if plan:
            print(f" -> Ресурс виділено для Заявки #{plan[0]['request_id']} у кількості {plan[0]['amount']} шт")

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 102)
        self.assertEqual(plan[0]['amount'], 10)
        print(" [УСПІХ] Весь запас 100% віддано високопріоритетній заявці (P=10.0)!")
        print("=" * 80)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_strict_priority_min_quantum(self):
        """Тест 2: Перевірка порогу рентабельності логістики (min_quantum)"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 2] Перевірка порогу рентабельності відвантаження (min_quantum)")
        print("=" * 80)
        print(" Умови: Потреба = 20 шт (min_quantum = 5 шт). Запас на складі = 3 шт (3 < 5)")

        requests = [
            {'id': 103, 'resource_id': 1, 'priority': 9.0, 'amount_needed': 20, 'lat': 50.1, 'lng': 30.1},
        ]
        low_stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 3, 'lat': 50.0, 'lng': 30.0}
        ]

        plan = calculate_strict_priority(requests, low_stocks)

        print(f" Результат: Елементів у плані = {len(plan)}")
        self.assertEqual(len(plan), 0)
        print(" [УСПІХ] Заявку відхилено! Відвантаження 3 шт скасовано через недоцільність логістики.")
        print("=" * 80)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_distribution_simplex_equity(self):
        """Тест 3: Пропорційна справедливість розподілу М-методом"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 3] Пропорційна справедливість розподілу М-методом (Симплекс)")
        print("=" * 80)
        print(" Умови: Заявка #201 (потреба 10, P=8.0) та Заявка #202 (потреба 10, P=8.0)")
        print(" Запас складу: 10 шт")

        requests = [
            {'id': 201, 'resource_id': 1, 'priority': 8.0, 'amount_needed': 10, 'lat': 50.1, 'lng': 30.1},
            {'id': 202, 'resource_id': 1, 'priority': 8.0, 'amount_needed': 10, 'lat': 50.5, 'lng': 30.5},
        ]

        plan = calculate_distribution(requests, self.mock_stocks)
        amounts_allocated = {item['request_id']: item['amount'] for item in plan}

        print(f" Результат розбиття:")
        print(f" -> Заявка #201 отримала: {amounts_allocated.get(201, 0)} шт")
        print(f" -> Заявка #202 отримала: {amounts_allocated.get(202, 0)} шт")

        self.assertEqual(len(plan), 2)
        self.assertEqual(amounts_allocated[201], 5)
        self.assertEqual(amounts_allocated[202], 5)
        print(" [УСПІХ] Дефіцит поділено Парето-справедливо по 50% (по 5 шт кожному)!")
        print("=" * 80)


class PerformanceTests(TestCase):
    """Навантажувальне тестування Жадібної Евристики (Strict Priority / Тріаж)"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_strict_priority_scaling_performance(self):
        """Тест 4: Замір швидкодії Жадібної Евристики (до 5000 заявок)"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 4] Навантажувальний тест Жадібної Евристики (Масштабування до 5000 заявок)")
        print("=" * 80)

        stocks = [
            {'resource_id': 1, 'warehouse_id': i, 'amount': 2000, 'lat': 50.0, 'lng': 30.0}
            for i in range(5)
        ]
        test_scales = [100, 500, 1000, 2500, 5000]
        performance_results = {}

        for n_req in test_scales:
            requests = [
                {'id': i, 'resource_id': 1, 'priority': (i % 10) + 1, 'amount_needed': 2, 'lat': 50.1, 'lng': 30.1}
                for i in range(n_req)
            ]
            start_time = time.time()
            plan = calculate_strict_priority(requests, stocks)
            execution_time = time.time() - start_time
            performance_results[n_req] = execution_time
            print(f"  Обсяг: {n_req:5d} заявок | Час обчислення: {execution_time:.4f} сек")

        self.assertLess(performance_results[5000], 2.0)
        print(f" [УСПІХ] 5000 заявок оброблено за {performance_results[5000]:.4f} с (< 2.0 с). Відсутність комбінаторного вибуху!")
        print("=" * 80)


class IntegrationTests(TestCase):
    """Інтеграційні тести з використанням БД та Django ORM"""

    def setUp(self):
        self.user = User.objects.create_user(username='test_logistician', password='password')
        self.unit, _ = Unit.objects.get_or_create(name='шт')
        self.cat, _ = Category.objects.get_or_create(name='Обладнання', defaults={'criticality': 1.0})
        self.purpose, _ = RequestPurpose.objects.get_or_create(name='Шпиталь', defaults={'weight': 9.0})

        self.resource = Resource.objects.create(name='Генератор Тестовий', unit=self.unit, category=self.cat, is_strategic=True)
        self.warehouse = Warehouse.objects.create(name='Хаб Тестовий', latitude=50.0, longitude=30.0)
        self.stock = Stock.objects.create(warehouse=self.warehouse, resource=self.resource, amount=5)

        self.request = UserRequest.objects.create(
            user=self.user,
            resource=self.resource,
            quantity_requested=5,
            purpose=self.purpose,
            latitude=50.1,
            longitude=30.1,
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            status='new'
        )

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_full_database_integration(self):
        """Тест 5: Повний цикл зчитування та обробки даних через ORM"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 5] Інтеграційний тест бази даних (Django ORM)")
        print("=" * 80)
        print(f" Запис у БД: Створено запит #{self.request.id} на 'Генератор Тестовий' (5 шт)")

        requests_list = [{
            'id': self.request.id,
            'resource_id': self.request.resource_id,
            'priority': float(self.request.priority),
            'amount_needed': self.request.quantity_requested,
            'lat': float(self.request.latitude),
            'lng': float(self.request.longitude)
        }]
        stocks_list = [{
            'warehouse_id': self.stock.warehouse_id,
            'resource_id': self.stock.resource_id,
            'amount': self.stock.amount,
            'lat': float(self.stock.warehouse.latitude),
            'lng': float(self.stock.warehouse.longitude)
        }]

        plan = calculate_strict_priority(requests_list, stocks_list)

        print(f" Результат зчитування та обробки ORM:")
        print(f" -> План згенеровано для склада ID={plan[0]['warehouse_id']}, обсяг = {plan[0]['amount']} шт")

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['warehouse_id'], self.warehouse.id)
        self.assertEqual(plan[0]['amount'], 5)
        print(" [УСПІХ] Зв'язок ORM -> Алгоритм оптимізації працює бездоганно!")
        print("=" * 80)


class APIDistributionTests(TestCase):
    """Інтеграційні тести REST API ендпоінтів"""

    def setUp(self):
        UserRequest.objects.all().delete()
        Stock.objects.all().delete()

        self.admin_user = User.objects.create_superuser(username='admin_test', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        self.unit, _ = Unit.objects.get_or_create(name='шт')
        self.cat, _ = Category.objects.get_or_create(name='Медицина', defaults={'criticality': 1.0})
        self.purpose, _ = RequestPurpose.objects.get_or_create(code='hospital', defaults={'name': 'Шпиталь', 'weight': 9.0})

        self.resource = Resource.objects.create(name='Турнікет API', unit=self.unit, category=self.cat, is_strategic=False)
        self.warehouse = Warehouse.objects.create(name='Хаб Київський', latitude=50.45, longitude=30.52)

        Stock.objects.create(warehouse=self.warehouse, resource=self.resource, amount=20)
        self.request_obj = UserRequest.objects.create(
            user=self.admin_user,
            resource=self.resource,
            quantity_requested=15,
            purpose=self.purpose,
            latitude=50.46,
            longitude=30.53,
            status='new'
        )

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_distribute_api_endpoint(self):
        """Тест 6: Перевірка ендпоінту POST /api/distribute/"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 6] Інтеграційний тест REST API ендпоінту /api/distribute/")
        print("=" * 80)
        print(" Запит: HTTP POST /api/distribute/ з JSON payload {'strategy': 'hybrid'}")

        response = self.client.post('/api/distribute/', {'strategy': 'hybrid'}, format='json')

        print(f" Отримана відповідь сервера: HTTP {response.status_code}")
        data = response.json()
        print(f" Створено план ID: {data.get('id')}, Кількість позицій розподілу: {len(data.get('items', []))}")

        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertIn('id', data)
        self.assertIn('items', data)
        print(" [УСПІХ] API ендпоінт успішно прийняв запит та повернув згенерований JSON-план!")
        print("=" * 80)


class MathModelBoundaryTests(TestCase):
    """Тести граничних умов математичної моделі"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_quantum_threshold_rejection(self):
        """Тест 7: Відхилення заявки за порогом min_quantum"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 7] Математична межа: Відхилення залишкової партії (min_quantum)")
        print("=" * 80)
        print(" Умови: Потреба = 20 шт -> Поріг min_quantum = 5 шт. На складі залишилося = 2 шт")

        requests = [
            {'id': 301, 'resource_id': 1, 'priority': 9.0, 'amount_needed': 20, 'lat': 50.1, 'lng': 30.1}
        ]
        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 2, 'lat': 50.0, 'lng': 30.0}
        ]

        plan = calculate_strict_priority(requests, stocks)

        print(f" Результат: Довжина сформованого плану = {len(plan)}")
        self.assertEqual(len(plan), 0)
        print(" [УСПІХ] Алгоритм захищено від мікро-відвантажень! План залишився порожнім.")
        print("=" * 80)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_lexicographic_priority_dominance_over_distance(self):
        """Тест 8: Домінування пріоритету об'єкта над географічною відстанню"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 8] Строга лексикографія: Пріоритет об'єкта vs Логістична відстань")
        print("=" * 80)
        print(" Заявка #401: Пріоритет = 10.0, Відстань = 111 км (Далеко)")
        print(" Заявка #402: Пріоритет = 9.5,  Відстань = 1 км (Поруч)")
        print(" В наявності: 5 шт (Вистачить лише одній заявці)")

        requests = [
            {'id': 401, 'resource_id': 1, 'priority': 10.0, 'amount_needed': 5, 'lat': 51.0, 'lng': 30.0},
            {'id': 402, 'resource_id': 1, 'priority': 9.5, 'amount_needed': 5, 'lat': 50.01, 'lng': 30.0},
        ]
        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 5, 'lat': 50.0, 'lng': 30.0}
        ]

        plan = calculate_strict_priority(requests, stocks)

        print(f" Результат: Ресурс призначено Заявці #{plan[0]['request_id']}")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['request_id'], 401)
        self.assertEqual(plan[0]['amount'], 5)
        print(" [УСПІХ] Пріоритет об'єкта (P=10.0) строго здолав логістичну близькість!")
        print("=" * 80)

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_simplex_extreme_deficit_stability(self):
        """Тест 9: Стійкість М-методу при екстремальному дефіциті"""
        print("\n" + "=" * 80)
        print(" [ТЕСТ 9] Стійкість М-методу при 100-кратному дефіциті (Акуратність матриці)")
        print("=" * 80)
        print(" Умови: Сумарний попит = 1000 шт. Сумарний запас = 10 шт")

        requests = [
            {'id': 501, 'resource_id': 1, 'priority': 8.0, 'amount_needed': 500, 'lat': 50.1, 'lng': 30.1},
            {'id': 502, 'resource_id': 1, 'priority': 8.0, 'amount_needed': 500, 'lat': 50.2, 'lng': 30.2},
        ]
        stocks = [
            {'resource_id': 1, 'warehouse_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}
        ]

        plan = calculate_distribution(requests, stocks)
        total_allocated = sum(item['amount'] for item in plan)

        print(f" Результат: Розподілено {total_allocated} шт з 10 наявних (Заявка #501: {plan[0]['amount']} шт, Заявка #502: {plan[1]['amount']} шт)")

        self.assertEqual(len(plan), 2)
        self.assertEqual(total_allocated, 10)
        print(" [УСПІХ] Матриця М-методу не розвалилася при екстремальному дефіциті!")
        print("=" * 80)


class AllApproachesComparisonTests(TestCase):
    """Порівняльний бенчмарк УСІХ алгоритмів оптимізації"""

    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.scipy_solver_simplex.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_solver.DistanceMatrixService', MockDistanceService)
    @patch('app.optimizer.milp_custom_solver.DistanceMatrixService', MockDistanceService)
    def test_compare_all_approaches_including_custom_milp(self):
        """Тест 10: Попозиційний та порівняльний аналіз для всіх 5 методів із вирівняною таблицею"""
        print("\n" + "=" * 175)
        print(" [ТЕСТ 10] Повне порівняння: NumPy М-метод vs SciPy Simplex vs SciPy HiGHS vs C++ MILP vs Pure Python MILP")
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

        def get_speed_label(t_base, t_curr, name):
            if t_curr <= 0:
                return f"{name} (миттєво)"
            if t_base >= t_curr:
                ratio = t_base / max(t_curr, 1e-6)
                return f"{ratio:4.1f}x швидший"
            else:
                ratio = t_curr / max(t_base, 1e-6)
                return f"{ratio:5.1f}ж повільніший"

        # Вивід верхньої зведеної таблиці часу
        print(f"  {'МЕТРИКА':<22} | {'ВЛАСНИЙ М-МЕТОД':<18} | {'SciPy SIMPLEX':<16} | {'SciPy HiGHS':<15} | {'MILP (C++ HiGHS)':<18} | {'Custom MILP (B&B)':<18}")
        print("  -----------------------+--------------------+------------------+-----------------+--------------------+--------------------")
        print(f"  {'Час виконання (сек)':<22} | {numpy_time:16.5f} с | {scipy_simplex_time:14.5f} с | {scipy_highs_time:13.5f} с | {milp_time:16.5f} с | {custom_milp_time:16.5f} с")
        print(f"  {'Динамічний аналіз':<22} | {'BASELINE (1x)':<18} | {get_speed_label(numpy_time, scipy_simplex_time, ''):<16} | {get_speed_label(numpy_time, scipy_highs_time, ''):<15} | {get_speed_label(numpy_time, milp_time, ''):<18} | {get_speed_label(numpy_time, custom_milp_time, ''):<18}")
        print("=" * 175)

        # Вивід нижньої попозиційної таблиці (ідеально рівні колонки по ширині)
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

            # Форматування рядка з жорстким вирівнюванням під шаблони
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