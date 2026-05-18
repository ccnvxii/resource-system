import numpy as np


# --- 1. СИМПЛЕКС-МЕТОД (М-МЕТОД) ---

def pivot_step(tableau, pivot_row, pivot_col):
    pivot_val = tableau[pivot_row, pivot_col]
    if abs(pivot_val) < 1e-9:
        raise ZeroDivisionError('Pivot value almost 0.')
    tableau[pivot_row, :] /= pivot_val
    for r in range(tableau.shape[0]):
        if r != pivot_row:
            tableau[r, :] -= tableau[r, pivot_col] * tableau[pivot_row, :]


def find_entering_var(tableau, tol=1e-7):
    obj = tableau[-1, :-1]
    max_val = np.max(obj)
    if max_val <= tol:
        return None
    return int(np.argmax(obj))


def find_leaving_var(tableau, pivot_col, tol=1e-9):
    col = tableau[:-1, pivot_col]
    rhs = tableau[:-1, -1]
    ratios = []
    for i in range(len(col)):
        if col[i] > tol:
            ratios.append(rhs[i] / col[i])
        else:
            ratios.append(np.inf)
    m = np.min(ratios)
    if np.isinf(m):
        return None
    return int(np.argmin(ratios))


def build_tableau_M(A, b, c_minimize, ineq_sense):
    m, n = A.shape
    blocks = [A.copy()]
    art_cols = []
    var_names = [f'x{j}' for j in range(n)]

    for i, s in enumerate(ineq_sense):
        if s == '<=':
            col = np.zeros((m, 1))
            col[i, 0] = 1
            blocks.append(col)
            var_names.append(f's{i}')
        elif s == '>=':
            col_sur = np.zeros((m, 1))
            col_sur[i, 0] = -1
            col_art = np.zeros((m, 1))
            col_art[i, 0] = 1
            blocks.append(col_sur)
            var_names.append(f'sur{i}')
            blocks.append(col_art)
            var_names.append(f'a{i}')
            art_cols.append(len(var_names) - 1)

    A_ext = np.hstack(blocks)
    total_vars = A_ext.shape[1]
    tableau = np.zeros((m + 1, total_vars + 1))
    tableau[:m, :total_vars] = A_ext
    tableau[:m, -1] = b

    tableau[-1, :n] = -c_minimize

    M_val = 1e4
    for j in art_cols:
        tableau[-1, j] = -M_val

    basic_vars = []
    for i in range(m):
        found = False
        for j in range(n, total_vars):
            col = tableau[:m, j]
            unit = np.zeros(m)
            unit[i] = 1
            if np.allclose(col, unit, atol=1e-7):
                basic_vars.append(j)
                found = True
                break
        if not found:
            raise RuntimeError(f"Basis error at row {i}")

    for i, bi in enumerate(basic_vars):
        if var_names[bi].startswith('a'):
            tableau[-1, :] -= (-M_val) * tableau[i, :]

    return tableau, basic_vars


def simplex_solve(A, b, c_minimize, ineq_sense):
    try:
        tableau, basic_vars = build_tableau_M(A, b, c_minimize, ineq_sense)
        for _ in range(500):
            ent = find_entering_var(tableau)
            if ent is None:
                break
            lv = find_leaving_var(tableau, ent)
            if lv is None:
                return 'unbounded', None
            basic_vars[lv] = ent
            pivot_step(tableau, lv, ent)
        else:
            return 'error', None

        n_orig = len(c_minimize)
        res_x = np.zeros(n_orig)
        for i, bi in enumerate(basic_vars):
            if bi < n_orig:
                res_x[bi] = tableau[i, -1]
        return 'optimal', res_x
    except Exception:
        return 'error', None


# --- 2. ГЕОГРАФИЧЕСКИЙ РАСЧЕТ РАССТОЯНИЯ ---

