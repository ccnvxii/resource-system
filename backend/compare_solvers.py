# -*- coding: utf-8 -*-
"""
Порівняння власного симплекс-методу з еталонним розв'язувачем HiGHS (scipy.optimize.linprog)
на одній і тій самій моделі справедливого розподілу.

Запуск:  docker compose exec backend python compare_solvers.py [розміри черг через пробіл]
Один ресурс, 4 склади, евклідові відстані. Порівнюються час, рівень справедливості Z*
(найбільше значення змінної Z етапу 1) і збіг підсумкових планів по заявках.
"""
import contextlib
import io
import os
import random
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from app.optimizer import distribute as dist
from app.optimizer.scipy_solver import calculate_scipy_distribution
from app.tests.helpers import EuclidRouting

RT = EuclidRouting()
_real_simplex = dist.simplex_solve
_captured = {}


def _spy(A, b, c, sense, max_iters=500):
    status, x = _real_simplex(A, b, c, sense, max_iters)
    if 'z' not in _captured and x is not None:
        _captured['z'] = x[-1]          # перше звернення - Етап 1, останній елемент - Z
    return status, x


def make_instance(n, seed=1, n_wh=4):
    rng = random.Random(seed)
    stocks = [{'resource_id': 1, 'warehouse_id': w, 'amount': n * 2,
               'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12} for w in range(n_wh)]
    reqs = [{'id': i, 'resource_id': 1, 'amount_needed': rng.randint(1, 30), 'priority': round(rng.uniform(0.1, 1.0), 2),
             'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12} for i in range(n)]
    return stocks, reqs


def highs_stage1_z(stocks, reqs):
    """Z* етапу 1, знайдене HiGHS незалежно від основного коду."""
    ns, nr = len(stocks), len(reqs)
    nv = ns * nr + 1
    supply = sum(s['amount'] for s in stocks)
    i_idx, j_idx = np.repeat(np.arange(ns), nr), np.tile(np.arange(nr), ns)
    col = i_idx * nr + j_idx
    w = np.array([min(r['amount_needed'], supply) * r['priority'] for r in reqs], dtype=float)
    rows = np.concatenate([i_idx, ns + j_idx, ns + nr + j_idx, ns + nr + np.arange(nr)])
    cols = np.concatenate([col, col, col, np.full(nr, nv - 1)])
    data = np.concatenate([np.ones(len(col)), np.ones(len(col)), -np.ones(len(col)), w])
    A = coo_matrix((data, (rows, cols)), shape=(ns + 2 * nr, nv)).tocsr()
    b = np.concatenate([[s['amount'] for s in stocks], [r['amount_needed'] for r in reqs], np.zeros(nr)]).astype(float)
    c = np.zeros(nv)
    c[-1] = -1
    return -linprog(c, A_ub=A, b_ub=b, bounds=[(0, None)] * nv, method='highs').fun


def per_request(plan):
    got = {}
    for it in plan:
        got[it['request_id']] = got.get(it['request_id'], 0) + it['amount']
    return got


def main(sizes):
    print('Заявок | Власний, с | HiGHS, с | Z* власний | Z* HiGHS | Збіг планів')
    for n in sizes:
        stocks, reqs = make_instance(n)
        _captured.clear()
        dist.simplex_solve = _spy
        with contextlib.redirect_stdout(io.StringIO()):
            t = time.perf_counter()
            own = dist.calculate_distribution(reqs, stocks, routing_service=RT, own_solver_max_requests=10 ** 9)
            t_own = time.perf_counter() - t
        dist.simplex_solve = _real_simplex
        with contextlib.redirect_stdout(io.StringIO()):
            t = time.perf_counter()
            sci = calculate_scipy_distribution(reqs, stocks, routing_service=RT)
            t_sci = time.perf_counter() - t
        z_sci = highs_stage1_z(stocks, reqs)
        g1, g2 = per_request(own), per_request(sci)
        same = sum(1 for r in reqs if abs(g1.get(r['id'], 0) - g2.get(r['id'], 0)) < 1e-9)
        print('%6d | %10.3f | %8.4f | %10.6f | %8.6f | %d з %d' % (n, t_own, t_sci, _captured['z'], z_sci, same, n))


if __name__ == '__main__':
    main([int(a) for a in sys.argv[1:]] or [25, 50, 100, 200, 300])
