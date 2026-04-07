import pulp

def calculate_distribution(requests, stocks):
    """
    Реалізація Weighted Max-Min Fairness.
    """
    plan_items = []
    resource_ids = set(r['resource_id'] for r in requests)

    for res_id in resource_ids:
        reqs_sub = [r for r in requests if r['resource_id'] == res_id]
        stocks_sub = [s for s in stocks if s['resource_id'] == res_id]

        total_stock = sum(s['amount'] for s in stocks_sub)
        if not reqs_sub or total_stock <= 0:
            continue

        prob = pulp.LpProblem(f"Fair_Dist_{res_id}", pulp.LpMaximize)

        # Змінні: скільки з кожного складу на кожну заявку
        x = pulp.LpVariable.dicts("dist",
                                 ((s['warehouse_id'], r['id']) for s in stocks_sub for r in reqs_sub),
                                 lowBound=0,
                                 cat='Integer')

        # Рівень задоволеності (Z)
        Z = pulp.LpVariable("Min_Satisfaction_Level", lowBound=0)

        # Цільова функція: Максимізуємо мінімальне задоволення + ефективність використання залишків
        prob += Z + 0.00001 * pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub for r in reqs_sub])

        # Обмеження 1: Склади
        for s in stocks_sub:
            prob += pulp.lpSum([x[(s['warehouse_id'], r['id'])] for r in reqs_sub]) <= s['amount']

        # Обмеження 2: Запити
        for r in reqs_sub:
            prob += pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub]) <= r['amount_needed']

        # Обмеження 3: Weighted Fairness
        for r in reqs_sub:
            # Формула: (Отримано / Треба) * Пріоритет >= Z
            # Для лінеаризації: Отримано >= Z * (Треба / Пріоритет)
            # Додаємо захист від ділення на нуль
            weight = r['amount_needed'] / max(r['priority'], 0.001)
            prob += pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub]) >= Z * weight

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[prob.status] == 'Optimal':
            for (w_id, r_id), var in x.items():
                if var.varValue > 0.001:
                    plan_items.append({
                        'request_id': r_id,
                        'warehouse_id': w_id,
                        'amount': float(round(var.varValue, 2))
                    })
    return plan_items