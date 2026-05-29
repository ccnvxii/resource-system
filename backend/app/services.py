import time
import math
import requests
import googlemaps

# Внутрішній локальний кеш для уникнення дублювання запитів під час роботи симплекс-методу
_ROUTING_CACHE = {}


class DistanceMatrixService:
    def __init__(self):
        # Твій робочий API ключ із Google Cloud Maps Platform
        self.google_key = "AIzaSyDR8L5DEC1oCb9eOhg6ZERNVQZMoeABNU0"

        try:
            self.gmaps_client = googlemaps.Client(key=self.google_key)
        except Exception as e:
            print(f"[DistanceMatrixService] Клієнт Google Maps не ініціалізовано: {e}")
            self.gmaps_client = None

    def get_distance(self, lat1, lng1, lat2, lng2):
        """
        Повертає реальну автомобільну відстань між двома точками в кілометрах.
        Каскадна стратегія: Google Maps API -> Безкоштовний OSRM API -> Евклідовий фолбек.
        """
        if None in (lat1, lng1, lat2, lng2):
            return 500.0  # Стандартний штрафний коефіцієнт системи при відсутності координат

        # Формуємо ключ для кешування (округлення до 4 знаків для стабільності)
        cache_key = (round(float(lat1), 4), round(float(lng1), 4), round(float(lat2), 4), round(float(lng2), 4))
        if cache_key in _ROUTING_CACHE:
            return _ROUTING_CACHE[cache_key]

        # --- СТРАТЕГІЯ 1: GOOGLE MAPS API (Режим Driving) ---
        if self.gmaps_client:
            try:
                origins = f"{lat1},{lng1}"
                destinations = f"{lat2},{lng2}"

                matrix = self.gmaps_client.distance_matrix(
                    origins=origins,
                    destinations=destinations,
                    mode="driving"
                )

                element = matrix['rows'][0]['elements'][0]
                if element.get('status') == 'OK':
                    distance_km = element['distance']['value'] / 1000.0
                    _ROUTING_CACHE[cache_key] = distance_km
                    return distance_km
                else:
                    print(f"[Google API] Статус відповіді NOT OK: {element.get('status')}. Спроба через OSRM...")
            except Exception as e:
                print(f"[Google API] Помилка запиту ({e}). Перемикання на OSRM...")

        # --- СТРАТЕГІЯ 2: БЕЗКОШТОВНИЙ СЕРВЕР OSRM (OPENSTREETMAP) ---
        try:
            # Важливо: OSRM приймає параметри у форматі (longitude, latitude)
            url = f"http://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=false"
            response = requests.get(url, timeout=2.0)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok':
                    distance_km = data['routes'][0]['distance'] / 1000.0
                    _ROUTING_CACHE[cache_key] = distance_km
                    return distance_km
        except Exception as e:
            print(f"[OSRM API] Помилка безкоштовного сервера ({e}). Розрахунок геометрії...")

        # --- СТРАТЕГІЯ 3: МАТЕМАТИЧНИЙ ГЕОМЕТРИЧНИЙ ФОЛБЕК (Автономний режим) ---
        # 1 градус широти ≈ 111 км, 1 градус довготи ≈ 73 км в шикротах України
        dx = (float(lng2) - float(lng1)) * 73.0
        dy = (float(lat2) - float(lat1)) * 111.0
        # 1.25 — середній коефіцієнт звивистості автомобільних доріг порівняно з прямою лінією
        fallback_distance = math.sqrt(dx ** 2 + dy ** 2) * 1.25

        _ROUTING_CACHE[cache_key] = fallback_distance
        return fallback_distance


class GeoFrontService:
    def __init__(self):
        # Приклад REST API ендпоінту ArcGIS (публічний шар моніторингу фронту)
        self.url = "https://services.arcgis.com/..."

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
    def __init__(self, api_key: str):
        self.api_key = api_key
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