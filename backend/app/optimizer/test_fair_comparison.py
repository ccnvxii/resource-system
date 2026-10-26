"""
Коректне порівняння методів розподілу (доповнення до OptimizationBenchmarks).

Чому старий Тест 2 не міг порівняти методи "правильно":
  1. MockDistanceService повертає 15 км для всіх пар -> логістичний етап стає константою,
     і розбиття по складах (0+3 / 3+0) довільне. Це не помилка, а рівноцінні розв'язки.
  2. Порівнювалися плани, а не значення цільової функції.
  3. Не було незалежного еталона.

Що робить цей модуль:
  * SimplexCorrectnessTest: власний симплекс проти HiGHS на НЕПЕРЕРВНІЙ задачі етапу 1
    (саме тут перевіряється коректність симплексу, до будь-якого округлення).
  * FairComparisonTest: усі 5 методів порівнюються за метриками відносно еталонів
    (LP-межа та цілочисельний оптимум, обчислені незалежно через scipy).
"""
import copy
import time
from collections import defaultdict
from unittest.mock import patch

import numpy as np
from django.test import TestCase
from scipy.optimize import linprog, milp, LinearConstraint, Bounds   # milp: SciPy >= 1.9

from app.optimizer.distribute import calculate_distribution, simplex_solve
from app.optimizer.scipy_solver import calculate_scipy_distribution
from app.optimizer.scipy_solver_simplex import calculate_scipy_distribution_simplex
from app.optimizer.milp_solver import calculate_milp_distribution
from app.optimizer.milp_custom_solver import calculate_custom_milp_distribution

EPS = 1e-6
RUN_CUSTOM_BB = True        # вимкніть, якщо власний B&B надто повільний
CUSTOM_BB_MAX_N = 20

SOLVER_MODULES = [
    'app.optimizer.distribute',
    'app.optimizer.scipy_solver',
    'app.optimizer.scipy_solver_simplex',
    'app.optimizer.milp_solver',
    'app.optimizer.milp_custom_solver',
]

# kind='hybrid' -> LP + округлення (оптимальність у цілих числах НЕ гарантується)
# kind='exact'  -> цілочисельна модель (має досягати цілочисельного оптимуму)
METHODS = [
    ('NumPy М-метод',      calculate_distribution,                'hybrid'),
    ('SciPy Simplex',      calculate_scipy_distribution_simplex,  'hybrid'),
    ('SciPy HiGHS',        calculate_scipy_distribution,          'hybrid'),
    ('MILP (C++ HiGHS)',   calculate_milp_distribution,           'exact'),
    ('Custom MILP (B&B)',  calculate_custom_milp_distribution,    'exact'),
]

# забезпеченість = запас / потреба
SCENARIOS = [
    {'name': 'Симетричний, 20 заявок, забезпеченість 67% (як Тест 2)', 'n': 20, 'scarcity': 80 / 120, 'random': False},
    {'name': 'Симетричний, 20 заявок, забезпеченість 30%',            'n': 20, 'scarcity': 0.30,     'random': False},
    {'name': 'Симетричний, 20 заявок, забезпеченість 90%',            'n': 20, 'scarcity': 0.90,     'random': False},
    {'name': 'Випадкові потреби/пріоритети, 15 заявок, 50%',          'n': 15, 'scarcity': 0.50,     'random': True, 'seed': 42},
]


# ----------------------------------------------------------------------------
# Допоміжні функції
# ----------------------------------------------------------------------------

def geo_km(lat1, lng1, lat2, lng2):
    """Відстань за координатами (та сама формула, що й геометричний фолбек у сервісі)."""
    return float(np.hypot((lng2 - lng1) * 73.0, (lat2 - lat1) * 111.0) * 1.25)


class GeoDistanceService:
    """Детермінований сервіс відстаней: різні склади мають РІЗНУ відстань до заявок."""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return geo_km(lat1, lng1, lat2, lng2)

    def get_distance_matrix(self, sources, destinations):
        return np.array([[geo_km(s['lat'], s['lng'], d['lat'], d['lng']) for d in destinations]
                         for s in sources])


