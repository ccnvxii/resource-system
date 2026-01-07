from typing import List, Dict, Any
from copy import deepcopy


def calculate_distribution(
        requests: List[Dict[str, Any]],
        stocks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Чистая функция реализации мат. модели.

    Args:
        requests: Список заявок [{'id': 1, 'resource_id': 2, 'amount_needed': 100, 'priority': 5}, ...]
        stocks: Список запасов [{'warehouse_id': 1, 'resource_id': 2, 'amount': 500}, ...]

    Returns:
        Список транзакций (Plan items): [{'request_id': 1, 'warehouse_id': 1, 'amount': 100}, ...]
    """

    # 1. Глубокое копирование, чтобы не мутировать входные данные в процессе расчетов
    available_stocks = deepcopy(stocks)
    distribution_plan = []

    # 2. Сортировка (реализация шага 4.2: Сортировка по приоритету DESC)
    # Если приоритеты равны, можно добавить вторичную сортировку по количеству или дате
    sorted_requests = sorted(requests, key=lambda x: x['priority'], reverse=True)

    # 3. Алгоритм распределения (Greedy)
    for req in sorted_requests:
        needed = req['amount_needed']
        resource_id = req['resource_id']
        req_id = req['id']

        if needed <= 0:
            continue

        # Ищем склады, где есть этот ресурс
        relevant_stocks = [
            s for s in available_stocks
            if s['resource_id'] == resource_id and s['amount'] > 0
        ]

        # Можно добавить сортировку складов (например, сначала с самых загруженных)
        # relevant_stocks.sort(key=lambda s: s['amount'], reverse=True)

        for stock in relevant_stocks:
            if needed <= 0:
                break

            # Определяем x_ijl (сколько берем с этого склада)
            take_amount = min(needed, stock['amount'])

            # Добавляем в план
            distribution_plan.append({
                'request_id': req_id,
                'resource_id': resource_id,
                'warehouse_id': stock['warehouse_id'],
                'amount': take_amount
            })

            # Обновляем локальные счетчики
            stock['amount'] -= take_amount
            needed -= take_amount

    return distribution_plan