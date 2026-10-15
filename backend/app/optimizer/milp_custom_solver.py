import numpy as np
from app.optimizer.distribute import (
    get_common_resource_ids,
    build_distance_matrix,
    create_plan_item,
    DistanceMatrixService,
    simplex_solve
)


def branch_and_bound_solve(base_A, base_b, base_sense, c_minimize, n_integer_vars, max_nodes=500):
    """
    Власний алгоритм Гілок і Меж (Branch and Bound) поверх власного Симплекс-методу.
    Шукає точний цілочисельний оптимум (MILP) без зовнішніх C++ вирішувачів.
    """
    best_obj = np.inf
    best_x = None

    # Черга вузлів дерева B&B: кожна позиція містить (A, b, sense)
    stack = [(list(base_A), list(base_b), list(base_sense))]
    nodes_processed = 0

    while stack and nodes_processed < max_nodes:
        nodes_processed += 1
        curr_A, curr_b, curr_sense = stack.pop()

        # 1. Розв'язуємо LP-релаксацію поточного вузла Симплекс-методом
        status, x_sol = simplex_solve(np.array(curr_A), np.array(curr_b), c_minimize, curr_sense)

        if status != 'optimal' or x_sol is None:
            continue  # Недопустима гілка (Infeasible)

        # Розраховуємо значення цільової функції у поточному вузлі
        current_obj = np.dot(c_minimize, x_sol)

        # 2. Відтинання гілок за цільовою функцією (Bounding)
        if current_obj >= best_obj - 1e-7:
            continue  # Поточне рішення не покращує кращий знайдений оптимум

        # 3. Перевірка на цілочисельність шуканих змінних
        fractional_idx = -1
        max_fraction = 0.0

        for idx in range(n_integer_vars):
            val = x_sol[idx]
            frac = abs(val - np.round(val))
            if frac > 1e-4:  # Якщо значення змінної є дробовим
                if frac > max_fraction:
                    max_fraction = frac
                    fractional_idx = idx

        # 4. Якщо дробових змінних немає — знайдено цілочисельне рішення!
        if fractional_idx == -1:
            best_obj = current_obj
            best_x = x_sol.copy()
            continue

        # 5. Розгалуження (Branching) за першою дробовою змінною x_idx
        frac_val = x_sol[fractional_idx]
        val_floor = np.floor(frac_val)
        val_ceil = np.ceil(frac_val)

        # Гілка 1: x_idx <= floor(val)
        A_left, b_left, sense_left = list(curr_A), list(curr_b), list(curr_sense)
        row_left = np.zeros(len(c_minimize))
        row_left[fractional_idx] = 1.0
        A_left.append(row_left)
        b_left.append(val_floor)
        sense_left.append('<=')
        stack.append((A_left, b_left, sense_left))

        # Гілка 2: x_idx >= ceil(val)
        A_right, b_right, sense_right = list(curr_A), list(curr_b), list(curr_sense)
        row_right = np.zeros(len(c_minimize))
        row_right[fractional_idx] = 1.0
        A_right.append(row_right)
        b_right.append(val_ceil)
        sense_right.append('>=')
        stack.append((A_right, b_right, sense_right))

    return best_x


def calculate_custom_milp_distribution(requests, stocks):
    """
    Повноцінна цілочисельна модель (MILP) на чистому Python/NumPy без використання
    зовнішніх бібліотек (SciPy / HiGHS / PuLP).
    """
    final_plan = []
    routing_service = DistanceMatrixService()
    common_ids = get_common_resource_ids(requests, stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_alloc_vars = n_stk * n_req
        n_vars = n_alloc_vars + 1  # x_ij (цілочисельні) + Z (неперервна)

        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)

        base_A, base_b, base_sense = [], [], []

        # 1. Обмеження запасів складів: sum_j x_ij <= q_i
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1.0
            base_A.append(row)
            base_b.append(s_sub[i]['amount'])
            base_sense.append('<=')

        # 2. Обмеження потреб заявок: sum_i x_ij <= d_j
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1.0
            base_A.append(row)
            base_b.append(r_sub[j]['amount_needed'])
            base_sense.append('<=')

        # 3. Обмеження Парето-справедливості: sum_i x_ij - w_j * Z >= 0
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1.0
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = -weight
            base_A.append(row)
            base_b.append(0.0)
            base_sense.append('>=')

        # ЕТАП 1: Максимізація Z (Справедливість) через Branch and Bound
        c_stage1 = np.zeros(n_vars)
        c_stage1[-1] = -1.0  # Мінімізуємо -Z

        res1_x = branch_and_bound_solve(
            base_A, base_b, base_sense,
            c_minimize=c_stage1,
            n_integer_vars=n_alloc_vars,
            max_nodes=300
        )

        if res1_x is None:
            continue

        opt_Z = res1_x[-1]

        # ЕТАП 2: Мінімізація логістичного плеча при фіксованому Z >= opt_Z - 0.001
        A_stage2, b_stage2, sense_stage2 = list(base_A), list(base_b), list(base_sense)

        z_restriction_row = np.zeros(n_vars)
        z_restriction_row[-1] = 1.0
        A_stage2.append(z_restriction_row)
        b_stage2.append(max(0.0, opt_Z - 0.001))
        sense_stage2.append('>=')

        c_stage2 = np.zeros(n_vars)
        for i in range(n_stk):
            for j in range(n_req):
                idx = i * n_req + j
                dist = dist_matrix[i, j]
                distance_bonus = min(1.0 / max(dist, 1.0), 0.005)
                full_order_bonus = 0.01 if s_sub[i]['amount'] >= r_sub[j]['amount_needed'] else 0.0
                c_stage2[idx] = -(0.0001 + distance_bonus + full_order_bonus)

        c_stage2[-1] = 0.0

        res2_x = branch_and_bound_solve(
            A_stage2, b_stage2, sense_stage2,
            c_minimize=c_stage2,
            n_integer_vars=n_alloc_vars,
            max_nodes=300
        )

        best_x = res2_x if res2_x is not None else res1_x

        # Формування підсумкового цілочисельного плану
        if best_x is not None:
            for i in range(n_stk):
                for j in range(n_req):
                    val = int(np.round(best_x[i * n_req + j]))
                    if val > 0:
                        final_plan.append(
                            create_plan_item(r_sub[j], s_sub[i], val)
                        )

    return final_plan