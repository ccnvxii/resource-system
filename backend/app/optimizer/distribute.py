import pulp


def calculate_distribution(requests, stocks):
    """
    Реалізація 'Weighted Max-Min Fairness' через Linear Programming (PuLP).
    Мета: Максимізувати рівень задоволення найменш щасливого користувача,
    зважений на його пріоритет.
    """
    plan_items = []

    # Групуємо по ресурсах (алгоритм запускається окремо для кожного типу)
    resource_ids = set(r['resource_id'] for r in requests)

    for res_id in resource_ids:
        reqs_sub = [r for r in requests if r['resource_id'] == res_id]
        stocks_sub = [s for s in stocks if s['resource_id'] == res_id]

        if not reqs_sub or not stocks_sub:
            continue

        # --- 1. СТВОРЕННЯ МОДЕЛІ ---
        prob = pulp.LpProblem(f"Fair_Dist_{res_id}", pulp.LpMaximize)

        # --- 2. ЗМІННІ ---
        # x[(warehouse, request)] = кількість товару
        x = {}
        for s in stocks_sub:
            for r in reqs_sub:
                x[(s['warehouse_id'], r['id'])] = pulp.LpVariable(
                    f"x_{s['warehouse_id']}_{r['id']}",
                    lowBound=0,
                    cat='Integer'  # Або 'Continuous', якщо це рідина
                )

        # Z - це "рівень справедливості" (допоміжна змінна)
        # Ми будемо намагатися зробити Z якомога більшим
        Z = pulp.LpVariable("Min_Satisfaction_Level", lowBound=0)

        # --- 3. ЦІЛЬОВА ФУНКЦІЯ ---
        # Максимізуємо Z (мінімальний рівень) + маленький бонус за загальну кількість
        # (0.0001 * sum(x) потрібен, щоб розподілити залишки, коли рівність досягнута)
        prob += Z + 0.0001 * pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub for r in reqs_sub])

        # --- 4. ОБМЕЖЕННЯ (CONSTRAINTS) ---

        # А) Не взяти зі складу більше, ніж є
        for s in stocks_sub:
            prob += pulp.lpSum([x[(s['warehouse_id'], r['id'])] for r in reqs_sub]) <= s['amount']

        # Б) Не дати заявці більше, ніж просили
        for r in reqs_sub:
            prob += pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub]) <= r['amount_needed']

        # В) ГОЛОВНЕ ОБМЕЖЕННЯ СПРАВЕДЛИВОСТІ
        # Для кожної заявки: (Отримано / Треба) * Пріоритет >= Z
        # Тобто Z не може бути більшим за найгірший показник у системі.
        # Максимізуючи Z, ми підтягуємо найгіршого вгору.
        for r in reqs_sub:
            total_allocated_to_req = pulp.lpSum([x[(s['warehouse_id'], r['id'])] for s in stocks_sub])

            # Математика: Allocated >= Z * (Needed / Priority)
            # Чим вищий пріоритет, тим менший дільник, тим більше треба дати, щоб задовольнити Z.
            if r['priority'] > 0:
                prob += total_allocated_to_req >= Z * (r['amount_needed'] / r['priority'])

        # --- 5. ВИРІШЕННЯ ---
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # --- 6. ЗБІР РЕЗУЛЬТАТІВ ---
        if pulp.LpStatus[prob.status] == 'Optimal':
            for s in stocks_sub:
                for r in reqs_sub:
                    val = x[(s['warehouse_id'], r['id'])].varValue
                    if val and val > 0:
                        plan_items.append({
                            'request_id': r['id'],
                            'warehouse_id': s['warehouse_id'],
                            'amount': val
                        })

    return plan_items