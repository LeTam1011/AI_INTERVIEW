
import unittest
from unittest.mock import patch

from app.ai.rag_question_generator import generate_rag_questions


class TestRAGQuestionGenerator(unittest.TestCase):
    def setUp(self):
        self.context = {
            "career_level": "junior",
            "language": "vi",
            "job": {
                "title": "Junior Python Developer",
                "description": "Develop backend web applications",
            },
            "cv_score": {
                "matched_required_skills": ["Python"],
                "missing_required_skills": ["PostgreSQL"],
            },
            "candidate_profile": {"projects": []},
        }

    @patch("app.ai.rag_question_generator.search_questions")
    def test_adds_relevant_rag_question(self, mock_search):
        mock_search.return_value = [{
            "id": "test-1",
            "question": "Explain Python decorators.",
            "answer": "Decorators modify or extend function behavior.",
            "category": "Languages and Frameworks",
            "difficulty": "Medium",
            "similarity": 0.8,
        }]

        questions = generate_rag_questions(self.context, count=6)

        self.assertTrue(
            any(q["question_text"] == "Explain Python decorators."
                for q in questions)
        )

    @patch("app.ai.rag_question_generator.search_questions")
    def test_rejects_low_similarity(self, mock_search):
        mock_search.return_value = [{
            "id": "test-2",
            "question": "Build a compiler for a new programming language.",
            "answer": "Compiler design",
            "category": "Low-level Systems",
            "difficulty": "Hard",
            "similarity": 0.3,
        }]

        questions = generate_rag_questions(self.context, count=6)

        self.assertFalse(
            any(q["question_text"] ==
                "Build a compiler for a new programming language."
                for q in questions)
        )

    @patch("app.ai.rag_question_generator.search_questions")
    def test_positions_are_sequential(self, mock_search):
        mock_search.return_value = []

        questions = generate_rag_questions(self.context, count=6)

        self.assertEqual(
            [q["position"] for q in questions],
            list(range(1, len(questions) + 1)),
        )

    def test_zero_count_returns_empty(self):
        self.assertEqual(
            generate_rag_questions(self.context, count=0),
            [],
        )


if __name__ == "__main__":
    unittest.main()
