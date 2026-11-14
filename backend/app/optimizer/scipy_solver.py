import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, vstack

from app.optimizer.distribute import (
    get_common_resource_ids,
    build_distance_matrix,
    create_plan_item,
    discretize_with_greedy_remainders,
    DistanceMatrixService
)


def solve_resource_scipy(r_sub, s_sub, dist_matrix):
    """
    Розв'язує справедливий розподіл одного ресурсу (Етапи 1 і 2 - LP за допомогою SciPy linprog / HiGHS,
    Етап 3 - спільна з власним вирішувачем жадібна дискретизація).
    Модель повністю збігається з calculate_distribution: ті самі обмеження, вага w_j = P_j * min(d_j, Q),
    допуск 0.001 для Z, ті самі бонуси логістичного критерію.

    Повертає кортеж (позиції_плану, статус, Z*): статус 'optimal' або 'failed'.
    """
    n_req, n_stk = len(r_sub), len(s_sub)
    n_vars = n_stk * n_req + 1                       # x_ij (за рядками: i * n_req + j) та Z
    total_supply = sum(s['amount'] for s in s_sub)

    i_idx = np.repeat(np.arange(n_stk), n_req)
    j_idx = np.tile(np.arange(n_req), n_stk)
    col = i_idx * n_req + j_idx
    ones = np.ones(len(col))

    weights = np.array([min(r['amount_needed'], total_supply) * r['priority'] for r in r_sub], dtype=float)
    fair_rows = n_stk + n_req + np.arange(n_req)

    rows = np.concatenate([i_idx, n_stk + j_idx, n_stk + n_req + j_idx, fair_rows])
    cols = np.concatenate([col, col, col, np.full(n_req, n_vars - 1)])
    data = np.concatenate([ones, ones, -ones, weights])
    # sum_j x_ij <= q_i ;  sum_i x_ij <= d_j ;  -sum_i x_ij + w_j * Z <= 0
    A_ub = coo_matrix((data, (rows, cols)), shape=(n_stk + 2 * n_req, n_vars)).tocsr()
    b_ub = np.concatenate([
        [s['amount'] for s in s_sub],
        [r['amount_needed'] for r in r_sub],
        np.zeros(n_req),
    ]).astype(float)
    bounds = [(0, None)] * n_vars

    # ЕТАП 1: максимізація Z
    c1 = np.zeros(n_vars)
    c1[-1] = -1.0
    res1 = linprog(c=c1, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    if not res1.success:
        return [], 'failed', None
    opt_z = res1.x[-1]

    # ЕТАП 2: логістика за зафіксованого Z (Z >= Z* - 0.001)
    z_row = csr_matrix(([-1.0], ([0], [n_vars - 1])), shape=(1, n_vars))
    A2 = vstack([A_ub, z_row], format='csr')
    b2 = np.concatenate([b_ub, [-max(0.0, opt_z - 0.001)]])

    max_dist = np.max(dist_matrix) if np.max(dist_matrix) >= 1.0 else 1.0
    distance_bonus = 0.005 * (1.0 - np.asarray(dist_matrix, dtype=float) / max_dist)
    stock_amount = np.array([s['amount'] for s in s_sub], dtype=float).reshape(-1, 1)
    need = np.array([r['amount_needed'] for r in r_sub], dtype=float).reshape(1, -1)
    full_bonus = np.where(stock_amount >= need, 0.01, 0.0)
    c2 = np.zeros(n_vars)
    c2[:-1] = -(0.0001 + distance_bonus + full_bonus).reshape(-1)

    res2 = linprog(c=c2, A_ub=A2, b_ub=b2, bounds=bounds, method='highs')
    best_x = res2.x if res2.success else res1.x

    # ЕТАП 3: дискретизація залишків (та сама функція, що й у власному вирішувачі)
    exact = best_x[:-1].reshape(n_stk, n_req)
    allocated = discretize_with_greedy_remainders(exact, s_sub, r_sub)

    plan = []
    for i in range(n_stk):
        for j in range(n_req):
            if allocated[i, j] > 0:
                plan.append(create_plan_item(r_sub[j], s_sub[i], allocated[i, j]))
    return plan, 'optimal', opt_z


def calculate_scipy_distribution(requests, stocks, routing_service=None):
    """
    Справедливий розподіл усіх ресурсів із використанням індустріального вирішувача SciPy linprog (HiGHS).
    Еталон для перевірки власної реалізації (див. test_fair_comp.py та compare_solvers.py).
    """
    final_plan = []
    if routing_service is None:
        routing_service = DistanceMatrixService()

    for res_id in get_common_resource_ids(requests, stocks):
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]
        if not r_sub or not s_sub or sum(s['amount'] for s in s_sub) <= 0:
            continue
        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)
        plan, status, _ = solve_resource_scipy(r_sub, s_sub, dist_matrix)
        final_plan.extend(plan)

    return final_plan
