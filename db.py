import sqlite3
from typing import Any

import mysql.connector
from flask import current_app, has_app_context

import config


DEFAULT_COURSES = (
    "Artificial Intelligence and Data Science (AI & DS)",
    "Artificial Intelligence and Machine Learning (AI & ML)",
    "Civil Engineering",
    "Computer Engineering (CE)",
    "Computer Science and Engineering (CSE)",
    "Data Science",
    "Electrical and Electronics Engineering (EEE)",
    "Electronics and Communication Engineering (ECE)",
    "Information Technology (IT)",
    "Introduction to Biology",
    "Mechanical Engineering",
    "Data Analytics",
    "Foundations of Psychology",
)
DEFAULT_QUESTIONS = (
    "Course materials support my learning.",
    "Course topics are explained clearly.",
    "The course supports my learning goals.",
)
FACULTY_RATING_CATEGORIES = (
    "Teaching quality",
    "Communication",
    "Subject knowledge",
    "Punctuality",
    "Student interaction",
)

SQLITE_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback_questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment_optional TEXT,
        submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(course_id),
        FOREIGN KEY (question_id) REFERENCES feedback_questions(question_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty_feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        comment_optional TEXT,
        submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty_feedback_ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feedback_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        FOREIGN KEY (feedback_id) REFERENCES faculty_feedback(feedback_id)
            ON DELETE CASCADE,
        UNIQUE (feedback_id, category)
    )
    """,
)

MYSQL_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS courses (
        course_id INT AUTO_INCREMENT PRIMARY KEY,
        course_name VARCHAR(100) NOT NULL UNIQUE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback_questions (
        question_id INT AUTO_INCREMENT PRIMARY KEY,
        question_text VARCHAR(255) NOT NULL UNIQUE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INT AUTO_INCREMENT PRIMARY KEY,
        course_id INT NOT NULL,
        question_id INT NOT NULL,
        rating TINYINT NOT NULL,
        comment_optional TEXT NULL,
        submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(course_id),
        FOREIGN KEY (question_id) REFERENCES feedback_questions(question_id),
        CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty_feedback (
        feedback_id INT AUTO_INCREMENT PRIMARY KEY,
        faculty_name VARCHAR(100) NOT NULL,
        subject VARCHAR(100) NOT NULL,
        comment_optional TEXT NULL,
        submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty_feedback_ratings (
        rating_id INT AUTO_INCREMENT PRIMARY KEY,
        feedback_id INT NOT NULL,
        category VARCHAR(50) NOT NULL,
        rating TINYINT NOT NULL,
        FOREIGN KEY (feedback_id) REFERENCES faculty_feedback(feedback_id)
            ON DELETE CASCADE,
        CONSTRAINT chk_faculty_rating CHECK (rating BETWEEN 1 AND 5),
        UNIQUE (feedback_id, category)
    ) ENGINE=InnoDB
    """,
)


def _setting(name: str, default: Any) -> Any:
    if has_app_context():
        return current_app.config.get(name, default)
    return default


def _database_type() -> str:
    return _setting("DATABASE_TYPE", config.DATABASE_TYPE)


def _connection():
    database_type = _database_type()
    if database_type == "mysql":
        mysql_config = _setting("MYSQL_CONFIG", config.MYSQL_CONFIG)
        return mysql.connector.connect(**mysql_config)
    if database_type != "sqlite":
        raise ValueError("DATABASE_TYPE must be either 'sqlite' or 'mysql'.")

    database_path = _setting("DATABASE_PATH", config.DATABASE_PATH)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _query(sql: str) -> str:
    if _database_type() == "mysql":
        return sql.replace("?", "%s")
    return sql


def initialize_database() -> None:
    statements = MYSQL_SCHEMA if _database_type() == "mysql" else SQLITE_SCHEMA
    connection = _connection()
    try:
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)

        insert_course = (
            "INSERT IGNORE INTO courses (course_name) VALUES (?)"
            if _database_type() == "mysql"
            else "INSERT OR IGNORE INTO courses (course_name) VALUES (?)"
        )
        insert_question = (
            "INSERT IGNORE INTO feedback_questions (question_text) VALUES (?)"
            if _database_type() == "mysql"
            else "INSERT OR IGNORE INTO feedback_questions (question_text) VALUES (?)"
        )
        cursor.executemany(insert_course, ((name,) for name in DEFAULT_COURSES))
        cursor.executemany(insert_question, ((text,) for text in DEFAULT_QUESTIONS))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection = _connection()
    try:
        cursor = connection.cursor(dictionary=True) if _database_type() == "mysql" else connection.cursor()
        cursor.execute(_query(sql), parameters)
        rows = cursor.fetchall()
        if _database_type() == "mysql":
            return rows
        return [dict(row) for row in rows]
    finally:
        connection.close()


def save_feedback(
    course_id: int, ratings: list[dict[str, Any]]
) -> None:
    connection = _connection()
    try:
        cursor = connection.cursor()
        cursor.executemany(
            _query(
                """
                INSERT INTO feedback
                    (course_id, question_id, rating, comment_optional)
                VALUES (?, ?, ?, ?)
                """
            ),
            [
                (
                    course_id,
                    item["question_id"],
                    item["rating"],
                    item["comment"],
                )
                for item in ratings
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_faculty_feedback(
    faculty_name: str,
    subject: str,
    comment: str | None,
    ratings: list[dict[str, Any]],
) -> None:
    connection = _connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            _query(
                """
                INSERT INTO faculty_feedback
                    (faculty_name, subject, comment_optional)
                VALUES (?, ?, ?)
                """
            ),
            (faculty_name, subject, comment),
        )
        feedback_id = cursor.lastrowid
        cursor.executemany(
            _query(
                """
                INSERT INTO faculty_feedback_ratings
                    (feedback_id, category, rating)
                VALUES (?, ?, ?)
                """
            ),
            [
                (feedback_id, item["category"], item["rating"])
                for item in ratings
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_courses() -> list[dict[str, Any]]:
    return fetch_all("SELECT course_id, course_name FROM courses ORDER BY course_name")


def get_questions() -> list[dict[str, Any]]:
    return fetch_all(
        "SELECT question_id, question_text FROM feedback_questions ORDER BY question_id"
    )


def get_rating_rows() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT c.course_id, c.course_name, q.question_id, q.question_text, f.rating
        FROM feedback AS f
        JOIN courses AS c ON c.course_id = f.course_id
        JOIN feedback_questions AS q ON q.question_id = f.question_id
        ORDER BY c.course_name, q.question_id
        """
    )


def get_faculty_rating_rows() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            f.faculty_name, f.subject, r.category, r.rating
        FROM faculty_feedback_ratings AS r
        JOIN faculty_feedback AS f ON f.feedback_id = r.feedback_id
        ORDER BY f.faculty_name, f.subject, r.category
        """
    )
