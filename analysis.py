import numpy as np
import pandas as pd

from db import get_faculty_rating_rows, get_rating_rows


PRIVACY_THRESHOLD = 3
RATING_VALUES = (1, 2, 3, 4, 5)


def get_dashboard_data() -> dict:
    rows = get_rating_rows()
    if not rows:
        return {"courses": [], "questions": [], "has_data": False}

    feedback = pd.DataFrame.from_records(rows)
    group_columns = ["course_id", "course_name", "question_id", "question_text"]
    grouped = (
        feedback.groupby(group_columns, as_index=False)
        .agg(response_count=("rating", "size"))
    )
    visible_groups = grouped[grouped["response_count"] >= PRIVACY_THRESHOLD]

    questions = []
    for item in visible_groups.to_dict(orient="records"):
        matching = feedback[
            (feedback["course_id"] == item["course_id"])
            & (feedback["question_id"] == item["question_id"])
        ]["rating"].to_numpy(dtype=int)
        distribution = np.bincount(matching, minlength=6)[1:6]
        questions.append(
            {
                "course_id": int(item["course_id"]),
                "course_name": str(item["course_name"]),
                "question_id": int(item["question_id"]),
                "question_text": str(item["question_text"]),
                "average_rating": round(float(np.average(matching)), 2),
                "response_count": int(item["response_count"]),
                "distribution": {
                    rating: int(distribution[rating - 1]) for rating in RATING_VALUES
                },
            }
        )

    if not questions:
        return {"courses": [], "questions": [], "has_data": False}

    visible_keys = {
        (item["course_id"], item["question_id"]) for item in questions
    }
    visible_feedback = feedback[
        feedback.apply(
            lambda row: (row["course_id"], row["question_id"]) in visible_keys,
            axis=1,
        )
    ]
    course_groups = visible_feedback.groupby(
        ["course_id", "course_name"], as_index=False
    ).agg(response_count=("rating", "size"))

    courses = []
    for item in course_groups.to_dict(orient="records"):
        ratings = visible_feedback[
            visible_feedback["course_id"] == item["course_id"]
        ]["rating"].to_numpy(dtype=int)
        distribution = np.bincount(ratings, minlength=6)[1:6]
        courses.append(
            {
                "course_id": int(item["course_id"]),
                "course_name": str(item["course_name"]),
                "average_rating": round(float(np.average(ratings)), 2),
                "response_count": int(item["response_count"]),
                "distribution": {
                    rating: int(distribution[rating - 1]) for rating in RATING_VALUES
                },
            }
        )

    total_ratings = len(visible_feedback)
    overall_average = np.average(visible_feedback["rating"].to_numpy(dtype=int))
    return {
        "courses": courses,
        "questions": questions,
        "has_data": bool(courses),
        "overall_average": round(overall_average, 2),
    }


def get_faculty_dashboard_data() -> dict:
    rows = get_faculty_rating_rows()
    if not rows:
        return {"faculty": [], "categories": [], "has_data": False}

    feedback = pd.DataFrame.from_records(rows)
    grouped = feedback.groupby(
        ["faculty_name", "subject", "category"], as_index=False
    ).agg(response_count=("rating", "size"))
    visible_groups = grouped[grouped["response_count"] >= PRIVACY_THRESHOLD]

    categories = []
    for item in visible_groups.to_dict(orient="records"):
        matching = feedback[
            (feedback["faculty_name"] == item["faculty_name"])
            & (feedback["subject"] == item["subject"])
            & (feedback["category"] == item["category"])
        ]["rating"].to_numpy(dtype=int)
        distribution = np.bincount(matching, minlength=6)[1:6]
        categories.append(
            {
                "faculty_name": str(item["faculty_name"]),
                "subject": str(item["subject"]),
                "category": str(item["category"]),
                "average_rating": round(float(np.average(matching)), 2),
                "response_count": int(item["response_count"]),
                "distribution": {
                    rating: int(distribution[rating - 1]) for rating in RATING_VALUES
                },
            }
        )

    if not categories:
        return {"faculty": [], "categories": [], "has_data": False}

    visible_keys = {
        (item["faculty_name"], item["subject"], item["category"])
        for item in categories
    }
    visible_feedback = feedback[
        feedback.apply(
            lambda row: (
                row["faculty_name"],
                row["subject"],
                row["category"],
            )
            in visible_keys,
            axis=1,
        )
    ]
    summaries = visible_feedback.groupby(
        ["faculty_name", "subject"], as_index=False
    ).agg(response_count=("rating", "size"))
    faculty = []
    for item in summaries.to_dict(orient="records"):
        matching = visible_feedback[
            (visible_feedback["faculty_name"] == item["faculty_name"])
            & (visible_feedback["subject"] == item["subject"])
        ]["rating"].to_numpy(dtype=int)
        faculty.append(
            {
                "faculty_name": str(item["faculty_name"]),
                "subject": str(item["subject"]),
                "average_rating": round(float(np.average(matching)), 2),
                "response_count": int(item["response_count"]),
            }
        )

    total_ratings = len(visible_feedback)
    return {
        "faculty": faculty,
        "categories": categories,
        "has_data": bool(faculty),
        "overall_average": round(
            float(np.average(visible_feedback["rating"].to_numpy(dtype=int))), 2
        ),
        "total_ratings": total_ratings,
    }