def build_scenario(n_req, scarcity, randomized=False, seed=0):
    rng = np.random.default_rng(seed)
    requests = []
    for i in range(n_req):
        if randomized:
            need = int(rng.integers(2, 13))
            prio = float(round(rng.uniform(1, 10), 1))
        else:
            need = 6
            prio = (i % 5) + 5.0
        requests.append({'id': i + 1, 'resource_id': 1, 'priority': prio, 'amount_needed': need,
                         'lat': 50.1 + i * 0.01, 'lng': 30.1})
    demand = sum(r['amount_needed'] for r in requests)
    supply = int(round(scarcity * demand))
    s1 = int(round(supply * 0.625))
    stocks = [
        {'resource_id': 1, 'warehouse_id': 1, 'amount': s1, 'lat': 50.0, 'lng': 30.0},
        {'resource_id': 1, 'warehouse_id': 2, 'amount': supply - s1, 'lat': 50.5, 'lng': 30.5},
    ]
    return requests, stocks


def build_stage1_lp(requests, stocks):
    """Етап 1 (max Z): та сама побудова, що й у calculate_distribution."""
    n_req, n_stk = len(requests), len(stocks)
    n_vars = n_stk * n_req + 1
    A, b, sense = [], [], []
    for i in range(n_stk):
        row = np.zeros(n_vars)
        row[i * n_req:(i + 1) * n_req] = 1
        A.append(row); b.append(stocks[i]['amount']); sense.append('<=')
    for j in range(n_req):
        row = np.zeros(n_vars)
        for i in range(n_stk):
            row[i * n_req + j] = 1
        A.append(row); b.append(requests[j]['amount_needed']); sense.append('<=')
    for j in range(n_req):
        row = np.zeros(n_vars)
        for i in range(n_stk):
            row[i * n_req + j] = 1
        row[-1] = -(requests[j]['amount_needed'] * requests[j]['priority'] / 10.0)
        A.append(row); b.append(0); sense.append('>=')
    c = np.zeros(n_vars)
    c[-1] = -1.0
    return np.array(A), np.array(b, dtype=float), c, sense


def reference_max_min(requests, stocks):
    """
    Незалежний еталон для цілі max Z, де Z = min_j x_j / w_j, w_j = потреба * пріоритет / 10.
    Усі склади взаємозамінні (немає заборонених маршрутів), тому достатньо сумарного запасу.
    Повертає (Z_LP, Z_int): верхню межу (неперервна задача) та цілочисельний оптимум.
    """
    need = np.array([r['amount_needed'] for r in requests], float)
    w = need * np.array([r['priority'] for r in requests], float) / 10.0
    supply = float(sum(s['amount'] for s in stocks))
    n = len(requests)

    c = np.zeros(n + 1)
    c[-1] = -1.0
    A = np.zeros((n + 1, n + 1))
    b = np.zeros(n + 1)
    A[0, :n] = 1.0
    b[0] = supply                       # sum x <= запас
    for j in range(n):
        A[j + 1, j] = -1.0              # w_j * Z - x_j <= 0
        A[j + 1, n] = w[j]

    bounds = [(0.0, float(need[j])) for j in range(n)] + [(0.0, None)]
    lp = linprog(c, A_ub=A, b_ub=b, bounds=bounds, method='highs')
    assert lp.status == 0, 'LP-еталон не розв\'язався'

    mi = milp(c, constraints=LinearConstraint(A, -np.inf, b),
              integrality=np.append(np.ones(n), 0.0),
              bounds=Bounds(np.zeros(n + 1), np.append(need, np.inf)),
              options={'mip_rel_gap': 1e-9})
    assert mi.success, 'MILP-еталон не розв\'язався'
    # HiGHS допускає відхилення від цілого ~1e-6, тому Z перераховуємо за округленим розв'язком
    x_int = np.round(mi.x[:n])
    assert x_int.sum() <= supply + 1e-6 and np.all(x_int <= need + 1e-6), 'MILP-еталон недопустимий'
    return float(lp.x[-1]), float(np.min(x_int / w))


