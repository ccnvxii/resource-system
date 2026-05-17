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
    """Вычисление расстояния в км между двумя GPS точками (Формула Гаверсинуса)"""
    if None in (lat1, lng1, lat2, lng2):
        return 500.0

    R = 6371.0  # Радиус Земли в км
    rad_lat1, rad_lng1 = np.radians(lat1), np.radians(lng1)
    rad_lat2, rad_lng2 = np.radians(lat2), np.radians(lng2)

    dlat = rad_lat2 - rad_lat1
    dlng = rad_lng2 - rad_lng1

    a = np.sin(dlat / 2) ** 2 + np.cos(rad_lat1) * np.cos(rad_lat2) * np.sin(dlng / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


# --- 3. УЛУЧШЕННАЯ ЛОГИКА РАСПРЕДЕЛЕНИЯ (ГЕОГРАФИЯ + КОНСОЛИДАЦИЯ) ---

def calculate_distribution(requests, stocks):
    final_plan = []
    common_ids = set(r['resource_id'] for r in requests) & set(s['resource_id'] for s in stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1  # x_ij + Z

        c_min = np.zeros(n_vars)
        c_min[-1] = -1.0  # Главная цель: максимизация справедливости Z

        # Заполняем веса для путей x_ij с учетом географии и возможности полной сборки
        for i in range(n_stk):
            for j in range(n_req):
                idx = i * n_req + j

                dist = calculate_distance(
                    s_sub[i].get('lat'), s_sub[i].get('lng'),
                    r_sub[j].get('lat'), r_sub[j].get('lng')
                )

                distance_bonus = 1.0 / max(dist, 1.0)
                distance_bonus = min(distance_bonus, 0.01)

                if s_sub[i]['amount'] >= r_sub[j]['amount_needed']:
                    full_order_bonus = 0.5
                else:
                    full_order_bonus = 0.0

                c_min[idx] = -(0.0001 + distance_bonus + full_order_bonus)

        A, b, sense = [], [], []

        # Ограничения складов <= Stock
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1
            A.append(row)
            b.append(s_sub[i]['amount'])
            sense.append('<=')

        # Ограничения заявок <= Demand
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            A.append(row)
            b.append(r_sub[j]['amount_needed'])
            sense.append('<=')

        # Ограничения Fairness
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = -weight
            A.append(row)
            b.append(0)
            sense.append('>=')

        status, best_x = simplex_solve(np.array(A), np.array(b), c_min, sense)

        if status == 'optimal' and best_x is not None:
            allocated = np.zeros((n_stk, n_req), dtype=int)
            residuals = np.zeros((n_stk, n_req))

            free_stock = [s['amount'] for s in s_sub]
            free_demand = [r['amount_needed'] for r in r_sub]

            # Шаг 1: Округление вниз
            for i in range(n_stk):
                for j in range(n_req):
                    val = best_x[i * n_req + j]
                    if val > 0.001:
                        floor_val = int(np.floor(val))
                        allocated[i, j] = floor_val
                        residuals[i, j] = val - floor_val

                        free_stock[i] -= floor_val
                        free_demand[j] -= floor_val

            # Шаг 2: Распределение остатков с учетом накопленного объема
            cell_residuals = []
            for i in range(n_stk):
                for j in range(n_req):
                    if residuals[i, j] > 0.001:
                        consolidation_bonus = allocated[i, j] * 10.0
                        priority_score = residuals[i, j] + consolidation_bonus
                        cell_residuals.append((priority_score, i, j))

            cell_residuals.sort(key=lambda x: x[0], reverse=True)

            for _, i, j in cell_residuals:
                while free_stock[i] > 0 and free_demand[j] > 0:
                    allocated[i, j] += 1
                    free_stock[i] -= 1
                    free_demand[j] -= 1

            # Шаг 3: Логистический фильтр объединения
            for j in range(n_req):
                if np.sum(allocated[:, j]) > 0:
                    main_stk = int(np.argmax(allocated[:, j]))
                    if allocated[main_stk, j] > 0:
                        for i in range(n_stk):
                            if i != main_stk and 0 < allocated[i, j] <= 15:
                                moved_amount = allocated[i, j]
                                if free_stock[main_stk] >= moved_amount:
                                    allocated[main_stk, j] += moved_amount
                                    free_stock[main_stk] -= moved_amount
                                    allocated[i, j] = 0
                                    free_stock[i] += moved_amount

            # Шаг 4: Экспорт в систему (Добавлено прокидання широти та довготи)
            for i in range(n_stk):
                for j in range(n_req):
                    if allocated[i, j] > 0:
                        final_plan.append({
                            'request_id': r_sub[j]['id'],
                            'warehouse_id': s_sub[i]['warehouse_id'],
                            'amount': float(allocated[i, j]),

                            # Передаємо координати складу та отримувача для побудови ГІС-маршрутів
                            'warehouse_lat': s_sub[i].get('lat'),
                            'warehouse_lng': s_sub[i].get('lng'),
                            'recipient_lat': r_sub[j].get('lat'),
                            'recipient_lng': r_sub[j].get('lng')
                        })

    return final_plan