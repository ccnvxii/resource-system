import numpy as np
from ..services import DistanceMatrixService


# -------------------------------
# ДОПОМІЖНІ функції
# -------------------------------

def get_common_resource_ids(requests, stocks):
    """Знаходить і сортує ID ресурсів, які є і в заявках, і на складах."""
    return sorted(
        set(r['resource_id'] for r in requests)
        & set(s['resource_id'] for s in stocks)
    )


def build_distance_matrix(stocks, requests_list, routing_service):
    """
    Створює матрицю логістичних відстаней між складами та заявниками.
    Використовується для кешування результатів маршрутизації (O(1) доступ).
    """
    n_stk, n_req = len(stocks), len(requests_list)
    dist_matrix = np.zeros((n_stk, n_req))

    for i, stk in enumerate(stocks):
        for j, req in enumerate(requests_list):
            dist_matrix[i, j] = routing_service.get_distance(
                stk.get('lat'), stk.get('lng'),
                req.get('lat'), req.get('lng')
            )
    return dist_matrix


# ----------------------------------------------------------
# 1. СИМПЛЕКС-МЕТОД ТА ЛЕКСИКОГРАФІЧНИЙ РОЗПОДІЛ (EQUITY)
# ----------------------------------------------------------

def pivot_step(tableau, pivot_row, pivot_col):
    pivot_val = tableau[pivot_row, pivot_col]
    if abs(pivot_val) < 1e-12:
        raise ZeroDivisionError('Pivot value almost 0.')

    tableau[pivot_row, :] /= pivot_val
    for r in range(tableau.shape[0]):
        if r != pivot_row:
            tableau[r, :] -= tableau[r, pivot_col] * tableau[pivot_row, :]


def find_entering_var(tableau, tol=1e-9):
    obj = tableau[-1, :-1]
    max_val = np.max(obj)
    if max_val <= tol:
        return None
    return int(np.argmax(obj))


def find_leaving_var(tableau, pivot_col, tol=1e-12):
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

    M_val = 1e6
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

    return tableau, basic_vars, var_names


def simplex_solve(A, b, c_minimize, ineq_sense, max_iters=500):
    try:
        tableau, basic_vars, var_names = build_tableau_M(A, b, c_minimize, ineq_sense)

        for _ in range(max_iters):
            ent = find_entering_var(tableau)
            if ent is None:
                break
            lv = find_leaving_var(tableau, ent)
            if lv is None:
                return 'unbounded', None

            basic_vars[lv] = ent
            pivot_step(tableau, lv, ent)
        else:
            return 'iteration_limit_reached', None

        infeasible = False
        for i, bi in enumerate(basic_vars):
            if var_names[bi].startswith('a'):
                val = tableau[i, -1]
                if val > 1e-6:
                    infeasible = True
                    break

        if infeasible:
            return 'infeasible', None

        n_orig = len(c_minimize)
        res_x = np.zeros(n_orig)
        for i, bi in enumerate(basic_vars):
            if bi < n_orig:
                res_x[bi] = tableau[i, -1]

        return 'optimal', res_x

    except ZeroDivisionError:
        return 'pivot_error', None
    except Exception as e:
        print(f"Simplex Exception: {e}")
        return 'error', None


def calculate_distribution(requests, stocks):
    """Розподіл для стандартних ресурсів (Лінійне програмування + Equity)"""
    final_plan = []
    routing_service = DistanceMatrixService()
    common_ids = get_common_resource_ids(requests, stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        n_req, n_stk = len(r_sub), len(s_sub)
        n_vars = n_stk * n_req + 1

        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)

        base_A, base_b, base_sense = [], [], []

        for i in range(n_stk):
            row = np.zeros(n_vars)
            row[i * n_req: (i + 1) * n_req] = 1
            base_A.append(row)
            base_b.append(s_sub[i]['amount'])
            base_sense.append('<=')

        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            base_A.append(row)
            base_b.append(r_sub[j]['amount_needed'])
            base_sense.append('<=')

        for j in range(n_req):
            row = np.zeros(n_vars)
            for i in range(n_stk):
                row[i * n_req + j] = 1
            weight = (r_sub[j]['amount_needed'] * r_sub[j]['priority']) / 10.0
            row[-1] = -weight
            base_A.append(row)
            base_b.append(0)
            base_sense.append('>=')

        # ЕТАП 1
        c_stage1 = np.zeros(n_vars)
        c_stage1[-1] = -1.0
        status_s1, res_s1 = simplex_solve(np.array(base_A), np.array(base_b), c_stage1, base_sense)

        if status_s1 != 'optimal' or res_s1 is None:
            continue

        opt_Z = res_s1[-1]

        # ЕТАП 2
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
                distance_bonus = 1.0 / max(dist, 1.0)
                distance_bonus = min(distance_bonus, 0.005)

                if s_sub[i]['amount'] >= r_sub[j]['amount_needed']:
                    full_order_bonus = 0.01
                else:
                    full_order_bonus = 0.0

                c_stage2[idx] = -(0.0001 + distance_bonus + full_order_bonus)

        c_stage2[-1] = 0.0
        status_s2, best_x = simplex_solve(np.array(A_stage2), np.array(b_stage2), c_stage2, sense_stage2)

        if status_s2 != 'optimal' or best_x is None:
            best_x = res_s1

        # ЕТАП 3
        if best_x is not None:
            allocated = np.zeros((n_stk, n_req), dtype=int)
            exact_distribution = np.zeros((n_stk, n_req))

            for i in range(n_stk):
                for j in range(n_req):
                    exact_distribution[i, j] = best_x[i * n_req + j]

            free_stock = [s['amount'] for s in s_sub]
            free_demand = [r['amount_needed'] for r in r_sub]

            for i in range(n_stk):
                for j in range(n_req):
                    val = exact_distribution[i, j]
                    if val > 0.001:
                        floor_val = int(np.floor(val))
                        allocated[i, j] = floor_val
                        free_stock[i] -= floor_val
                        free_demand[j] -= floor_val

            remainder_candidates = []
            for i in range(n_stk):
                for j in range(n_req):
                    fraction = exact_distribution[i, j] - np.floor(exact_distribution[i, j])
                    if fraction > 0.001 or exact_distribution[i, j] > 0:
                        score = r_sub[j]['priority'] * 10.0 + fraction
                        remainder_candidates.append((score, i, j))

            remainder_candidates.sort(key=lambda x: x[0], reverse=True)

            for _, i, j in remainder_candidates:
                if free_stock[i] > 0 and free_demand[j] > 0:
                    allocated[i, j] += 1
                    free_stock[i] -= 1
                    free_demand[j] -= 1

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


