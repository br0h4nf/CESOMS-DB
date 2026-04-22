# CESOMS

Campus Event and Student Organization Management System built with Flask and MySQL.

## Features

- Secure database-backed authentication with hashed passwords
- Student signup, login, logout, profile editing, and password change
- Officer dashboard for event creation, editing, submission, and attendance tracking
- Admin dashboard for approvals, user creation, memberships, officer roles, organizations, locations, categories, and academic terms
- Reporting cards and schema demo dashboard

## Tech Stack

- Frontend: Flask templates, HTML, CSS, vanilla JavaScript
- Backend: Flask, Python
- Database: MySQL
- Auth security: `werkzeug.security` password hashing

## Project Files

- `app.py`: main Flask application
- `templates/`: role dashboards and auth pages
- `static/`: styles and dashboard JavaScript
- `DB_info.example.txt`: database config template
- `bootstrap_admin.py`: CLI helper to seed the first admin login

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create `DB_info.txt` in the `CESOMS` folder using this format:

```txt
host=YOUR_DB_HOST
user=YOUR_DB_USER
password=YOUR_DB_PASSWORD
database=YOUR_DB_NAME
port=3306
```

4. Start the app:

```powershell
python app.py
```

5. Open:

```txt
http://127.0.0.1:5000
```

## First Admin Login

You have two ways to create the first admin login.

### Option 1: In the Browser

- Open `/login`
- Click `Initialize the first administrator`
- Use an existing `ADMINISTRATOR` record and set a password

### Option 2: Command Line Bootstrap

Run:

```powershell
python bootstrap_admin.py --admin-id ADM-1 --first-name Alex --last-name Rivera --email admin@school.edu --department "Student Affairs" --password "ChangeMe123!"
```

This helper:

- creates or updates the `ADMINISTRATOR` row
- creates or updates the hashed login in `APP_USER`

## Default User Flows

### Student

- Sign up
- Log in
- Update profile
- Change password
- Join or leave organizations
- Register or unregister from events

### Officer

- Everything a student can do
- Create and edit events
- Submit events for approval
- Record attendance

### Admin

- Log in
- Change password
- Create student and admin users
- Review approvals
- Move students between memberships and officer roles
- Manage organizations, locations, categories, and terms

## Security Notes

- Passwords are never stored in plain text
- Passwords are hashed using Werkzeug
- Database queries use parameterized statements to reduce basic SQL injection risk
- Authentication data is stored in the `APP_USER` table, not hardcoded in source files

## Demo Tips

- Create one admin and one student account first
- Assign the student to an organization and officer role from the admin dashboard
- Log in as that student to show the officer dashboard
- Create an event, submit it, approve it as admin, then register and record attendance