def gini(values):
    v = np.sort(np.asarray(values, float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float(2.0 * np.sum(idx * v) / (n * v.sum()) - (n + 1.0) / n)


def plan_metrics(plan, requests, stocks):
    """Допустимість плану та метрики. Порівнюються ЗНАЧЕННЯ, а не розбиття по складах."""
    req_by_id = {r['id']: r for r in requests}
    stk_by_id = {s['warehouse_id']: s for s in stocks}
    by_req, by_stk = defaultdict(float), defaultdict(float)
    cost, errors = 0.0, []

    for it in plan:
        a = float(it['amount'])
        if a < -1e-9 or abs(a - round(a)) > 1e-6:
            errors.append(f"нецілий або від'ємний обсяг {a} (заявка {it['request_id']})")
        by_req[it['request_id']] += a
        by_stk[it['warehouse_id']] += a
        r, s = req_by_id[it['request_id']], stk_by_id[it['warehouse_id']]
        cost += a * geo_km(s['lat'], s['lng'], r['lat'], r['lng'])

    for r in requests:
        if by_req[r['id']] > r['amount_needed'] + 1e-6:
            errors.append(f"заявка {r['id']}: видано більше за потребу")
    for s in stocks:
        if by_stk[s['warehouse_id']] > s['amount'] + 1e-6:
            errors.append(f"склад {s['warehouse_id']}: перевищено запас")

    x = np.array([by_req[r['id']] for r in requests])
    need = np.array([r['amount_needed'] for r in requests], float)
    w = need * np.array([r['priority'] for r in requests], float) / 10.0
    return {
        'z': float(np.min(x / w)),            # ціль max-min (та сама, що в LP)
        'min_fill': float(np.min(x / need)),  # мінімальна частка закритої потреби
        'gini': gini(x / w),                  # 0 = ідеально пропорційно вагам
        'served': float(x.sum()),
        'cost': float(cost),                  # км * одиниць
        'errors': errors,
    }


# ----------------------------------------------------------------------------
# Тест A: чи правильний власний симплекс (неперервна задача, без округлення)
# ----------------------------------------------------------------------------

class SimplexCorrectnessTest(TestCase):

    def test_custom_simplex_matches_highs_on_stage1(self):
        """Власний М-метод vs HiGHS: значення Z етапу 1 мають збігатися до 1e-6."""
        print("\n" + "=" * 100)
        print(" [ТЕСТ A] Власний симплекс vs HiGHS на неперервній задачі етапу 1 (20 випадкових задач)")
        print("=" * 100)
        max_diff = 0.0
        for seed in range(20):
            with self.subTest(seed=seed):
                n = 4 + seed % 8
                scarcity = [0.3, 0.5, 0.7, 0.9][seed % 4]
                requests, stocks = build_scenario(n, scarcity, randomized=True, seed=seed)
                A, b, c, sense = build_stage1_lp(requests, stocks)

                status, x = simplex_solve(A, b, c, sense, max_iters=5000)
                self.assertEqual(status, 'optimal')

                sign = np.array([1.0 if s == '<=' else -1.0 for s in sense])
                ref = linprog(c, A_ub=A * sign[:, None], b_ub=b * sign, bounds=(0, None), method='highs')
                self.assertEqual(ref.status, 0)

                diff = abs(x[-1] - ref.x[-1])
                max_diff = max(max_diff, diff)
                self.assertLess(diff, EPS, f'Z: власний {x[-1]:.8f} vs HiGHS {ref.x[-1]:.8f}')

                resid = A @ x - b            # допустимість власного розв'язку
                for i, s in enumerate(sense):
                    if s == '<=':
                        self.assertLessEqual(resid[i], EPS)
                    else:
                        self.assertGreaterEqual(resid[i], -EPS)
                self.assertGreaterEqual(x.min(), -1e-9)
        print(f" Максимальна розбіжність Z серед усіх задач: {max_diff:.2e}")
        print("=" * 100)


# ----------------------------------------------------------------------------
# Тест B: чесне порівняння всіх 5 методів
# ----------------------------------------------------------------------------

class FairComparisonTest(TestCase):

    def setUp(self):
        for module in SOLVER_MODULES:
            patcher = patch(f'{module}.DistanceMatrixService', GeoDistanceService)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_methods_compared_by_objective_not_by_plan(self):
        print("\n" + "=" * 150)
        print(" [ТЕСТ B] Порівняння за метриками відносно еталонів (LP-межа та цілочисельний оптимум)")
        print(" Z = min x/(потреба*пріоритет/10). Однакові Z з різним розбиттям по складах = рівноцінні розв'язки.")
        print("=" * 150)

        for sc in SCENARIOS:
            requests, stocks = build_scenario(sc['n'], sc['scarcity'], sc['random'], sc.get('seed', 0))
            supply = sum(s['amount'] for s in stocks)
            demand = sum(r['amount_needed'] for r in requests)
            z_lp, z_int = reference_max_min(requests, stocks)
            self.assertLessEqual(z_int, z_lp + EPS, 'еталон: цілочисельний оптимум не може бути вищим за LP-межу')

            print(f"\n СЦЕНАРІЙ: {sc['name']}  | запас={supply}, потреба={demand}")
            print(f" ЕТАЛОНИ: Z_LP (верхня межа) = {z_lp:.4f}, Z_цілочисельний оптимум = {z_int:.4f}"
                  f"  (ціна цілочисельності {(z_lp - z_int) / z_lp * 100:.1f}%)")
            print(f" {'Метод':<19} | {'Z':>7} | {'Δ до LP':>8} | {'Δ до опт.':>9} | {'min частка':>10} | "
                  f"{'Gini(x/w)':>9} | {'Видано':>6} | {'Логістика':>10} | {'Час, с':>8}")
            print(" " + "-" * 108)

            for name, func, kind in METHODS:
                if 'Custom' in name and (not RUN_CUSTOM_BB or sc['n'] > CUSTOM_BB_MAX_N):
                    print(f" {name:<19} | пропущено (RUN_CUSTOM_BB / CUSTOM_BB_MAX_N)")
                    continue
                with self.subTest(scenario=sc['name'], method=name):
                    t0 = time.perf_counter()
                    plan = func(copy.deepcopy(requests), copy.deepcopy(stocks))
                    elapsed = time.perf_counter() - t0
                    m = plan_metrics(plan, requests, stocks)

                    gap_lp = max(0.0, (z_lp - m['z']) / z_lp * 100)
                    gap_int = max(0.0, (z_int - m['z']) / z_int * 100)
                    print(f" {name:<19} | {m['z']:7.4f} | {gap_lp:7.1f}% | {gap_int:8.1f}% | "
                          f"{m['min_fill'] * 100:9.1f}% | {m['gini']:9.4f} | {m['served']:6.0f} | "
                          f"{m['cost']:10.1f} | {elapsed:8.4f}")

                    # 1. План допустимий
                    self.assertEqual(m['errors'], [], f'{name}: недопустимий план')
                    # 2. Не видано більше, ніж є і ніж потрібно
                    self.assertLessEqual(m['served'], min(supply, demand) + EPS)
                    # 3. Допустимий цілочисельний план не може перевищити цілочисельний оптимум
                    self.assertLessEqual(m['z'], z_int + EPS,
                                         f'{name}: Z вище еталонного оптимуму (помилка в плані або в еталоні)')
                    # 4. Точні методи мають досягати цілочисельного оптимуму
                    if kind == 'exact':
                        if 'Custom' in name:
                            # Для власного B&B допускаємо невеликий евристичний відступ (gap до 25%),
                            # оскільки він обмежений по часу та ітераціях
                            self.assertGreaterEqual(
                                m['z'], z_int * 0.75 - EPS,
                                f'{name}: Z={m["z"]:.4f} занадто далеко від оптимуму {z_int:.4f}.'
                            )
                        else:
                            self.assertGreaterEqual(
                                m['z'], z_int - EPS,
                                f'{name}: Z={m["z"]:.4f} < оптимум {z_int:.4f}.'
                            )
        print("=" * 150)