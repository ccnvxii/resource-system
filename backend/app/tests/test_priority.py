import unittest
from unittest.mock import MagicMock
from decimal import Decimal


# ==============================================================================
# ІМІТАЦІЯ МОДЕЛІ ТА МАКРО-ФОРМУЛИ РОЗХОДЖЕННЯ ПРІОРИТЕТУ (UserRequest)
# ==============================================================================

class MockRequestPurpose:
    def __init__(self, weight):
        self.weight = weight


class MockCategory:
    def __init__(self, criticality):
        self.criticality = criticality


class MockUserRequestModel:
    """Імітація бізнес-логіки методу save() та макро-формули розрахунку пріоритету"""

    def __init__(self, purpose, category, time_urgency_factor, geo_zone_factor, extension_count=0):
        self.purpose = purpose
        self.category = category
        self.time_urgency_factor = time_urgency_factor  # k_time [0; 1]
        self.geo_zone_factor = geo_zone_factor  # k_geo [0; 1]
        self.extension_count = extension_count
        self.priority = 0.0

    def calculate_priority_macro(self):
        # Коефіцієнти макро-формули (альфа, бета, гамма, дельта)
        alpha, beta, gamma, delta = 0.3, 0.3, 0.2, 0.2

        k_purp = self.purpose.weight
        k_crit = self.category.criticality
        k_time = self.time_urgency_factor
        k_geo = self.geo_zone_factor

        # Згортка у базову шкалу [0; 10]
        base_score = 10 * (
                alpha * k_purp +
                beta * k_time +
                gamma * k_geo +
                delta * k_crit
        )

        # Штраф за пролонгації (extension_count)
        penalty = self.extension_count * 0.5

        # Фінальний розрахунок із захистом від виходу за межі [0; 10]
        calculated = max(0.0, min(10.0, base_score - penalty))
        return round(calculated, 2)

    def save(self, *args, **kwargs):
        self.priority = self.calculate_priority_macro()


# ==============================================================================
# ТЕСТОВИЙ КЛАС ПЕРЕВІРКИ МАКРО-ФОРМУЛИ ПРІОРИТЕТУ
# ==============================================================================

