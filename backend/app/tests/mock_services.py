from app.services import DistanceMatrixService, _ROUTING_CACHE


# --- 1. МОК-СЕРВІС ДЛЯ ІМІТАЦІЇ ЛОГІСТИЧНИХ ВІДСТАНЕЙ (OSRM) ---
class MockDistanceService:
    """Імітація OSRM Table API для ізольованого тестування"""

    def get_distance(self, lat1, lng1, lat2, lng2):
        return 15.0

    def get_distance_matrix(self, sources, destinations):
        import numpy as np
        return np.full((len(sources), len(destinations)), 15.0)
