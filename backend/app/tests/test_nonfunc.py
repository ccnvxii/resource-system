import time
from concurrent.futures import ThreadPoolExecutor
from django.test import TransactionTestCase
from django.db import connection


class NonFunctionalLoadTests(TransactionTestCase):
    """Нефункціональні тести продуктивності та навантаження API"""

    reset_sequences = True

    def test_concurrent_api_load_performance(self):
        """Стрес-тест: паралельне виконання запитів до API з вимірюванням часу"""
        url = '/api/resources/'

        def make_request():
            # Важливо: закриваємо з'єднання в кінці потоку, щоб уникнути блокування БД
            try:
                response = self.client.get(url)
                return response.status_code
            finally:
                connection.close()

        t_start = time.time()
        # Запускаємо 20 паралельних потоків
        with ThreadPoolExecutor(max_workers=5) as executor:
            status_codes = list(executor.map(lambda _: make_request(), range(20)))

        duration = time.time() - t_start

        # Перевірки
        for code in status_codes:
            self.assertEqual(code, 200)

        self.assertLess(duration, 3.0, "Час обробки паралельних запитів перевищує норму")
        print(f"\n[УСПІХ] 20 паралельних запитів опрацьовано за {duration:.4f} с")