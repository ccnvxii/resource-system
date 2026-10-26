import numpy as np
from scipy.optimize import linprog
from app.optimizer.distribute import (
    get_common_resource_ids,
    build_distance_matrix,
    create_plan_item,
    discretize_with_greedy_remainders,
    DistanceMatrixService
)


def calculate_scipy_distribution(requests, stocks):
    """
    Гібридна модель розподілу із використанням індустріального вирішувача SciPy linprog (HiGHS).
    Повністю синхронізована за логікою, обмеженнями та нормалізацією з основним вирішувачем.
    Етапи 1 і 2 розв'язуються як неперервна LP-задача, Етап 3 — жадібна дискретизація залишків.
    """
    final_plan = []
    routing_service = DistanceMatrixService()
    common_ids = get_common_resource_ids(requests, stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1  # x_ij + Z

        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)

        A_ub, b_ub = [], []

        # 1. Обмеження складських запасів: sum_j x_ij <= q_i
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1.0
            A_ub.append(row)
            b_ub.append(s_sub[i]['amount'])

        # 2. Обмеження потреб заявок: sum_i x_ij <= d_j
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1.0
            A_ub.append(row)
            b_ub.append(r_sub[j]['amount_needed'])

        # 3. Обмеження зваженої справедливості: sum_i x_ij - w_j * Z >= 0  ==>  -sum_i x_ij + w_j * Z <= 0
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = -1.0
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = weight
            A_ub.append(row)
            b_ub.append(0.0)

        bounds = [(0, None) for _ in range(n_vars)]

        # ЕТАП 1: Максимізація Z (Мінімізація -Z)
        c_stage1 = np.zeros(n_vars)
        c_stage1[-1] = -1.0

        res1 = linprog(
            c=c_stage1,
            A_ub=np.array(A_ub),
            b_ub=np.array(b_ub),
            bounds=bounds,
            method='highs'
        )

        if not res1.success:
            continue

        opt_Z = res1.x[-1]

        # ЕТАП 2: Мінімізація логістичного плеча за зафіксованого opt_Z з урахуванням Min-Max нормалізації
        A_ub_s2 = list(A_ub)
        b_ub_s2 = list(b_ub)

        # Обмеження Z >= opt_Z - 0.001  ==>  -Z <= -(opt_Z - 0.001)
        z_row = np.zeros(n_vars)
        z_row[-1] = -1.0
        A_ub_s2.append(z_row)
        b_ub_s2.append(-max(0.0, opt_Z - 0.001))

        # Визначаємо максимальну відстань у матриці для лінійної нормалізації
        max_dist = np.max(dist_matrix) if np.max(dist_matrix) >= 1.0 else 1.0

        c_stage2 = np.zeros(n_vars)
        for i in range(n_stk):
            for j in range(n_req):
                idx = i * n_req + j
                dist = dist_matrix[i, j]

                # Синхронізований розрахунок бонусів (Min-Max Scaling замість жорсткої стелі)
                dist_norm = dist / max_dist
                distance_bonus = 0.005 * (1.0 - dist_norm)

                full_order_bonus = 0.01 if s_sub[i]['amount'] >= r_sub[j]['amount_needed'] else 0.0
                c_stage2[idx] = -(0.0001 + distance_bonus + full_order_bonus)

        c_stage2[-1] = 0.0

        res2 = linprog(
            c=c_stage2,
            A_ub=np.array(A_ub_s2),
            b_ub=np.array(b_ub_s2),
            bounds=bounds,
            method='highs'
        )

        best_x_vars = res2.x if res2.success else res1.x

        # ЕТАП 3: Дискретизація залишків та формування підсумкового плану
        if best_x_vars is not None:
            exact_distribution = np.zeros((n_stk, n_req))
            for i in range(n_stk):
                for j in range(n_req):
                    exact_distribution[i, j] = best_x_vars[i * n_req + j]

            allocated = discretize_with_greedy_remainders(exact_distribution, s_sub, r_sub)

            for i in range(n_stk):
                for j in range(n_req):
                    if allocated[i, j] > 0:
                        final_plan.append(create_plan_item(r_sub[j], s_sub[i], allocated[i, j]))

    return final_plan