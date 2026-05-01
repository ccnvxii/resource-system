import numpy as np


# --- 1. СИМПЛЕКС-МЕТОД (М-МЕТОД) ---

def pivot_step(tableau, pivot_row, pivot_col):
    pivot_val = tableau[pivot_row, pivot_col]
    if abs(pivot_val) < 1e-12:
        raise ZeroDivisionError('Pivot value almost 0.')
    tableau[pivot_row, :] /= pivot_val
    for r in range(tableau.shape[0]):
        if r != pivot_row:
            tableau[r, :] -= tableau[r, pivot_col] * tableau[pivot_row, :]


def find_entering_var(tableau, tol=1e-9):
    # Шукаємо найбільший коефіцієнт (для мінімізації -Z, що є максимізацією Z)
    obj = tableau[-1, :-1]
    max_val = np.max(obj)
    if max_val <= tol:
        return None
    return int(np.argmax(obj))


def find_leaving_var(tableau, pivot_col, tol=1e-12):
    col = tableau[:-1, pivot_col]
    rhs = tableau[:-1, -1]
    # Правило мінімального відношення
    ratios = [rhs[i] / col[i] if col[i] > tol else np.inf for i in range(len(col))]
    m = np.min(ratios)
    if np.isinf(m):
        return None
    return int(np.argmin(ratios))


def build_tableau_M(A, b, c_minimize, ineq_sense):
    m, n = A.shape
    blocks = [A.copy()]
    art_cols = []
    var_names = [f'x{j}' for j in range(n)]

    # Додаємо додаткові та штучні змінні
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

    # Коефіцієнти цільової функції
    tableau[-1, :n] = -c_minimize
    M_val = 1e7  # Великий штраф для М-методу
    for j in art_cols:
        tableau[-1, j] = -M_val

    # Встановлення початкового базису
    basic_vars = []
    for i in range(m):
        found = False
        for j in range(n, total_vars):
            col = tableau[:m, j]
            unit = np.zeros(m);
            unit[i] = 1
            if np.allclose(col, unit):
                basic_vars.append(j)
                found = True
                break
        if not found: raise RuntimeError(f"Basis error at row {i}")

    # Корекція Z-рядка для штучних змінних (виключення М з базису)
    for i, bi in enumerate(basic_vars):
        if var_names[bi].startswith('a'):
            tableau[-1, :] -= (-M_val) * tableau[i, :]

    return tableau, basic_vars


def simplex_solve(A, b, c_minimize, ineq_sense):
    try:
        tableau, basic_vars = build_tableau_M(A, b, c_minimize, ineq_sense)
        for _ in range(1000):
            ent = find_entering_var(tableau)
            if ent is None: break
            lv = find_leaving_var(tableau, ent)
            if lv is None: return 'unbounded', None
            basic_vars[lv] = ent
            pivot_step(tableau, lv, ent)

        n_orig = len(c_minimize)
        res_x = np.zeros(n_orig)
        for i, bi in enumerate(basic_vars):
            if bi < n_orig: res_x[bi] = tableau[i, -1]
        return 'optimal', res_x
    except Exception:
        return 'error', None


# --- 2. МЕТОД ГІЛОК ТА МЕЖ (ЦІЛОЧИСЕЛЬНІСТЬ) ---

def branch_and_bound(c, A, b, sense, int_vars):
    status, res = simplex_solve(A, b, c, sense)
    if status != 'optimal': return None, -1e18

    # Обчислюємо значення цільової функції (пам'ятаємо про мінус)
    obj_val = -np.dot(c, res)

    branch_idx = -1
    for idx in int_vars:
        if not np.isclose(res[idx], np.round(res[idx]), atol=1e-2):
            branch_idx = idx
            break

    if branch_idx == -1: return res, obj_val

    val = res[branch_idx]

    # Гілка x <= floor(val)
    A_l = np.vstack([A, np.zeros(len(c))])
    A_l[-1, branch_idx] = 1
    res_l, obj_l = branch_and_bound(c, A_l, np.append(b, np.floor(val)), sense + ['<='], int_vars)

    # Гілка x >= ceil(val)
    A_r = np.vstack([A, np.zeros(len(c))])
    A_r[-1, branch_idx] = 1
    res_r, obj_r = branch_and_bound(c, A_r, np.append(b, np.ceil(val)), sense + ['>='], int_vars)

    return (res_l, obj_l) if obj_l >= obj_r else (res_r, obj_r)


# --- 3. ГОЛОВНА ЛОГІКА РОЗПОДІЛУ ---

def calculate_distribution(requests, stocks):
    final_plan = []
    # Знаходимо ресурси, які є і в заявках, і на складах
    common_ids = set(r['resource_id'] for r in requests) & set(s['resource_id'] for s in stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1  # x_ij + Z

        # Мінімізуємо (-Z) = Максимізуємо Z
        c_min = np.zeros(n_vars)
        c_min[-1] = -1.0
        c_min[:-1] = -0.0001  # Мікро-добавка для утилізації залишків

        A, b, sense = [], [], []

        # Обмеження складів: сума виданого <= Stock
        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1
            A.append(row);
            b.append(s_sub[i]['amount']);
            sense.append('<=')

        # Обмеження заявок: сума отриманого <= Demand
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk): row[i * n_req + j] = 1
            A.append(row);
            b.append(r_sub[j]['amount_needed']);
            sense.append('<=')

        # Обмеження Fairness: Satisfaction >= Z * Priority * Demand
        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk): row[i * n_req + j] = 1

            # ВАГА: Demand * Priority (Нормалізовано для стабільності М-методу)
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = -weight
            A.append(row);
            b.append(0);
            sense.append('>=')

        # Індекси змінних x_ij для цілочисельності
        int_indices = list(range(n_stk * n_req))
        best_x, _ = branch_and_bound(c_min, np.array(A), np.array(b), sense, int_indices)

        if best_x is not None:
            for i in range(n_stk):
                for j in range(n_req):
                    val = best_x[i * n_req + j]
                    if val > 0.05:
                        final_plan.append({
                            'request_id': r_sub[j]['id'],
                            'warehouse_id': s_sub[i]['warehouse_id'],
                            'amount': float(round(val, 2))
                        })

    return final_plan
