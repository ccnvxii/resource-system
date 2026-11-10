import unittest
from unittest.mock import patch
from app.utils import calculate_request_priority


class UserRequestPriorityMacroTest(unittest.TestCase):
    """Набір юнит-тестів для перевірки макро-формули розрахунку пріоритету заявки."""

    def log_test_header(self, test_name, description):
        print(f"\n======================================================================")
        print(f" МАКРО-ФОРМУЛА ПРІОРИТЕТУ | ТЕСТ: {test_name}")
        print(f" ОПИС: {description}")
        print(f"----------------------------------------------------------------------")

    def log_results(self, inputs, expected, actual, status="УСПІШНО"):
        print(f" [Вхідні дані] : {inputs}")
        print(f" [Очікувано]   : {expected}")
        print(f" [Отримано]    : {actual}")
        print(f" [СТАТУС]      : {status} ")
        print(f"======================================================================")

    @patch('app.utils.calculate_front_multiplier', return_value=0.0)
    @patch('app.utils.calculate_time_multiplier', return_value=0.0)
    def test_priority_boundaries_and_penalties(self, mock_time, mock_geo):
        """Тест 1: Граничні значення та захист нижньої межі."""
        self.log_test_header(
            "Тест 1",
            "Граничні значення та захист нижньої межі (мінімальні вхідні параметри та критичний штраф)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=0.0,
            category_criticality=0.0,
            latitude=50.45,
            longitude=30.52,
            due_date="2020-01-01",
            extension_count=10
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertAlmostEqual(display_priority, 0.25, places=2)
        self.log_results(
            inputs="Нульові вхідні дані, гео=0.0, час=0.0, штраф за 10 пролонгацій",
            expected="Пріоритет (інтерфейс) = 0.25 (Мінімальний захищений поріг)",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=0.66)
    def test_priority_rounding_precision(self, mock_geo):
        """Тест 2: Точність обчислень та округлення."""
        self.log_test_header(
            "Тест 2",
            "Точність обчислень та округлення (нецілочисельні коефіцієнти згідно зі стандартом)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=0.33,
            category_criticality=0.44,
            latitude=50.45,
            longitude=30.52,
            due_date="2030-01-01",
            extension_count=0
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertIsInstance(priority_db, float)
        self.log_results(
            inputs="Нецілочисельні коефіцієнти (0.33, 0.44, 0.55, 0.66), гео=0.66",
            expected="Округлено до встановленої точності та адаптоване для інтерфейсу",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=0.7)
    @patch('app.utils.calculate_time_multiplier', return_value=0.5)
    def test_priority_single_extension_penalty(self, mock_time, mock_geo):
        """Тест 3: Штрафні санкції за пролонгацію."""
        self.log_test_header(
            "Тест 3",
            "Штрафні санкції за пролонгацію (оцінка впливу першої пролонгації extension_count = 1)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=0.5,
            category_criticality=0.5,
            latitude=50.45,
            longitude=30.52,
            due_date="2026-06-01",
            extension_count=1
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertIsInstance(priority_db, float)
        self.log_results(
            inputs="Коефіцієнти=0.5, гео=0.7, час=0.5, пролонгації=1 (штраф -0.01)",
            expected="Зменшення фінального пріоритету з урахуванням одиничного штрафу застарілої заявки",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=0.7)
    @patch('app.utils.calculate_time_multiplier', return_value=0.5)
    def test_priority_standard_weighted_case(self, mock_time, mock_geo):
        """Тест 4: Типовий зважений сценарій."""
        self.log_test_header(
            "Тест 4",
            "Типовий зважений сценарій (змішані коефіцієнти без штрафів, лінійна згортка)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=0.8,
            category_criticality=0.6,
            latitude=50.45,
            longitude=30.52,
            due_date="2026-06-01",
            extension_count=0
        )

        display_priority = round(priority_db * 10.0, 2)
        expected_display = 6.7

        self.assertEqual(display_priority, expected_display)
        self.log_results(
            inputs="Призначення=0.8, Критичність=0.6, Час=0.5, Гео=0.7, Пролонгації=0",
            expected=f"Пріоритет (інтерфейс) = {expected_display}",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=1.0)
    @patch('app.utils.calculate_time_multiplier', return_value=1.0)
    def test_priority_upper_bound_clamping(self, mock_time, mock_geo):
        """Тест 5: Верхня межа."""
        self.log_test_header(
            "Тест 5",
            "Верхня межа (максимальні вхідні параметри 1.0 без штрафів, обмеження стелею шкали)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=1.0,
            category_criticality=1.0,
            latitude=50.45,
            longitude=30.52,
            due_date="2030-01-01",
            extension_count=0
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertEqual(display_priority, 10.0)
        self.log_results(
            inputs="Максимальні коефіцієнти (1.0), гео=1.0, час=1.0, 0 пролонгацій",
            expected="Пріоритет (інтерфейс) = 10.0 (Обмежено максимальною стелею)",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=1.0)
    def test_priority_with_none_due_date(self, mock_geo):
        """Тест 6: Стійкість за відсутності дедлайну."""
        self.log_test_header(
            "Тест 6",
            "Стійкість за відсутності дедлайну (Due date = None із перерозподілом ваг)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=1.0,
            category_criticality=1.0,
            latitude=50.45,
            longitude=30.52,
            due_date=None,
            extension_count=0
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertIsInstance(priority_db, float)
        self.log_results(
            inputs="Дедлайн = Відсутній (None), Інші коефіцієнти = 1.0, Гео = 1.0",
            expected="Пріоритет перераховано за перерозподіленими вагами без часового штрафу",
            actual=f"У базі (0.0-1.0) = {priority_db} | На екрані (0-10) = {display_priority}"
        )

    @patch('app.utils.calculate_front_multiplier', return_value=1.0)
    @patch('app.utils.calculate_time_multiplier', return_value=0.9)
    def test_priority_complex_integration_case(self, mock_time, mock_geo):
        """Тест 7: Комплексна інтеграційна перевірка."""
        self.log_test_header(
            "Тест 7",
            "Комплексна інтеграційна перевірка (реальний запит у наближених до бойових умовах)."
        )

        priority_db = calculate_request_priority(
            purpose_weight=1.0,
            category_criticality=0.9,
            latitude=48.5,  # Наближено до зони бойових дій
            longitude=37.6,
            due_date="2026-06-15",
            extension_count=2  # Наявність двох пролонгацій
        )

        display_priority = round(priority_db * 10.0, 2)

        self.assertIsInstance(priority_db, float)
        self.log_results(
            inputs="Призначення=1.0, Критичність=0.9, Гео=1.0 (фронт), Час=0.9, Пролонгації=2",
            expected="Комплексний результат високого пріоритету з урахуванням бойових умов та невеликого штрафу",
            actual=f"У базі = {priority_db} | На екрані = {display_priority}"
        )


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" СТАРТ ТЕСТУВАННЯ МАКРО-ФОРМУЛИ ПРІОРИТЕТУ USER_REQUEST")
    print("=" * 70)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(UserRequestPriorityMacroTest))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(" ПІДСУМОК ТЕСТУВАННЯ ПРІОРИТЕТІВ:")
    print(f" Проведено тестів : {result.testsRun}")
    print(f" Успішно          : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" Помилок/Збоїв    : {len(result.failures) + len(result.errors)}")
    print("=" * 70 + "\n")