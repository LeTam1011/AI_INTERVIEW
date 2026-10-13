
import unittest

from app.ai.follow_up_generator import generate_follow_up


class TestFollowUpGenerator(unittest.TestCase):

    def test_empty_answer_requests_retry(self):
        result = generate_follow_up(
            question_text="String là gì?",
            answer_text="",
            topic="string",
        )

        self.assertIn("trả lời lại", result["question_text"])
        self.assertEqual(result["question_type"], "follow_up")

    def test_repetitive_answer_requests_retry(self):
        result = generate_follow_up(
            question_text="Bạn hiểu gì về Python?",
            answer_text="ha ha ha ha ha ha ha",
            topic="Python",
        )

        self.assertIn("trả lời lại", result["question_text"])

    def test_short_answer_requests_more_details(self):
        result = generate_follow_up(
            question_text="String là gì?",
            answer_text="String dùng để lưu văn bản.",
            topic="string",
        )

        self.assertIn("giải thích rõ hơn", result["question_text"])

    def test_low_score_focuses_on_missing_criteria(self):
        result = generate_follow_up(
            question_text="Bạn đã sử dụng Java thế nào?",
            answer_text=(
                "Tôi dùng Java trong dự án và viết các chức năng."
            ),
            expected_points=[
                "Giải thích cách xử lý ngoại lệ",
                "Nêu kết quả kiểm thử",
            ],
            topic="Java",
            evaluation_score=40,
        )

        self.assertIn(
            "Giải thích cách xử lý ngoại lệ",
            result["question_text"],
        )

    def test_high_score_asks_deeper_question(self):
        result = generate_follow_up(
            question_text="Bạn thiết kế API như thế nào?",
            answer_text=(
                "Tôi thiết kế REST API, xác thực dữ liệu đầu vào, "
                "xử lý lỗi, kiểm thử endpoint và ghi log để theo dõi "
                "các vấn đề phát sinh trong quá trình vận hành."
            ),
            topic="REST API",
            evaluation_score=90,
        )

        self.assertIn(
            "tình huống phức tạp hơn",
            result["question_text"],
        )

    def test_evaluation_metadata_is_preserved(self):
        result = generate_follow_up(
            question_text="SQL là gì?",
            answer_text="SQL dùng để truy vấn dữ liệu.",
            topic="SQL",
            evaluation_score=75,
            evaluation_hint="Cần đưa ví dụ cụ thể.",
        )

        source = result["source_context"]

        self.assertEqual(source["generator"], "rule_based_v2")
        self.assertEqual(source["evaluation_score"], 75)
        self.assertEqual(
            source["evaluation_hint"],
            "Cần đưa ví dụ cụ thể.",
        )


if __name__ == "__main__":
    unittest.main()