
import unittest

from app.ai.question_generator import generate_questions


class TestQuestionGenerator(unittest.TestCase):

    def setUp(self):
        self.context = {
            "career_level": "junior",
            "language": "vi",
            "candidate_profile": {
                "projects": [
                    {
                        "name": "Website quản lý bán hàng",
                        "title": "Website quản lý bán hàng",
                    }
                ]
            },
            "cv_score": {
                "overall_score": 72,
                "matched_required_skills": ["JavaScript", "PostgreSQL"],
                "missing_required_skills": ["Python"],
                "matched_preferred_skills": ["React"],
                "strengths": ["Có kinh nghiệm xây dựng ứng dụng web"],
                "improvements": ["Cần cải thiện Python"],
            },
            "job": {
                "title": "Junior Web Developer",
                "required_skills": ["JavaScript", "PostgreSQL", "Python"],
                "preferred_skills": ["React"],
                "description": "Develop web applications",
            },
        }

    def test_generates_questions(self):
        questions = generate_questions(self.context)

        self.assertGreater(len(questions), 0)

    def test_respects_requested_count(self):
        questions = generate_questions(self.context, count=3)

        self.assertEqual(len(questions), 3)

    def test_positions_are_sequential(self):
        questions = generate_questions(self.context, count=10)

        positions = [q["position"] for q in questions]

        self.assertEqual(
            positions,
            list(range(1, len(questions) + 1)),
        )

    def test_missing_skill_is_prioritized(self):
        questions = generate_questions(self.context, count=10)

        self.assertIn(
            "Python",
            questions[0]["question_text"],
        )
        self.assertEqual(questions[0]["topic"], "Python")

    def test_questions_contain_expected_points(self):
        questions = generate_questions(self.context)

        for question in questions:
            self.assertTrue(question["question_text"])
            self.assertIsInstance(question["expected_points"], list)
            self.assertGreater(len(question["expected_points"]), 0)

    def test_questions_include_source_context(self):
        questions = generate_questions(self.context)

        for question in questions:
            self.assertIn("source_context", question)
            self.assertEqual(
                question["source_context"]["career_level"],
                "junior",
            )

    def test_senior_level_changes_problem_difficulty(self):
        context = {
            **self.context,
            "career_level": "senior",
            "cv_score": {},
            "candidate_profile": {},
        }

        questions = generate_questions(context, count=10)

        problem_questions = [
            q for q in questions
            if q["topic"] == "problem_solving"
        ]

        self.assertEqual(len(problem_questions), 1)
        self.assertEqual(
            problem_questions[0]["source_context"]["difficulty"],
            "hard",
        )

    def test_empty_context_does_not_crash(self):
        questions = generate_questions({}, count=5)

        self.assertLessEqual(len(questions), 5)
        self.assertGreater(len(questions), 0)

    def test_zero_count_returns_empty_list(self):
        questions = generate_questions(self.context, count=0)

        self.assertEqual(questions, [])

    def test_negative_count_returns_empty_list(self):
        questions = generate_questions(self.context, count=-1)

        self.assertEqual(questions, [])


if __name__ == "__main__":
    unittest.main()
