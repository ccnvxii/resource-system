import time
import math
import requests
import googlemaps
import numpy as np
from django.conf import settings  # Імпортуємо глобальні налаштування Django

# Внутрішній локальний кеш для уникнення дублювання запитів під час роботи симплекс-методу
# Ключ: (round(lat1, 3), round(lng1, 3), round(lat2, 3), round(lng2, 3))
_ROUTING_CACHE = {}


class DistanceMatrixService:
    def __init__(self, cache=None, base_url=None, timeout=3.0, max_batch_size=80):
        self.cache = cache if cache is not None else _ROUTING_CACHE
        self.base_url = (base_url or getattr(settings, "OSRM_BASE_URL", "http://router.project-osrm.org")).rstrip('/')
        self.timeout = timeout
        self.max_batch_size = max_batch_size

    @staticmethod
    def _extract_coords(point):
        """Витягує (lat, lng) зі словника, кортежу/списку або об'єкта."""
        if point is None:
            return None, None
        if isinstance(point, dict):
            return point.get('lat'), point.get('lng')
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            return point[0], point[1]
        if hasattr(point, 'lat') and hasattr(point, 'lng'):
            return getattr(point, 'lat'), getattr(point, 'lng')
        return None, None

    @staticmethod
    def _make_cache_key(lat1, lng1, lat2, lng2):
        """Формує ключ кешу на основі округлених до 3 знаків координат."""
        try:
            return (
                round(float(lat1), 3),
                round(float(lng1), 3),
                round(float(lat2), 3),
                round(float(lng2), 3),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def compute_fallback_distance(lat1, lng1, lat2, lng2):
        """
        Математичний геометричний фолбек (Автономний режим).
        Штрафний коефіцієнт 500.0 км при відсутності координат.
        """
        if None in (lat1, lng1, lat2, lng2):
            return 500.0
        try:
            dx = (float(lng2) - float(lng1)) * 73.0
            dy = (float(lat2) - float(lat1)) * 111.0
            return math.sqrt(dx ** 2 + dy ** 2) * 1.25
        except (TypeError, ValueError):
            return 500.0

    def get_distance(self, lat1, lng1, lat2, lng2):
        """
        Повертає реальну автомобільну відстань між двома точками в кілометрах.
        Каскадна стратегія: Локальний кеш -> Безкоштовний OSRM Table API -> Математичний фолбек.
        """
        if None in (lat1, lng1, lat2, lng2):
            return 500.0

        cache_key = self._make_cache_key(lat1, lng1, lat2, lng2)
        if cache_key and cache_key in self.cache:
            return self.cache[cache_key]

        matrix = self.get_distance_matrix([(lat1, lng1)], [(lat2, lng2)])
        return float(matrix[0, 0])

    def get_distance_matrix(self, sources, destinations):
        """
        Повертає 2D матрицю (numpy array) реальних автомобільних відстаней (км) між джерелами (sources)
        та призначеннями (destinations).

        Замість N*M окремих запитів (проблема N+1) використовує OSRM Table API (Distance Matrix API).
        Він приймає масив координат джерел і призначень та повертає готову матрицю за один HTTP-запит
        (або декілька пакетних запитів, якщо розмір перевищує ліміт URL/сервера).
        
        Усі результати кешуються в in-memory кеші з ключем:
        cache[(round(lat1, 3), round(lng1, 3), round(lat2, 3), round(lng2, 3))].
        """
        n_stk = len(sources)
        n_req = len(destinations)

        if n_stk == 0 or n_req == 0:
            return np.zeros((n_stk, n_req), dtype=float)

        dist_matrix = np.zeros((n_stk, n_req), dtype=float)

        src_coords = [self._extract_coords(s) for s in sources]
        dst_coords = [self._extract_coords(d) for d in destinations]

        # 1. Попередній прохід: перевірка in-memory кешу та обробка відсутніх координат
        unresolved_pairs = set()
        for i, (lat1, lng1) in enumerate(src_coords):
            for j, (lat2, lng2) in enumerate(dst_coords):
                if None in (lat1, lng1, lat2, lng2):
                    dist_matrix[i, j] = 500.0
                    continue

                key = self._make_cache_key(lat1, lng1, lat2, lng2)
                if key and key in self.cache:
                    dist_matrix[i, j] = self.cache[key]
                else:
                    unresolved_pairs.add((i, j))

        if not unresolved_pairs:
            return dist_matrix

        # 2. Пакетні виклики OSRM Table API з урахуванням ліміту точок на один запит
        max_src = min(n_stk, 40)
        max_dst = max(1, self.max_batch_size - max_src)

        for src_start in range(0, n_stk, max_src):
            src_end = min(src_start + max_src, n_stk)
            src_slice = list(range(src_start, src_end))

            for dst_start in range(0, n_req, max_dst):
                dst_end = min(dst_start + max_dst, n_req)
                dst_slice = list(range(dst_start, dst_end))

                block_needed = any((i, j) in unresolved_pairs for i in src_slice for j in dst_slice)
                if not block_needed:
                    continue

                self._fetch_table_block(
                    dist_matrix,
                    src_coords,
                    dst_coords,
                    src_slice,
                    dst_slice,
                    unresolved_pairs
                )

        return dist_matrix

    def _fetch_table_block(self, dist_matrix, src_coords, dst_coords, src_slice, dst_slice, unresolved_pairs):
        """Виконує один OSRM Table API запит для пакету джерел і призначень з каскадним фолбеком."""
        valid_coords = True
        src_points = []
        for i in src_slice:
            lat, lng = src_coords[i]
            if lat is None or lng is None:
                valid_coords = False
                break
            src_points.append((lat, lng))

        dst_points = []
        if valid_coords:
            for j in dst_slice:
                lat, lng = dst_coords[j]
                if lat is None or lng is None:
                    valid_coords = False
                    break
                dst_points.append((lat, lng))

        success = False
        if valid_coords:
            try:
                # OSRM очікує формат: longitude,latitude через крапку з комою
                all_coords_str = ";".join(
                    [f"{float(lng):.6f},{float(lat):.6f}" for lat, lng in src_points] +
                    [f"{float(lng):.6f},{float(lat):.6f}" for lat, lng in dst_points]
                )
                sources_idx_str = ";".join(str(idx) for idx in range(len(src_points)))
                dests_idx_str = ";".join(str(len(src_points) + idx) for idx in range(len(dst_points)))

                url = (
                    f"{self.base_url}/table/v1/driving/{all_coords_str}"
                    f"?sources={sources_idx_str}&destinations={dests_idx_str}&annotations=distance"
                )

                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 'Ok' and 'distances' in data:
                        distances = data['distances']
                        for si, orig_i in enumerate(src_slice):
                            for dj, orig_j in enumerate(dst_slice):
                                val = distances[si][dj]
                                lat1, lng1 = src_coords[orig_i]
                                lat2, lng2 = dst_coords[orig_j]
                                key = self._make_cache_key(lat1, lng1, lat2, lng2)

                                if val is not None:
                                    dist_km = float(val) / 1000.0
                                else:
                                    dist_km = self.compute_fallback_distance(lat1, lng1, lat2, lng2)

                                dist_matrix[orig_i, orig_j] = dist_km
                                if key:
                                    self.cache[key] = dist_km
                                unresolved_pairs.discard((orig_i, orig_j))

                        success = True
                        print(f"[SUCCESS] [OSRM Table API] Отримано матрицю {len(src_slice)}x{len(dst_slice)}")
                    else:
                        print(f"[OSRM Table API] Сервер повернув код: {data.get('code')}. Використовується фолбек...")
                else:
                    print(f"[OSRM Table API] Помилка сервера (Статус {response.status_code}). Використовується фолбек...")
            except Exception as e:
                print(f"[OSRM Table API] Помилка мережевого запиту ({e}). Розрахунок геометрії...")

        # Якщо запит не вдався (або координати невалідні), обчислюємо геометричний фолбек
        if not success:
            for orig_i in src_slice:
                for orig_j in dst_slice:
                    if (orig_i, orig_j) in unresolved_pairs:
                        lat1, lng1 = src_coords[orig_i]
                        lat2, lng2 = dst_coords[orig_j]
                        dist_km = self.compute_fallback_distance(lat1, lng1, lat2, lng2)
                        dist_matrix[orig_i, orig_j] = dist_km
                        key = self._make_cache_key(lat1, lng1, lat2, lng2)
                        if key:
                            self.cache[key] = dist_km
                        unresolved_pairs.discard((orig_i, orig_j))


class GeoFrontService:
    def __init__(self):
        self.url = getattr(settings, "ARCGIS_FRONT_LINE_URL", "https://services.arcgis.com/...")

    def get_front_line_points(self):
        """
        Отримує геометрію лінії фронту через REST API ArcGIS.
        """
        params = {
            'where': '1=1',
            'outFields': '*',   
            'f': 'geojson',
            'resultType': 'standard'
        }
        try:
            response = requests.get(self.url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                points = []
                # Витягуємо координати з MultiLineString або LineString
                for feature in data.get('features', []):
                    geometry = feature.get('geometry', {})
                    if geometry.get('type') in ['LineString', 'MultiLineString']:
                        coords = geometry.get('coordinates')
                        self._extract_coords(coords, points)
                return points if points else self._get_fallback_points()
            return self._get_fallback_points()
        except Exception as e:
            print(f"ArcGIS API Error: {e}")
            return self._get_fallback_points()

    def _extract_coords(self, coords, result_list):
        for item in coords:
            if isinstance(item[0], (int, float)):
                result_list.append((item[1], item[0]))
            else:
                self._extract_coords(item, result_list)

    def _get_fallback_points(self):
        return [(49.95, 36.85), (48.45, 37.95), (47.85, 36.65), (46.65, 32.61)]


class NovaPoshtaService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "NOVA_POSHTA_API_KEY", "")
        self.url = "https://api.novaposhta.ua/v2.0/json/"

    def _request(self, model, method, props):
        payload = {
            "apiKey": self.api_key,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": props,
        }
        response = requests.post(self.url, json=payload, timeout=15)
        return response.json()

    def _safe_request(self, model, method, props, retries=3):
        last = None
        for i in range(retries):
            try:
                data = self._request(model, method, props)
                last = data

                if data.get("success") is False:
                    time.sleep(0.5 * (i + 1))
                    continue
                return data
            except Exception as e:
                print(f"NP ERROR: {e}")
                time.sleep(0.5 * (i + 1))
        return last or {"success": False, "data": []}

    def get_cities(self, search):
        return self._safe_request(
            "Address", "searchSettlements",
            {"CityName": search, "Limit": 20}
        )

    def get_warehouses(self, city_ref):
        return self._safe_request(
            "Address", "getWarehouses",
            {"SettlementRef": city_ref}
        )

    def get_streets(self, settlement_ref, search):
        return self._safe_request(
            "Address",
            "searchSettlementStreets",
            {
                "SettlementRef": settlement_ref,
                "StreetName": search,
                "Limit": 50
            }
        )

    def get_warehouse_coordinates(self, warehouse_ref):
        """ Отримуємо координати конкретного відділення за його унікальним Ref """
        try:
            data = self._safe_request(
                "Address", "getWarehouses",
                {"Ref": warehouse_ref}
            )
            if data.get('success') and data.get('data'):
                wh = data['data'][0]
                return float(wh.get('Latitude', 0)), float(wh.get('Longitude', 0))
        except Exception as e:
            print(f"Помилка парсингу координат НП: {e}")
        return None, None
