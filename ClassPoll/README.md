# ClassPoll – Smart Classroom Poll & Participation Tracker

A full-stack WAD project using HTML, CSS, JavaScript, Flask, and MySQL.

## Features
- Teacher/student registration and login
- Teacher creates classes and shares a join code
- Students join a class with the code
- Teachers create polls with 2–8 options and an optional closing time
- Students can vote once per poll
- Poll results with counts and percentages
- Teacher participation status (Voted/Pending)
- Search participation list and export it as CSV
- Role and class access checks

## 1. Requirements
Install Python 3.10+ and MySQL Server. Use VS Code or another editor.

## 2. Create the database
1. Open MySQL Workbench or the MySQL command line.
2. Run the full contents of `schema.sql`.
3. Create a dedicated database user (recommended) and grant access:

```sql
CREATE USER 'classpoll_user'@'localhost' IDENTIFIED BY 'Choose-A-Strong-Password';
GRANT ALL PRIVILEGES ON classpoll.* TO 'classpoll_user'@'localhost';
FLUSH PRIVILEGES;
```

If you use another MySQL username, update `.env` accordingly.

## 3. Configure environment
Copy `.env.example` to a new file named `.env`, then set the values:

```env
SECRET_KEY=put-a-long-random-secret-here
DB_HOST=localhost
DB_USER=classpoll_user
DB_PASSWORD=Choose-A-Strong-Password
DB_NAME=classpoll
```

Do not upload `.env` to GitHub. `.gitignore` excludes it.

## 4. Install and run

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate.bat
```

Then open `http://127.0.0.1:5000` in your browser.

## 5. Demo flow
1. Register a Teacher account.
2. Log in and create a class, for example `WAD - Section A`.
3. Copy the generated six-character class code.
4. Register a Student account with a different email.
5. Log in as the student and join using that code.
6. Log back in as the teacher and create a poll with at least two options.
7. Log in as the student and vote.
8. Log in as the teacher, open the poll, then select **View participation**.
9. Use **Export CSV** to download the participation report.

## Database tables
- `users`: teacher/student accounts and password hashes
- `classes`: classes and unique join codes
- `class_members`: student membership in classes
- `polls`: poll question, deadline and settings
- `poll_options`: available answers
- `votes`: student selections; unique key prevents duplicate votes

## GitHub
From the project folder:

```bash
git init
git add .
git commit -m "Initial ClassPoll full-stack application"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ClassPoll.git
git push -u origin main
```

Create an empty repository on GitHub first, then replace the example URL with your repository URL. Check `git status` before pushing and ensure `.env` is not staged.

## Notes
- This is a college/demo starter project. Before public production deployment, add CSRF protection, rate limiting, stronger operational logging, database migrations, secure HTTPS deployment, and tests.
- For privacy, the participation page shows only whether a student voted; it does not show their selected answer.
- Results are summarized by option. Students may see results according to the poll visibility setting.
