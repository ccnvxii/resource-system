import numpy as np
from scipy.optimize import linprog
from app.optimizer.distribute import get_common_resource_ids, build_distance_matrix, create_plan_item, DistanceMatrixService


def calculate_milp_distribution(requests, stocks):
    """
    Эталонный точный алгоритм MILP (Mixed-Integer Linear Programming)
    Использует солвер HiGHS с ограничением целочисленности x_ij in Z+
    """
    final_plan = []
    routing_service = DistanceMatrixService()
    common_ids = get_common_resource_ids(requests, stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1  # x_ij (целые) + Z (непрерывная)

        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)

        A_ub, b_ub = [], []

        # 1. Ограничение запасов складов: sum_j x_ij <= q_i
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1.0
            A_ub.append(row)
            b_ub.append(s_sub[i]['amount'])

        # 2. Ограничение потребностей заявок: sum_i x_ij <= d_j
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1.0
            A_ub.append(row)
            b_ub.append(r_sub[j]['amount_needed'])

        # 3. Ограничение взвешенной справедливости: -sum_i x_ij + w_j * Z <= 0
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = -1.0
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = weight
            A_ub.append(row)
            b_ub.append(0.0)

        # Границы переменных
        bounds = [(0, None) for _ in range(n_vars)]

        # Массив целочисленности: 1 для всех x_ij (целые), 0 для Z (непрерывная)
        integrality = [1] * (n_stk * n_req) + [0]

        # ЭТАП 1: Максимизация Z (Минимизация -Z)
        c_stage1 = np.zeros(n_vars)
        c_stage1[-1] = -1.0

        res1 = linprog(
            c=c_stage1,
            A_ub=np.array(A_ub),
            b_ub=np.array(b_ub),
            bounds=bounds,
            integrality=integrality,
            method='highs'
        )

        if not res1.success:
            continue

        opt_Z = res1.x[-1]

        # ЭТАП 2: Миниматизация логистического плеча при зафиксированном opt_Z
        A_ub_s2 = list(A_ub)
        b_ub_s2 = list(b_ub)

        # Ограничение Z >= opt_Z - 1e-4  ==>  -Z <= -(opt_Z - 1e-4)
        z_row = np.zeros(n_vars)
        z_row[-1] = -1.0
        A_ub_s2.append(z_row)
        b_ub_s2.append(-max(0.0, opt_Z - 1e-4))

        c_stage2 = np.zeros(n_vars)
        for i in range(n_stk):
            for j in range(n_req):
                idx = i * n_req + j
                dist = dist_matrix[i, j]

                # Добавляем доминирующий вес приоритета (например, priority * 100)
                priority_weight = r_sub[j]['priority'] * 100.0
                distance_bonus = min(1.0 / max(dist, 1.0), 0.005)

                c_stage2[idx] = -(priority_weight + distance_bonus)

        res2 = linprog(
            c=c_stage2,
            A_ub=np.array(A_ub_s2),
            b_ub=np.array(b_ub_s2),
            bounds=bounds,
            integrality=integrality,
            method='highs'
        )

        best_x = res2.x if res2.success else res1.x

        # Формирование плана из точных целых значений MILP
        for i in range(n_stk):
            for j in range(n_req):
                val = int(round(best_x[i * n_req + j]))
                if val > 0:
                    final_plan.append(create_plan_item(r_sub[j], s_sub[i], val))

    return final_plan