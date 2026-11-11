import requests as req_lib
from unittest.mock import patch
from django.test import TestCase

from app.services import DistanceMatrixService, _ROUTING_CACHE


class RoutingServiceTests(TestCase):
    """Тести для OSRM Table API, локального кешування та фолбеків"""

    def setUp(self):
        _ROUTING_CACHE.clear()

    @patch('app.services.requests.get')
    def test_osrm_table_api_single_request(self, mock_get):
        """Перевірка виклику Table API рівно 1 раз для всієї матриці (вирішення проблеми N+1)"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [[10000.0, 20000.0], [30000.0, 40000.0]]
        }

        service = DistanceMatrixService()
        stocks = [{'lat': 50.45, 'lng': 30.52}, {'lat': 49.84, 'lng': 24.03}]
        requests = [{'lat': 50.00, 'lng': 36.23}, {'lat': 46.48, 'lng': 30.73}]

        matrix = service.get_distance_matrix(stocks, requests)

        self.assertEqual(matrix.shape, (2, 2))
        self.assertAlmostEqual(matrix[0, 0], 10.0)
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_in_memory_cache_prevents_duplicate_calls(self, mock_get):
        """Перевірка роботи ін-меморі кешу: при повторному запиті HTTP не викликається"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'code': 'Ok',
            'distances': [[12000.0]]
        }

        service = DistanceMatrixService()
        stocks = [{'lat': 50.450, 'lng': 30.520}]
        requests = [{'lat': 50.000, 'lng': 36.230}]

        service.get_distance_matrix(stocks, requests)
        self.assertEqual(mock_get.call_count, 1)

        # Повторний запит неподалік (має взятися з кешу)
        service.get_distance_matrix([{'lat': 50.4502, 'lng': 30.5204}], [{'lat': 50.0003, 'lng': 36.2301}])
        self.assertEqual(mock_get.call_count, 1)

    @patch('app.services.requests.get')
    def test_fallback_to_geometry_on_network_error(self, mock_get):
        """Перевірка спрацювання геометричного фолбеку при збої мережі OSRM"""
        mock_get.side_effect = req_lib.RequestException("Network timeout")

        service = DistanceMatrixService()
        stocks = [{'lat': 50.0, 'lng': 30.0}]
        requests = [{'lat': 51.0, 'lng': 31.0}]

        matrix = service.get_distance_matrix(stocks, requests)
        self.assertGreater(matrix[0, 0], 0.0)

    def test_missing_coordinates_penalty(self):
        """Перевірка повернення штрафної відстані (500 км) при відсутності координат"""
        service = DistanceMatrixService()
        stocks = [{'lat': None, 'lng': 30.0}]
        requests = [{'lat': 50.0, 'lng': None}]

        matrix = service.get_distance_matrix(stocks, requests)
        self.assertEqual(matrix[0, 0], 500.0)