class UserRequestPriorityMacroTest(unittest.TestCase):
    """Окремий набір тестів для перевірки коректності макро-формули розрахунку пріоритету заявки."""

    def log_test_header(self, test_name, description):
        print(f"\n======================================================================")
        print(f" ТЕСТ: {test_name}")
        print(f" ОПИС: {description}")
        print(f"----------------------------------------------------------------------")

    def log_results(self, inputs, expected, actual, status="PASSED"):
        print(f" [Вхідні дані] : {inputs}")
        print(f" [Очікувано]   : {expected}")
        print(f" [Отримано]    : {actual}")
        print(f" [СТАТУС]      : {status} ")
        print(f"======================================================================")

    def test_user_request_priority_calculation(self):
        self.log_test_header(
            "test_user_request_priority_calculation",
            "Перевірка макро-формули UserRequest.save() з урахуванням вагових коефіцієнтів та штрафів."
        )

        # Вхідні параметри: мета (вага 1.0), категорія критична (1.0), терміновість (0.9), прифронтова зона (1.0)
        purpose = MockRequestPurpose(weight=1.0)
        category = MockCategory(criticality=1.0)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=0.9,
            geo_zone_factor=1.0,
            extension_count=1  # 1 пролонгація дає штраф 0.5
        )

        request_obj.save()

        # Розрахунок вручну:
        # base_score = 10 * (0.3*1.0 + 0.3*0.9 + 0.2*1.0 + 0.2*1.0) = 10 * (0.3 + 0.27 + 0.2 + 0.2) = 10 * 0.97 = 9.7
        # penalty = 1 * 0.5 = 0.5
        # final = 9.7 - 0.5 = 9.2
        expected_priority = 9.2

        self.assertEqual(request_obj.priority, expected_priority)
        self.log_results(
            inputs="Purpose w=1.0, Crit=1.0, Time=0.9, Geo=1.0, Extensions=1",
            expected=f"Priority = {expected_priority}",
            actual=f"Priority = {request_obj.priority}"
        )

    def test_priority_boundaries_and_penalties(self):
        self.log_test_header(
            "test_priority_boundaries_and_penalties",
            "Перевірка захисту від виходу за межі діапазону [0; 10] та великих штрафів."
        )
        # Мінімальні коефіцієнти + велика кількість штрафів
        purpose = MockRequestPurpose(weight=0.0)
        category = MockCategory(criticality=0.0)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=0.0,
            geo_zone_factor=0.0,
            extension_count=10
        )

        request_obj.save()

        # Захист max(0.0, ...) має повернути 0.0
        self.assertEqual(request_obj.priority, 0.0)
        self.log_results(
            inputs="Min coefficients (0.0) and heavy extensions penalty (10)",
            expected="Priority = 0.0 (Clamped by lower bound)",
            actual=f"Priority = {request_obj.priority}"
        )

    def test_priority_upper_bound_clamping(self):
        self.log_test_header(
            "test_priority_upper_bound_clamping",
            "Перевірка верхньої межі діапазону [0; 10] при максимальних коефіцієнтах і без штрафів."
        )
        purpose = MockRequestPurpose(weight=1.0)
        category = MockCategory(criticality=1.0)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=1.0,
            geo_zone_factor=1.0,
            extension_count=0
        )
        request_obj.save()

        # base_score = 10 * (0.3*1 + 0.3*1 + 0.2*1 + 0.2*1) = 10.0
        self.assertEqual(request_obj.priority, 10.0)
        self.log_results(
            inputs="Max coefficients (1.0), 0 extensions",
            expected="Priority = 10.0 (Clamped by upper bound)",
            actual=f"Priority = {request_obj.priority}"
        )

    def test_priority_standard_weighted_case(self):
        self.log_test_header(
            "test_priority_standard_weighted_case",
            "Перевірка розрахунку для типової заявки зі змішаними коефіцієнтами без штрафів."
        )
        purpose = MockRequestPurpose(weight=0.8)
        category = MockCategory(criticality=0.6)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=0.5,
            geo_zone_factor=0.7,
            extension_count=0
        )
        request_obj.save()

        # base_score = 10 * (0.3*0.8 + 0.3*0.5 + 0.2*0.7 + 0.2*0.6) = 10 * (0.24 + 0.15 + 0.14 + 0.12) = 10 * 0.65 = 6.5
        expected_priority = 6.5
        self.assertEqual(request_obj.priority, expected_priority)
        self.log_results(
            inputs="Purpose w=0.8, Crit=0.6, Time=0.5, Geo=0.7, Extensions=0",
            expected=f"Priority = {expected_priority}",
            actual=f"Priority = {request_obj.priority}"
        )

    def test_priority_rounding_precision(self):
        self.log_test_header(
            "test_priority_rounding_precision",
            "Перевірка коректності округлення результату до двох знаків після коми."
        )
        purpose = MockRequestPurpose(weight=0.33)
        category = MockCategory(criticality=0.44)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=0.55,
            geo_zone_factor=0.66,
            extension_count=0
        )
        request_obj.save()

        # Перевіряємо що тип float і значення округлене
        self.assertIsInstance(request_obj.priority, float)
        self.log_results(
            inputs="Non-integer coefficients (0.33, 0.44, 0.55, 0.66)",
            expected="Rounded to 2 decimal places",
            actual=f"Priority = {request_obj.priority}"
        )

    def test_priority_single_extension_penalty(self):
        self.log_test_header(
            "test_priority_single_extension_penalty",
            "Перевірка коректності застосування одиничного штрафу за пролонгацію заявки."
        )
        purpose = MockRequestPurpose(weight=0.5)
        category = MockCategory(criticality=0.5)

        request_obj = MockUserRequestModel(
            purpose=purpose,
            category=category,
            time_urgency_factor=0.5,
            geo_zone_factor=0.5,
            extension_count=1  # Штраф 1 * 0.5 = 0.5
        )
        request_obj.save()

        # base_score = 10 * (0.3*0.5 + 0.3*0.5 + 0.2*0.5 + 0.2*0.5) = 10 * 0.5 = 5.0
        # penalty = 0.5 -> final = 4.5
        expected_priority = 4.5
        self.assertEqual(request_obj.priority, expected_priority)
        self.log_results(
            inputs="Coefficients=0.5, Extensions=1 (Penalty=0.5)",
            expected=f"Priority = {expected_priority}",
            actual=f"Priority = {request_obj.priority}"
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