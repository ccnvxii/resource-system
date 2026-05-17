import time
import requests


class GeoFrontService:
    def __init__(self):
        # Пример REST API эндпоинта ArcGIS (публичный слой мониторинга фронта)
        self.url = "https://services.arcgis.com/..."  # Здесь вставляется конкретный URL слоя

    def get_front_line_points(self):
        """
        Получает геометрию линии фронта через REST API ArcGIS.
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
                # Извлекаем координаты из MultiLineString или LineString
                for feature in data.get('features', []):
                    geometry = feature.get('geometry', {})
                    if geometry.get('type') in ['LineString', 'MultiLineString']:
                        coords = geometry.get('coordinates')
                        # Обработка вложенности координат
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
            except Exception:
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

    def get_streets(self, city_ref, search):
        return self._safe_request(
            "Address", "searchSettlementStreets",
            {"SettlementRef": city_ref, "StreetName": search, "Limit": 50}
        )

    def get_warehouse_coordinates(self, warehouse_ref):
        """ПРАВИЛЬНИЙ PRODUCTION FIX: Отримуємо координати конкретного відділення за його унікальним Ref"""
        try:
            data = self._safe_request(
                "Address", "getWarehouses",
                {"Ref": warehouse_ref}
            )
            if data.get('success') and data.get('data'):
                wh = data['data'][0]
                return float(wh.get('Latitude', 0)), float(wh.get('Longitude', 0))
        except Exception as e:
            print(f"🚨 Помилка парсингу координат НП: {e}")
        return None, None