
import unittest

from app.ai.cv_scorer import score_cv, _matches_skill


class TestSkillAliases(unittest.TestCase):
    def test_javascript_matches_js(self):
        self.assertTrue(_matches_skill("I built an app using JavaScript", "JS"))

    def test_postgres_matches_postgresql(self):
        self.assertTrue(
            _matches_skill("Database: PostgreSQL", "Postgres")
        )

    def test_react_does_not_automatically_match_nextjs(self):
        self.assertFalse(
            _matches_skill("Built a React application", "Next.js")
        )


class TestCVScorer(unittest.TestCase):
    def score(self, **overrides):
        args = {
            "resume_text": (
                "Education\nComputer Science degree\n"
                "Experience\n2 years experience as a developer\n"
                "Projects\nBuilt a web application using JavaScript "
                "and PostgreSQL\n"
                "Skills\nJavaScript, PostgreSQL, React\n"
                "Email: candidate@example.com"
            ),
            "candidate_profile": {},
            "job_title": "Junior Web Developer",
            "job_description": (
                "Develop web applications and maintain databases."
            ),
            "required_skills": ["JS", "Postgres", "Python"],
            "preferred_skills": ["React"],
            "responsibilities": ["web applications"],
            "career_level": "junior",
        }
        args.update(overrides)
        return score_cv(**args)

    def test_equivalent_skills_are_matched(self):
        result = self.score()

        self.assertIn("JS", result["matched_required_skills"])
        self.assertIn("Postgres", result["matched_required_skills"])
        self.assertIn("Python", result["missing_required_skills"])
        self.assertIn("React", result["matched_preferred_skills"])

    def test_missing_required_skills_are_reported(self):
        result = self.score(required_skills=["Python", "Java"])

        self.assertEqual(
            set(result["missing_required_skills"]),
            {"Python", "Java"},
        )

    def test_empty_skill_requirements_do_not_crash(self):
        result = self.score(
            required_skills=[],
            preferred_skills=[],
        )

        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)

    def test_senior_level_requires_more_experience_than_intern(self):
        resume_text = (
            "Experience\nWorked as a developer.\n"
            "Projects\nBuilt a web application."
        )

        intern = self.score(
            resume_text=resume_text,
            career_level="intern",
        )
        senior = self.score(
            resume_text=resume_text,
            career_level="senior",
        )

        self.assertGreater(
            intern["breakdown"]["experience_match"]["score"],
            senior["breakdown"]["experience_match"]["score"],
        )

    def test_empty_cv_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.score(resume_text="", candidate_profile={})

    def test_score_stays_within_zero_and_one_hundred(self):
        result = self.score()

        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)

        for item in result["breakdown"].values():
            self.assertGreaterEqual(item["score"], 0)
            self.assertLessEqual(item["score"], 100)


if __name__ == "__main__":
    unittest.main()
