import json
import tempfile
import unittest
from pathlib import Path

from app import create_app
from db import (
    FACULTY_RATING_CATEGORIES,
    get_courses,
    get_faculty_rating_rows,
    get_questions,
    get_rating_rows,
)


class FeedbackAppTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": Path(self.temporary_directory.name) / "test.sqlite3",
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            self.course_id = get_courses()[0]["course_id"]
            self.questions = get_questions()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def payload(self, rating=4, comment=""):
        if isinstance(rating, list):
            ratings = rating
        else:
            ratings = [rating] * len(self.questions)
        return {
            "course_id": self.course_id,
            "ratings": [
                {
                    "question_id": question["question_id"],
                    "rating": ratings[index],
                    "comment": comment,
                }
                for index, question in enumerate(self.questions)
            ],
        }

    def submit(self, rating=4, comment=""):
        return self.client.post(
            "/api/feedback",
            data=json.dumps(self.payload(rating, comment)),
            content_type="application/json",
        )

    def test_home_and_feedback_form_render(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No name or email address is requested", response.data)
        self.assertIn(b"Artificial Intelligence and Machine Learning (AI &amp; ML)", response.data)
        self.assertIn(b"Computer Engineering (CE)", response.data)
        self.assertIn(b"Artificial Intelligence and Data Science (AI &amp; DS)", response.data)
        self.assertIn(b"Data Science", response.data)
        self.assertIn(b"Computer Science and Engineering (CSE)", response.data)

    def test_rating_validation_rejects_out_of_range(self):
        payload = self.payload()
        payload["ratings"][0]["rating"] = 6
        response = self.client.post(
            "/api/feedback",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(get_rating_rows(), [])

    def test_reports_hide_small_groups_and_comments(self):
        private_text = "student-name-should-never-be-public"
        self.assertEqual(self.submit(rating=2, comment=private_text).status_code, 201)
        self.assertEqual(self.submit(rating=4, comment=private_text).status_code, 201)
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"No reportable ratings yet", dashboard.data)
        self.assertNotIn(private_text.encode(), dashboard.data)

        self.assertEqual(self.submit(rating=5, comment=private_text).status_code, 201)
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"Course and question summary", dashboard.data)
        self.assertIn(b"3</td>", dashboard.data)
        self.assertIn(b"3.67", dashboard.data)
        self.assertIn(b"0 / 1 / 0 / 1 / 1", dashboard.data)
        self.assertNotIn(private_text.encode(), dashboard.data)
        self.assertEqual(self.client.get("/charts/courses.png").status_code, 200)
        self.assertEqual(self.client.get("/charts/ratings.png").status_code, 200)

        report = self.client.get("/reports/summary.csv")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"Average rating", report.data)
        self.assertNotIn(private_text.encode(), report.data)

    def test_feedback_form_saves_valid_ratings(self):
        form = {
            "course_id": str(self.course_id),
            **{
                f"rating_{question['question_id']}": "5"
                for question in self.questions
            },
            f"comment_{self.questions[0]['question_id']}": "Helpful course",
        }
        response = self.client.post("/feedback", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertIn("submitted=1", response.headers["Location"])
        with self.app.app_context():
            rows = get_rating_rows()
        self.assertEqual(len(rows), len(self.questions))
        self.assertTrue(all(row["rating"] == 5 for row in rows))

    def test_json_endpoint_requires_complete_question_set(self):
        payload = self.payload()
        payload["ratings"].pop()
        response = self.client.post(
            "/api/feedback",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_faculty_form_saves_anonymous_category_ratings(self):
        form = {
            "faculty_name": "Dr. Example",
            "subject": "Computer Science",
            "comment": "student-private-comment",
            **{
                f"rating_{index}": str(index)
                for index in range(1, len(FACULTY_RATING_CATEGORIES) + 1)
            },
        }
        form_page = self.client.get("/faculty-feedback")
        self.assertEqual(form_page.status_code, 200)
        self.assertIn(b"does not ask for a student ID", form_page.data)
        self.assertNotIn(b'name="student_id"', form_page.data)

        response = self.client.post("/faculty-feedback", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertIn("submitted=1", response.headers["Location"])
        with self.app.app_context():
            rows = get_faculty_rating_rows()
        self.assertEqual(len(rows), len(FACULTY_RATING_CATEGORIES))
        self.assertEqual(
            {row["category"] for row in rows}, set(FACULTY_RATING_CATEGORIES)
        )
        self.assertEqual(
            {row["rating"] for row in rows}, set(range(1, 6))
        )

    def test_faculty_summary_hides_small_groups_and_private_comments(self):
        private_text = "faculty-comment-must-not-be-public"
        for rating in (2, 4):
            form = {
                "faculty_name": "Dr. Example",
                "subject": "Computer Science",
                "comment": private_text,
                **{
                    f"rating_{index}": str(rating)
                    for index in range(1, len(FACULTY_RATING_CATEGORIES) + 1)
                },
            }
            self.assertEqual(
                self.client.post("/faculty-feedback", data=form).status_code,
                302,
            )

        dashboard = self.client.get("/dashboard")
        self.assertIn(b"No reportable faculty ratings yet", dashboard.data)
        self.assertNotIn(private_text.encode(), dashboard.data)

        form = {
            "faculty_name": "Dr. Example",
            "subject": "Computer Science",
            "comment": private_text,
            **{
                f"rating_{index}": "5"
                for index in range(1, len(FACULTY_RATING_CATEGORIES) + 1)
            },
        }
        self.assertEqual(self.client.post("/faculty-feedback", data=form).status_code, 302)
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"Faculty and teaching category summary", dashboard.data)
        self.assertIn(b"Dr. Example", dashboard.data)
        self.assertIn(b"3.67", dashboard.data)
        self.assertNotIn(private_text.encode(), dashboard.data)
        self.assertEqual(self.client.get("/charts/faculty.png").status_code, 200)

        report = self.client.get("/reports/faculty-summary.csv")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"Faculty", report.data)
        self.assertIn(b"Teaching quality", report.data)
        self.assertNotIn(private_text.encode(), report.data)

    def test_faculty_api_rejects_invalid_rating(self):
        response = self.client.post(
            "/api/faculty-feedback",
            json={
                "faculty_name": "Dr. Example",
                "subject": "Computer Science",
                "ratings": [
                    {"category": category, "rating": 6}
                    for category in FACULTY_RATING_CATEGORIES
                ],
            },
        )
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(get_faculty_rating_rows(), [])


if __name__ == "__main__":
    unittest.main()
