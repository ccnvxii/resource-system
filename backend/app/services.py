import requests

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
        """Пошук населеного пункту для отримання SettlementRef"""
        return self._send_request(
            model="Address",
            method="searchSettlements",
            properties={"CityName": search_text, "Limit": "20"}
        )

    def get_warehouses(self, settlement_ref):
        """Отримання відділень за SettlementRef"""
        return self._send_request(
            model="Address",
            method="getWarehouses",
            properties={"SettlementRef": settlement_ref}
        )

    def get_streets(self, settlement_ref, search_text):
        """Пошук вулиць у населеному пункті"""
        return self._send_request(
            model="Address",
            method="searchSettlementStreets",
            properties={
                "StreetName": search_text,
                "SettlementRef": settlement_ref,
                "Limit": "50"
            }
        )