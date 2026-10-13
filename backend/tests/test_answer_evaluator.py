
import unittest

from app.ai.answer_evaluator import evaluate_answer, normalize_text


class TestAnswerEvaluator(unittest.TestCase):

    def test_normalize_vietnamese_text(self):
        self.assertEqual(
            normalize_text("Cơ sở dữ liệu"),
            normalize_text("Co so du lieu"),
        )

    def test_empty_answer_raises_error(self):
        with self.assertRaises(ValueError):
            evaluate_answer("")

    def test_empty_expected_points_returns_zero(self):
        result = evaluate_answer(
            "Một câu trả lời có ví dụ thực tế",
            [],
        )

        self.assertEqual(result["total_score"], 0.0)
        self.assertEqual(result["matched_points"], [])
        self.assertEqual(result["missing_points"], [])

    def test_matching_criteria_are_reported(self):
        result = evaluate_answer(
            "Tôi giải thích khái niệm và đưa ra ví dụ thực tế.",
            [
                "Giải thích khái niệm",
                "Đưa ra ví dụ thực tế",
                "Giải thích cách kiểm thử",
            ],
        )

        self.assertEqual(len(result["matched_points"]), 2)
        self.assertEqual(len(result["missing_points"]), 1)

    def test_score_is_between_zero_and_one_hundred(self):
        result = evaluate_answer(
            "Tôi giải thích khái niệm và đưa ra ví dụ thực tế.",
            [
                "Giải thích khái niệm",
                "Đưa ra ví dụ thực tế",
            ],
        )

        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)

    def test_feedback_is_returned(self):
        result = evaluate_answer(
            "Tôi giải thích khái niệm.",
            ["Giải thích khái niệm", "Đưa ra ví dụ thực tế"],
        )

        self.assertTrue(result["feedback"])
        self.assertIsInstance(result["improvements"], list)

    def test_correct_vietnamese_answer_scores_above_irrelevant_answer(self):
        expected = [
            "A decorator modifies the behavior of another function "
            "without changing its source code.",
            "Decorators are commonly used for logging and authentication.",
        ]

        correct = evaluate_answer(
            "Decorator cho phép bổ sung hành vi cho một hàm mà không "
            "phải sửa trực tiếp mã nguồn của hàm đó. Ví dụ, decorator "
            "có thể kiểm tra quyền đăng nhập trước khi gọi chức năng.",
            expected,
        )

        irrelevant = evaluate_answer(
            "Python là ngôn ngữ phổ biến. Tôi từng xây dựng ứng dụng "
            "web, làm việc với cơ sở dữ liệu và triển khai API.",
            expected,
        )

        self.assertGreater(
            correct["total_score"],
            irrelevant["total_score"],
        )

    def test_partial_answer_scores_below_complete_answer(self):
        expected = [
            "A decorator modifies the behavior of another function "
            "without changing its source code.",
            "Decorators are commonly used for logging and authentication.",
        ]

        complete = evaluate_answer(
            "Decorator bổ sung hành vi cho hàm mà không cần sửa mã nguồn. "
            "Ví dụ, decorator có thể ghi log và kiểm tra xác thực người dùng.",
            expected,
        )

        partial = evaluate_answer(
            "Decorator là một hàm dùng để bổ sung hành vi cho hàm khác.",
            expected,
        )

        self.assertGreater(
            complete["total_score"],
            partial["total_score"],
        )

    def test_irrelevant_answer_scores_low(self):
        result = evaluate_answer(
            "Tôi thích làm việc nhóm và xây dựng các ứng dụng web.",
            [
                "A decorator modifies the behavior of another function.",
            ],
        )

        self.assertLess(result["total_score"], 40)


if __name__ == "__main__":
    unittest.main()