def calculate_distance(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return 500.0

    R = 6371.0
    rad_lat1, rad_lng1 = np.radians(lat1), np.radians(lng1)
    rad_lat2, rad_lng2 = np.radians(lat2), np.radians(lng2)

    dlat = rad_lat2 - rad_lat1
    dlng = rad_lng2 - rad_lng1

    a = np.sin(dlat / 2) ** 2 + np.cos(rad_lat1) * np.cos(rad_lat2) * np.sin(dlng / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


# --- 3. ДВОЕТАПНА ЛЕКСИКОГРАФІЧНА ОПТИМІЗАЦІЯ ---

def calculate_distribution(requests, stocks):
    final_plan = []
    common_ids = set(r['resource_id'] for r in requests) & set(s['resource_id'] for s in stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1  # x_ij + Z

        # Базова матриця обмежень для складів та заявок (однакова для обох етапів)
        base_A = []
        base_b = []
        base_sense = []

        # Обмеження складів <= Stock
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1
            base_A.append(row)
            base_b.append(s_sub[i]['amount'])
            base_sense.append('<=')

        # Обмеження заявок <= Demand
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            base_A.append(row)
            base_b.append(r_sub[j]['amount_needed'])
            base_sense.append('<=')

        # Обмеження Fairness (зважена рівність): sum(x_ij) + Z * weight >= 0
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = -weight
            base_A.append(row)
            base_b.append(0)
            base_sense.append('>=')

        # =================================================================
        # ЕТАП 1: Максимізація чистої справедливості Z (Логістика ігнорується)
        # =================================================================
        c_stage1 = np.zeros(n_vars)
        c_stage1[-1] = -1.0  # Мінімізуємо -Z, тобто максимізуємо Z

        status_s1, res_s1 = simplex_solve(np.array(base_A), np.array(base_b), c_stage1, base_sense)

        if status_s1 != 'optimal' or res_s1 is None:
            continue  # Якщо не знайшли розв'язку для справедливості, пропускаємо ресурс

        # Зберігаємо максимально можливий рівень справедливості
        opt_Z = res_s1[-1]

        # =================================================================
        # ЕТАП 2: Оптимізація логістики при зафіксованому рівні справедливості opt_Z
        # =================================================================
        # Додаємо нове обмеження до базової системи: Z >= opt_Z - 0.001
        A_stage2 = list(base_A)
        b_stage2 = list(base_b)
        sense_stage2 = list(base_sense)

        z_restriction_row = np.zeros(n_vars)
        z_restriction_row[-1] = 1.0  # Фіксуємо змінну Z
        A_stage2.append(z_restriction_row)
        b_stage2.append(max(0.0, opt_Z - 0.001))  # Допуск для запобігання чисельної жорсткості
        sense_stage2.append('>=')

        # Формуємо нову цільову функцію для Етапу 2: суворо логістика
        c_stage2 = np.zeros(n_vars)
        for i in range(n_stk):
            for j in range(n_req):
                idx = i * n_req + j

                dist = calculate_distance(
                    s_sub[i].get('lat'), s_sub[i].get('lng'),
                    r_sub[j].get('lat'), r_sub[j].get('lng')
                )

                distance_bonus = 1.0 / max(dist, 1.0)
                distance_bonus = min(distance_bonus, 0.005)

                if s_sub[i]['amount'] >= r_sub[j]['amount_needed']:
                    full_order_bonus = 0.01
                else:
                    full_order_bonus = 0.0

                # Мінімізуємо негативні бонуси = максимізуємо ефективність доставки
                c_stage2[idx] = -(0.0001 + distance_bonus + full_order_bonus)

        # Передаємо унікальний коефіцієнт для Z, щоб рушій не скидав її значення
        c_stage2[-1] = 0.0

        status_s2, best_x = simplex_solve(np.array(A_stage2), np.array(b_stage2), c_stage2, sense_stage2)

        # Якщо етап логістики збігся з помилкою через жорсткість умов, робимо відкат до результатів Етапу 1
        if status_s2 != 'optimal' or best_x is None:
            best_x = res_s1

        # =================================================================
        # ЕТАП 3: Округлення та поштучний пріоритетний розподіл залишків
        # =================================================================
        if best_x is not None:
            allocated = np.zeros((n_stk, n_req), dtype=int)
            exact_distribution = np.zeros((n_stk, n_req))

            for i in range(n_stk):
                for j in range(n_req):
                    exact_distribution[i, j] = best_x[i * n_req + j]

            free_stock = [s['amount'] for s in s_sub]
            free_demand = [r['amount_needed'] for r in r_sub]

            # Округлення вниз
            for i in range(n_stk):
                for j in range(n_req):
                    val = exact_distribution[i, j]
                    if val > 0.001:
                        floor_val = int(np.floor(val))
                        allocated[i, j] = floor_val
                        free_stock[i] -= floor_val
                        free_demand[j] -= floor_val

            # Суворий поштучний дорозподіл залишків на основі ПРІОРИТЕТУ заявки
            remainder_candidates = []
            for i in range(n_stk):
                for j in range(n_req):
                    fraction = exact_distribution[i, j] - np.floor(exact_distribution[i, j])
                    if fraction > 0.001 or exact_distribution[i, j] > 0:
                        # Головний пріоритет — вага замовника, другорядний — дробовий залишок
                        score = r_sub[j]['priority'] * 10.0 + fraction
                        remainder_candidates.append((score, i, j))

            remainder_candidates.sort(key=lambda x: x[0], reverse=True)

            for _, i, j in remainder_candidates:
                if free_stock[i] > 0 and free_demand[j] > 0:
                    allocated[i, j] += 1
                    free_stock[i] -= 1
                    free_demand[j] -= 1

            # Експорт результатів у систему
            for i in range(n_stk):
                for j in range(n_req):
                    if allocated[i, j] > 0:
                        final_plan.append({
                            'request_id': r_sub[j]['id'],
                            'warehouse_id': s_sub[i]['warehouse_id'],
                            'amount': float(allocated[i, j]),
                            'warehouse_lat': s_sub[i].get('lat'),
                            'warehouse_lng': s_sub[i].get('lng'),
                            'recipient_lat': r_sub[j].get('lat'),
                            'recipient_lng': r_sub[j].get('lng')
                        })

    return final_plan