# ----------------------------------------------------------
# 2. ЖОРСТКИЙ РОЗПОДІЛ СТРАТЕГІЧНИХ ВАНТАЖІВ (TRIAGE)
# ----------------------------------------------------------

def calculate_strict_priority(requests, stocks):
    """Розподіл для стратегічних ресурсів (Жадібна евристика + Order Consolidation)"""
    final_plan = []
    routing_service = DistanceMatrixService()
    common_ids = get_common_resource_ids(requests, stocks)

    for res_id in common_ids:
        r_sub = [r for r in requests if r['resource_id'] == res_id]
        s_sub = [s for s in stocks if s['resource_id'] == res_id]

        for idx, req in enumerate(r_sub):
            req['_idx'] = idx

        stock_available = {i: int(s['amount']) for i, s in enumerate(s_sub)}
        n_stk, n_req = len(s_sub), len(r_sub)

        dist_matrix = build_distance_matrix(s_sub, r_sub, routing_service)

        for p in range(10, -1, -1):
            if sum(stock_available.values()) == 0:
                break

            p_requests = [r for r in r_sub if int(r['priority']) == p]
            if not p_requests:
                continue

            needs_dist_recalc = True

            while p_requests:
                if needs_dist_recalc:
                    for req in p_requests:
                        j = req['_idx']
                        active_dists = [
                            dist_matrix[i, j] for i in range(n_stk) if stock_available[i] > 0
                        ]
                        req['_curr_min_dist'] = min(active_dists) if active_dists else float('inf')

                    needs_dist_recalc = False

                valid_p_requests = [r for r in p_requests if r['_curr_min_dist'] != float('inf')]
                if not valid_p_requests:
                    break

                valid_p_requests.sort(
                    key=lambda x: (
                        -float(x['priority']),
                        x['_curr_min_dist'],
                        int(x['amount_needed'])
                    )
                )

                req = valid_p_requests[0]
                p_requests.remove(req)
                j = req['_idx']
                demand = int(req['amount_needed'])

                if demand <= 4:
                    min_quantum = 1
                elif demand <= 50:
                    min_quantum = max(2, int(demand * 0.25))
                else:
                    min_quantum = max(10, int(demand * 0.15))

                total_avail = sum(stock_available.values())
                if total_avail < min_quantum:
                    continue

                candidates = []
                for i in range(n_stk):
                    if stock_available[i] > 0:
                        candidates.append({
                            'index': i,
                            'warehouse': s_sub[i],
                            'amount': stock_available[i],
                            'distance': dist_matrix[i, j]
                        })

                full_candidates = [c for c in candidates if c['amount'] >= demand]
                if full_candidates:
                    selected = min(full_candidates, key=lambda c: (c['distance'], c['index']))
                    i = selected['index']

                    stock_available[i] -= demand
                    if stock_available[i] == 0:
                        needs_dist_recalc = True

                    final_plan.append({
                        'request_id': req['id'],
                        'warehouse_id': selected['warehouse']['warehouse_id'],
                        'amount': float(demand),
                        'warehouse_lat': selected['warehouse'].get('lat'),
                        'warehouse_lng': selected['warehouse'].get('lng'),
                        'recipient_lat': req.get('lat'),
                        'recipient_lng': req.get('lng'),
                    })
                    continue

                candidates.sort(key=lambda c: (-c['amount'], c['distance']))
                alloc_plan = []
                rem = demand

                for c in candidates:
                    if rem <= 0:
                        break
                    take = min(rem, c['amount'])
                    alloc_plan.append((c['index'], c['warehouse'], take))
                    rem -= take

                allocated_total = demand - rem

                if allocated_total >= min_quantum:
                    for i, wh, take in alloc_plan:
                        stock_available[i] -= take
                        if stock_available[i] == 0:
                            needs_dist_recalc = True

                        final_plan.append({
                            'request_id': req['id'],
                            'warehouse_id': wh['warehouse_id'],
                            'amount': float(take),
                            'warehouse_lat': wh.get('lat'),
                            'warehouse_lng': wh.get('lng'),
                            'recipient_lat': req.get('lat'),
                            'recipient_lng': req.get('lng'),
                        })

        for req in r_sub:
            req.pop('_idx', None)
            req.pop('_curr_min_dist', None)

    return final_plan