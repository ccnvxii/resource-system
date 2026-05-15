import requests

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
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.novaposhta.ua/v2.0/json/"

    def _send_request(self, model, method, properties):
        payload = {
            "apiKey": self.api_key,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": properties
        }
        try:
            response = requests.post(self.url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            return {"success": False, "errors": [str(e)], "data": []}

    def get_cities(self, search_text=""):
        return self._send_request(
            model="Address",
            method="searchSettlements",
            properties={"CityName": search_text, "Limit": "20"}
        )

    def get_warehouses(self, settlement_ref):
        return self._send_request(
            model="Address",
            method="getWarehouses",
            properties={"SettlementRef": settlement_ref}
        )

    def get_streets(self, settlement_ref, search_text):
        return self._send_request(
            model="Address",
            method="searchSettlementStreets",
            properties={
                "StreetName": search_text,
                "SettlementRef": settlement_ref,
                "Limit": "50"
            }
        )

    def get_warehouse_coordinates(self, warehouse_ref):
        """Отримує координати конкретного відділення за його Ref."""
        payload = {
            "apiKey": self.api_key,
            "modelName": "Address",
            "calledMethod": "getWarehouses",
            "methodProperties": {
                "Ref": warehouse_ref
            }
        }
        try:
            response = requests.post(self.url, json=payload, timeout=10)
            data = response.json()
            if data.get('success') and data.get('data'):
                wh = data['data'][0]
                return float(wh.get('Latitude', 0)), float(wh.get('Longitude', 0))
        except Exception as e:
            print(f"NP Coords Error: {e}")
        return None, None

