# Kindred course feedback

An anonymous Flask app for collecting course and faculty ratings and viewing privacy-conscious summaries.

## Run locally

The app uses SQLite by default, creates an `instance\feedback.sqlite3` database on first run, and adds example courses and questions. The course list includes AI &amp; ML, AI &amp; Data Science, CE, CSE, Data Science, ECE, EEE, IT, Civil, and Mechanical Engineering, along with the original examples. Added course names are inserted into an existing database the next time the app starts. It does not add any invented feedback, so the dashboard starts empty.

Install the packages from `requirements.txt`, then run:

```powershell
python app.py
```

Open <http://127.0.0.1:5000/>. The faculty feedback form is at `/faculty-feedback`, course feedback is at `/feedback`, and aggregated charts and summaries are at `/dashboard`.

## MySQL option

Run `schema.sql` in MySQL to create the `feedback_db` database and its tables. Then set the connection environment variables before starting the app:

```powershell
$env:DATABASE_TYPE = "mysql"
$env:MYSQL_HOST = "localhost"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "your-local-password"
$env:MYSQL_DATABASE = "feedback_db"
python app.py
```

`MYSQL_PORT` defaults to `3306`. Keep database credentials out of source control.

## Privacy and reporting

- Respondents are not asked for their own name, email, or student ID. The faculty form asks only for the faculty member and subject being reviewed.
- Faculty feedback collects the faculty member and subject being reviewed, five 1–5 teaching-category ratings, and an optional comment that is not included in reports.
- Ratings must be integers from 1 through 5. Optional comments are limited to 500 characters and are never shown in the dashboard or exported.
- A course/question or faculty/subject/category group is reported only after it has at least three ratings. Suppressed groups are excluded from comparisons as well.
- CSV downloads contain aggregate averages, rating counts, and rating distributions only.

## JSON endpoint

`POST /api/feedback` accepts a JSON object with a valid `course_id` and one rating for every configured `question_id`:

```json
{
  "course_id": 1,
  "ratings": [
    {"question_id": 1, "rating": 4, "comment": ""},
    {"question_id": 2, "rating": 5},
    {"question_id": 3, "rating": 3}
  ]
}
```

`POST /api/faculty-feedback` accepts `faculty_name`, `subject`, `comment`, and one rating from 1 to 5 for each category: Teaching quality, Communication, Subject knowledge, Punctuality, and Student interaction. It does not accept or collect student identity fields.

## Tests

```powershell
python -m unittest discover -s tests -v
```
