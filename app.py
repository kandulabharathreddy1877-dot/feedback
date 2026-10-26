import csv
import io
import os
import secrets
from typing import Any

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

import config
from analysis import (
    PRIVACY_THRESHOLD,
    get_dashboard_data,
    get_faculty_dashboard_data,
)
from charts import render_chart
from db import (
    get_courses,
    FACULTY_RATING_CATEGORIES,
    get_questions,
    initialize_database,
    save_faculty_feedback,
    save_feedback,
)


def _parse_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a whole number.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ValueError(f"{field_name} must be a whole number.")


def _make_submission(
    course_value: Any,
    ratings: Any,
    courses: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> tuple[int, list[dict[str, Any]]]:
    course_id = _parse_integer(course_value, "Course")
    valid_course_ids = {course["course_id"] for course in courses}
    if course_id not in valid_course_ids:
        raise ValueError("Choose a valid course.")
    if not isinstance(ratings, list):
        raise ValueError("Ratings must be a list.")

    question_ids = {question["question_id"] for question in questions}
    normalized_ratings = {}
    for item in ratings:
        if not isinstance(item, dict):
            raise ValueError("Each rating must be an object.")
        question_id = _parse_integer(item.get("question_id"), "Question")
        rating = _parse_integer(item.get("rating"), "Rating")
        if question_id not in question_ids:
            raise ValueError("Choose a valid question.")
        if question_id in normalized_ratings:
            raise ValueError("Submit one rating for each question.")
        if rating not in range(1, 6):
            raise ValueError("Ratings must be between 1 and 5.")

        comment = item.get("comment", "")
        if not isinstance(comment, str):
            raise ValueError("Comments must be text.")
        comment = comment.strip()
        if len(comment) > 500:
            raise ValueError("Comments must be 500 characters or fewer.")
        normalized_ratings[question_id] = {
            "question_id": question_id,
            "rating": rating,
            "comment": comment or None,
        }

    if set(normalized_ratings) != question_ids:
        raise ValueError("Please rate every question before submitting.")
    return course_id, list(normalized_ratings.values())


def _make_faculty_submission(
    faculty_name: Any,
    subject: Any,
    ratings: Any,
    comment: Any,
) -> tuple[str, str, str | None, list[dict[str, Any]]]:
    if not isinstance(faculty_name, str) or not faculty_name.strip():
        raise ValueError("Enter the faculty member's name.")
    if len(faculty_name.strip()) > 100:
        raise ValueError("Faculty names must be 100 characters or fewer.")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Enter the subject or course name.")
    if len(subject.strip()) > 100:
        raise ValueError("Subject names must be 100 characters or fewer.")
    if not isinstance(ratings, list):
        raise ValueError("Ratings must be a list.")
    if not isinstance(comment, str):
        raise ValueError("Comments must be text.")
    comment = comment.strip()
    if len(comment) > 500:
        raise ValueError("Comments must be 500 characters or fewer.")

    normalized_ratings = {}
    for item in ratings:
        if not isinstance(item, dict):
            raise ValueError("Each rating must be an object.")
        category = item.get("category")
        if category not in FACULTY_RATING_CATEGORIES:
            raise ValueError("Choose a valid feedback category.")
        if category in normalized_ratings:
            raise ValueError("Submit one rating for each category.")
        rating = _parse_integer(item.get("rating"), "Rating")
        if rating not in range(1, 6):
            raise ValueError("Ratings must be between 1 and 5.")
        normalized_ratings[category] = {
            "category": category,
            "rating": rating,
        }

    if set(normalized_ratings) != set(FACULTY_RATING_CATEGORIES):
        raise ValueError("Please rate every faculty category before submitting.")
    return (
        faculty_name.strip(),
        subject.strip(),
        comment or None,
        list(normalized_ratings.values()),
    )


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_TYPE=config.DATABASE_TYPE,
        DATABASE_PATH=config.DATABASE_PATH,
        MYSQL_CONFIG=config.MYSQL_CONFIG,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    with app.app_context():
        initialize_database()

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/feedback", methods=["GET", "POST"])
    def feedback_form():
        courses = get_courses()
        questions = get_questions()
        errors = []

        if request.method == "POST":
            try:
                ratings = [
                    {
                        "question_id": question["question_id"],
                        "rating": request.form.get(f"rating_{question['question_id']}"),
                        "comment": request.form.get(
                            f"comment_{question['question_id']}", ""
                        ),
                    }
                    for question in questions
                ]
                course_id, submission = _make_submission(
                    request.form.get("course_id"), ratings, courses, questions
                )
                save_feedback(course_id, submission)
                return redirect(url_for("feedback_form", submitted="1"))
            except ValueError as error:
                errors.append(str(error))

        return render_template(
            "feedback.html",
            courses=courses,
            questions=questions,
            errors=errors,
            submitted=request.args.get("submitted") == "1",
            privacy_threshold=PRIVACY_THRESHOLD,
        ), (400 if errors else 200)

    @app.route("/faculty-feedback", methods=["GET", "POST"])
    def faculty_feedback_form():
        errors = []
        if request.method == "POST":
            ratings = [
                {
                    "category": category,
                    "rating": request.form.get(f"rating_{index}"),
                }
                for index, category in enumerate(FACULTY_RATING_CATEGORIES, start=1)
            ]
            try:
                faculty_name, subject, comment, submission = _make_faculty_submission(
                    request.form.get("faculty_name"),
                    request.form.get("subject"),
                    ratings,
                    request.form.get("comment", ""),
                )
                save_faculty_feedback(faculty_name, subject, comment, submission)
                return redirect(
                    url_for("faculty_feedback_form", submitted="1")
                )
            except ValueError as error:
                errors.append(str(error))

        return render_template(
            "faculty_feedback.html",
            categories=FACULTY_RATING_CATEGORIES,
            errors=errors,
            submitted=request.args.get("submitted") == "1",
            privacy_threshold=PRIVACY_THRESHOLD,
        ), (400 if errors else 200)

    @app.route("/api/feedback", methods=["POST"])
    def submit_feedback_api():
        if not request.is_json:
            return jsonify({"error": "Send feedback as a JSON object."}), 415

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "The request body must be a JSON object."}), 400

        try:
            course_id, submission = _make_submission(
                payload.get("course_id"),
                payload.get("ratings"),
                get_courses(),
                get_questions(),
            )
            save_feedback(course_id, submission)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        return jsonify(
            {
                "message": "Feedback submitted.",
                "ratings_saved": len(submission),
            }
        ), 201

    @app.route("/api/faculty-feedback", methods=["POST"])
    def submit_faculty_feedback_api():
        if not request.is_json:
            return jsonify({"error": "Send feedback as a JSON object."}), 415

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "The request body must be a JSON object."}), 400

        try:
            faculty_name, subject, comment, submission = _make_faculty_submission(
                payload.get("faculty_name"),
                payload.get("subject"),
                payload.get("ratings"),
                payload.get("comment", ""),
            )
            save_faculty_feedback(faculty_name, subject, comment, submission)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        return jsonify(
            {
                "message": "Faculty feedback submitted.",
                "ratings_saved": len(submission),
            }
        ), 201

    @app.route("/dashboard")
    def dashboard():
        data = get_dashboard_data()
        faculty_data = get_faculty_dashboard_data()
        return render_template(
            "dashboard.html",
            data=data,
            faculty_data=faculty_data,
            privacy_threshold=PRIVACY_THRESHOLD,
        )

    @app.route("/reports/summary.csv")
    def summary_csv():
        data = get_dashboard_data()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Course",
                "Question",
                "Average rating (out of 5)",
                "Rating count",
                *[f"Rating {rating} count" for rating in range(1, 6)],
            ]
        )
        for item in data["questions"]:
            writer.writerow(
                [
                    item["course_name"],
                    item["question_text"],
                    item["average_rating"],
                    item["response_count"],
                    *[
                        item["distribution"][rating]
                        for rating in range(1, 6)
                    ],
                ]
            )
        response = send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="course-feedback-summary.csv",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/reports/faculty-summary.csv")
    def faculty_summary_csv():
        data = get_faculty_dashboard_data()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Faculty",
                "Subject",
                "Category",
                "Average rating (out of 5)",
                "Response count",
                *[f"Rating {rating} count" for rating in range(1, 6)],
            ]
        )
        for item in data["categories"]:
            writer.writerow(
                [
                    item["faculty_name"],
                    item["subject"],
                    item["category"],
                    item["average_rating"],
                    item["response_count"],
                    *[
                        item["distribution"][rating]
                        for rating in range(1, 6)
                    ],
                ]
            )

        response = send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="faculty-feedback-summary.csv",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/charts/<chart_type>.png")
    def chart_image(chart_type: str):
        if chart_type not in {"courses", "ratings", "faculty"}:
            abort(404)
        if chart_type == "faculty":
            data = get_faculty_dashboard_data()
        else:
            data = get_dashboard_data()
        if not data["has_data"]:
            abort(404)
        response = send_file(render_chart(chart_type, data), mimetype="image/png")
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
