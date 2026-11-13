"""Спільні допоміжні класи та функції для тестів (підміни зовнішніх сервісів, генератори даних)."""
import random

import numpy as np


class FakeFront:
    """Підміна GeoFrontService: детермінована лінія фронту без мережевих запитів."""
    points = [(50.0, 36.0)]

    def get_front_line_points(self):
        return list(self.points)


class FlatRouting:
    """Однакова відстань між усіма точками (ізолює розподіл від географії)."""

    def get_distance(self, *args):
        return 10.0

    def get_distance_matrix(self, sources, destinations):
        return np.full((len(sources), len(destinations)), 10.0)


class EuclidRouting:
    """Детермінована евклідова відстань за координатами."""

    def get_distance(self, lat1, lng1, lat2, lng2):
        if lat1 is None or lat2 is None:
            return 10.0
        return float(np.hypot(lat1 - lat2, lng1 - lng2))

    def get_distance_matrix(self, sources, destinations):
        m = np.zeros((len(sources), len(destinations)))
        for i, s in enumerate(sources):
            for j, d in enumerate(destinations):
                m[i, j] = self.get_distance(s['lat'], s['lng'], d['lat'], d['lng'])
        return m


def random_instance(rng, n_res=2, max_wh=4, max_req=8):
    """Випадковий набір складів і заявок (для перевірки інваріантів)."""
    stocks, requests, rid = [], [], 1
    for res in range(1, n_res + 1):
        for wh in range(rng.randint(1, max_wh)):
            stocks.append({
                'resource_id': res, 'warehouse_id': f'w{res}_{wh}', 'amount': rng.randint(0, 60),
                'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12,
            })
        for _ in range(rng.randint(1, max_req)):
            requests.append({
                'id': rid, 'resource_id': res, 'amount_needed': rng.randint(1, 80),
                'priority': round(rng.uniform(0.1, 1.0), 2),
                'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12,
            })
            rid += 1
    return stocks, requests


def make_instance(n_requests, n_warehouses=4, seed=1):
    """Один ресурс, дефіцит: зручно для вимірювання часу розрахунку."""
    rng = random.Random(seed)
    stocks = [{
        'resource_id': 1, 'warehouse_id': w, 'amount': n_requests * 2,
        'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12,
    } for w in range(n_warehouses)]
    requests = [{
        'id': i, 'resource_id': 1, 'amount_needed': rng.randint(1, 30), 'priority': rng.uniform(0.1, 1.0),
        'lat': 48 + rng.random() * 3, 'lng': 24 + rng.random() * 12,
    } for i in range(n_requests)]
    return stocks, requests


def check_invariants(test, plan, stocks, requests):
    """Інваріанти будь-якого плану: не більше запасу складу, не більше потреби, ресурс збігається."""
    wh_res = {s['warehouse_id']: s['resource_id'] for s in stocks}
    req_res = {r['id']: r['resource_id'] for r in requests}
    by_req, by_wh = {}, {}
    for item in plan:
        test.assertGreater(item['amount'], 0)
        test.assertEqual(wh_res[item['warehouse_id']], req_res[item['request_id']])
        by_req[item['request_id']] = by_req.get(item['request_id'], 0) + item['amount']
        by_wh[item['warehouse_id']] = by_wh.get(item['warehouse_id'], 0) + item['amount']
    needed = {r['id']: r['amount_needed'] for r in requests}
    amount = {s['warehouse_id']: s['amount'] for s in stocks}
    for rid, got in by_req.items():
        test.assertLessEqual(got, needed[rid] + 1e-6, f'заявка {rid} отримала більше потреби')
    for wid, used in by_wh.items():
        test.assertLessEqual(used, amount[wid] + 1e-6, f'склад {wid} віддав більше за запас')


def allocated_by_request(plan):
    """{request_id: сумарно виділено}."""
    out = {}
    for item in plan:
        out[item['request_id']] = out.get(item['request_id'], 0) + item['amount']
    return out
