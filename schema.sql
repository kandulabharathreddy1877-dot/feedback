CREATE DATABASE IF NOT EXISTS feedback_db;
USE feedback_db;

CREATE TABLE IF NOT EXISTS courses (
  course_id INT AUTO_INCREMENT PRIMARY KEY,
  course_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS feedback_questions (
  question_id INT AUTO_INCREMENT PRIMARY KEY,
  question_text VARCHAR(255) NOT NULL UNIQUE
);

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
);

CREATE TABLE IF NOT EXISTS faculty_feedback (
  feedback_id INT AUTO_INCREMENT PRIMARY KEY,
  faculty_name VARCHAR(100) NOT NULL,
  subject VARCHAR(100) NOT NULL,
  comment_optional TEXT NULL,
  submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faculty_feedback_ratings (
  rating_id INT AUTO_INCREMENT PRIMARY KEY,
  feedback_id INT NOT NULL,
  category VARCHAR(50) NOT NULL,
  rating TINYINT NOT NULL,
  FOREIGN KEY (feedback_id) REFERENCES faculty_feedback(feedback_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_faculty_rating CHECK (rating BETWEEN 1 AND 5),
  UNIQUE (feedback_id, category)
);