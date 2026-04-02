import os
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import mysql.connector
from datetime import date, datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cesoms-dev-secret")

def normalize_config_key(key):
    normalized = key.strip().lower()
    if normalized.startswith("db_"):
        normalized = normalized[3:]
    return normalized


def parse_config_value(value):
    return value.strip().strip('"').strip("'")


def load_db_config():
    config_path = os.environ.get("DB_CONFIG_FILE")
    candidate_paths = [config_path] if config_path else [".DB_info.txt", "DB_info.txt"]
    parsed = {}
    used_path = ""

    for path in candidate_paths:
        if not path or not os.path.exists(path):
            continue
        used_path = path
        with open(path, encoding="utf-8") as config_file:
            for raw_line in config_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                parsed[normalize_config_key(key)] = parse_config_value(value)
        break

    if not used_path:
        raise RuntimeError(
            "Database config file not found. Create .DB_info.txt or set DB_CONFIG_FILE."
        )

    required_keys = ("host", "user", "password", "database")
    missing_keys = [key for key in required_keys if not parsed.get(key)]
    if missing_keys:
        raise RuntimeError(
            f"Missing required DB keys in {used_path}: {', '.join(missing_keys)}"
        )

    config = {
        "host": parsed["host"],
        "user": parsed["user"],
        "password": parsed["password"],
        "database": parsed["database"],
    }

    if parsed.get("port"):
        try:
            config["port"] = int(parsed["port"])
        except ValueError as exc:
            raise RuntimeError(f"Invalid DB port in {used_path}: {parsed['port']}") from exc

    return config


DB_CONFIG = load_db_config()


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch_all_dict(cursor, query, params=None):
    cursor.execute(query, params or ())
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    results = []

    for row in rows:
        item = {}
        for index, column in enumerate(columns):
            item[column] = serialize_value(row[index])
        results.append(item)

    return results


def safe_fetch(cursor, query, params=None):
    try:
        return fetch_all_dict(cursor, query, params)
    except mysql.connector.Error:
        return []


def fetch_student_by_id(cursor, student_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        WHERE StudentID = %s
        LIMIT 1
    """, (student_id,))
    return rows[0] if rows else None


def fetch_student_by_credentials(cursor, student_id, email):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        WHERE StudentID = %s
          AND LOWER(Email) = LOWER(%s)
        LIMIT 1
    """, (student_id, email))
    return rows[0] if rows else None


def fetch_student_signups(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            r.EventID AS eventId,
            r.RegisteredAt AS registeredAt,
            r.RegistrationStatus AS registrationStatus,
            e.Title AS eventTitle,
            e.Description AS eventDescription,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            e.EventStatus AS eventStatus,
            o.OrgName AS organizationName,
            l.LocationName AS locationName,
            l.IsVirtual AS isVirtual
        FROM REGISTRATION r
        JOIN EVENT e ON e.EventID = r.EventID
        LEFT JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN LOCATION l ON l.LocationID = e.LocationID
        WHERE r.StudentID = %s
        ORDER BY e.StartDateTime DESC, r.RegisteredAt DESC
    """, (student_id,))


def fetch_registration_record(cursor, student_id, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            EventID AS eventId,
            RegisteredAt AS registeredAt,
            RegistrationStatus AS registrationStatus
        FROM REGISTRATION
        WHERE StudentID = %s
          AND EventID = %s
        LIMIT 1
    """, (student_id, event_id))
    return rows[0] if rows else None


def fetch_event_for_registration(cursor, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            EventID AS eventId,
            Title AS title,
            Capacity AS capacity,
            StartDateTime AS startDateTime,
            EndDateTime AS endDateTime,
            EventStatus AS eventStatus
        FROM EVENT
        WHERE EventID = %s
        LIMIT 1
    """, (event_id,))
    return rows[0] if rows else None


def count_registered_students(cursor, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT COUNT(*) AS total
        FROM REGISTRATION
        WHERE EventID = %s
          AND RegistrationStatus = 'Registered'
    """, (event_id,))
    return rows[0]["total"] if rows else 0


def fetch_available_events(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            e.EventID AS eventId,
            e.Title AS eventTitle,
            e.Description AS eventDescription,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            e.EventStatus AS eventStatus,
            e.Capacity AS capacity,
            o.OrgName AS organizationName,
            l.LocationName AS locationName,
            l.IsVirtual AS isVirtual,
            (
                SELECT COUNT(*)
                FROM REGISTRATION r2
                WHERE r2.EventID = e.EventID
                  AND r2.RegistrationStatus = 'Registered'
            ) AS registeredCount,
            r.RegistrationStatus AS myRegistrationStatus
        FROM EVENT e
        LEFT JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN LOCATION l ON l.LocationID = e.LocationID
        LEFT JOIN REGISTRATION r
            ON r.EventID = e.EventID
           AND r.StudentID = %s
        WHERE e.EventStatus IN ('Approved', 'Scheduled')
        ORDER BY e.StartDateTime ASC, e.EventID ASC
    """, (student_id,))


def current_student_id():
    return session.get("student_id")


def fetch_event_creation_options(cursor):
    return {
        "organizations": fetch_all_dict(cursor, """
            SELECT
                OrgID AS orgId,
                OrgName AS orgName
            FROM ORGANIZATION
            WHERE OrgStatus = 'Active'
            ORDER BY OrgName
        """),
        "locations": fetch_all_dict(cursor, """
            SELECT
                LocationID AS locationId,
                LocationName AS locationName
            FROM LOCATION
            ORDER BY LocationName
        """),
        "categories": fetch_all_dict(cursor, """
            SELECT
                CategoryID AS categoryId,
                CategoryName AS categoryName
            FROM EVENT_CATEGORY
            ORDER BY CategoryName
        """),
        "terms": fetch_all_dict(cursor, """
            SELECT
                TermID AS termId,
                TermName AS termName
            FROM ACADEMIC_TERM
            ORDER BY StartDate DESC
        """),
    }


def parse_datetime_local(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def student_required():
    student_id = current_student_id()
    if not student_id:
        return None, redirect(url_for("login"))
    return student_id, None


def build_reports(cursor):
    reports = safe_fetch(cursor, """
        SELECT
            ReportID AS reportId,
            GeneratedByAdminID AS generatedByAdminId,
            ReportType AS reportType,
            GeneratedAt AS generatedAt,
            Summary AS summary
        FROM REPORT
        ORDER BY GeneratedAt DESC
    """)

    if reports:
        return reports

    generated_at = datetime.now().isoformat(timespec="minutes")

    active_registrations = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM REGISTRATION
        WHERE RegistrationStatus = 'Registered'
    """)
    pending_approvals = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM APPROVAL
        WHERE DecisionStatus = 'Pending'
    """)
    active_orgs = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM ORGANIZATION
        WHERE OrgStatus = 'Active'
    """)

    reg_total = active_registrations[0]["total"] if active_registrations else 0
    pending_total = pending_approvals[0]["total"] if pending_approvals else 0
    org_total = active_orgs[0]["total"] if active_orgs else 0

    return [
        {
            "reportId": "AUTO-001",
            "generatedByAdminId": "",
            "reportType": "Registration Snapshot",
            "generatedAt": generated_at,
            "summary": f"There are {reg_total} active event registrations in the system.",
        },
        {
            "reportId": "AUTO-002",
            "generatedByAdminId": "",
            "reportType": "Approval Queue",
            "generatedAt": generated_at,
            "summary": f"There are {pending_total} event approvals still waiting for review.",
        },
        {
            "reportId": "AUTO-003",
            "generatedByAdminId": "",
            "reportType": "Organization Status",
            "generatedAt": generated_at,
            "summary": f"There are {org_total} active organizations currently on file.",
        },
    ]


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard_page():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_student_id():
        return redirect(url_for("my_signups"))

    error = ""
    form_values = {"student_id": "", "email": ""}

    if request.method == "POST":
        form_values["student_id"] = request.form.get("student_id", "").strip()
        form_values["email"] = request.form.get("email", "").strip()

        if not form_values["student_id"] or not form_values["email"]:
            error = "Enter both Student ID and email."
        else:
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                student = fetch_student_by_credentials(
                    cursor,
                    form_values["student_id"],
                    form_values["email"],
                )

                if not student:
                    error = "Invalid Student ID or email."
                elif student["accountStatus"] != "Active":
                    error = f"Account is {student['accountStatus']}. Contact your administrator."
                else:
                    session.clear()
                    session["student_id"] = student["studentId"]
                    session["student_name"] = f"{student['firstName']} {student['lastName']}"
                    return redirect(url_for("my_signups"))
            except mysql.connector.Error:
                error = "Unable to connect to the database right now. Please try again."
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    return render_template("login.html", error=error, form_values=form_values)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/my-signups")
def my_signups():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        if not student:
            session.clear()
            return redirect(url_for("login"))
        signups = fetch_student_signups(cursor, student_id)
        available_events = fetch_available_events(cursor, student_id)
    except mysql.connector.Error:
        student = {"studentId": student_id, "firstName": "", "lastName": ""}
        signups = []
        available_events = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "my_signups.html",
        student=student,
        signups=signups,
        available_events=available_events,
    )


@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    form_values = {
        "event_id": "",
        "title": "",
        "description": "",
        "org_id": "",
        "location_id": "",
        "category_id": "",
        "term_id": "",
        "capacity": "0",
        "start_datetime": "",
        "end_datetime": "",
        "event_status": "Draft",
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()

        student = fetch_student_by_id(cursor, student_id)
        if not student or student["accountStatus"] != "Active":
            session.clear()
            flash("Only active student accounts can create events.", "error")
            return redirect(url_for("login"))

        options = fetch_event_creation_options(cursor)

        if request.method == "POST":
            form_values = {
                "event_id": request.form.get("event_id", "").strip(),
                "title": request.form.get("title", "").strip(),
                "description": request.form.get("description", "").strip(),
                "org_id": request.form.get("org_id", "").strip(),
                "location_id": request.form.get("location_id", "").strip(),
                "category_id": request.form.get("category_id", "").strip(),
                "term_id": request.form.get("term_id", "").strip(),
                "capacity": request.form.get("capacity", "0").strip(),
                "start_datetime": request.form.get("start_datetime", "").strip(),
                "end_datetime": request.form.get("end_datetime", "").strip(),
                "event_status": request.form.get("event_status", "Draft").strip(),
            }

            required_values = [
                form_values["event_id"],
                form_values["title"],
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["start_datetime"],
                form_values["end_datetime"],
                form_values["event_status"],
            ]
            if any(not value for value in required_values):
                flash("Fill in all required fields.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            try:
                capacity = int(form_values["capacity"])
            except ValueError:
                flash("Capacity must be a whole number.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            if capacity < 0:
                flash("Capacity cannot be negative.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            start_datetime = parse_datetime_local(form_values["start_datetime"])
            end_datetime = parse_datetime_local(form_values["end_datetime"])
            if not start_datetime or not end_datetime:
                flash("Enter valid start and end date/time values.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            if start_datetime >= end_datetime:
                flash("Start date/time must be earlier than end date/time.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            if form_values["event_status"] not in ("Draft", "Submitted"):
                flash("Event status must be Draft or Submitted.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            org_ids = {str(item["orgId"]) for item in options["organizations"]}
            location_ids = {str(item["locationId"]) for item in options["locations"]}
            category_ids = {str(item["categoryId"]) for item in options["categories"]}
            term_ids = {str(item["termId"]) for item in options["terms"]}

            if form_values["org_id"] not in org_ids:
                flash("Choose a valid organization.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )
            if form_values["location_id"] not in location_ids:
                flash("Choose a valid location.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )
            if form_values["category_id"] not in category_ids:
                flash("Choose a valid category.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )
            if form_values["term_id"] not in term_ids:
                flash("Choose a valid academic term.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            existing = safe_fetch(cursor, """
                SELECT EventID
                FROM EVENT
                WHERE EventID = %s
                LIMIT 1
            """, (form_values["event_id"],))
            if existing:
                flash("That Event ID already exists. Use a unique ID.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    options=options,
                    form_values=form_values,
                )

            cursor.execute("""
                INSERT INTO EVENT (
                    EventID,
                    OrgID,
                    LocationID,
                    CategoryID,
                    TermID,
                    Title,
                    Description,
                    Capacity,
                    StartDateTime,
                    EndDateTime,
                    EventStatus
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                form_values["event_id"],
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["title"],
                form_values["description"],
                capacity,
                start_datetime,
                end_datetime,
                form_values["event_status"],
            ))
            conn.commit()
            flash(f"Event {form_values['event_id']} created successfully.", "success")
            return redirect(url_for("create_event"))

        return render_template(
            "create_event.html",
            student=student,
            options=options,
            form_values=form_values,
        )
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not create the event right now. Please try again.", "error")
        return redirect(url_for("create_event"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/register-event", methods=["POST"])
def register_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    event_id = request.form.get("event_id", "").strip()
    if not event_id:
        flash("Choose a valid event to register.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        student = fetch_student_by_id(cursor, student_id)
        if not student or student["accountStatus"] != "Active":
            flash("Only active student accounts can register for events.", "error")
            session.clear()
            return redirect(url_for("login"))

        event = fetch_event_for_registration(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("my_signups"))

        if event["eventStatus"] not in ("Approved", "Scheduled"):
            flash("This event is not open for registration.", "error")
            return redirect(url_for("my_signups"))

        registration = fetch_registration_record(cursor, student_id, event_id)
        if registration and registration["registrationStatus"] in ("Registered", "Waitlisted"):
            flash(f"You are already {registration['registrationStatus'].lower()} for this event.", "info")
            return redirect(url_for("my_signups"))

        registered_count = count_registered_students(cursor, event_id)
        can_register = event["capacity"] is None or registered_count < event["capacity"]
        new_status = "Registered" if can_register else "Waitlisted"
        now = datetime.now()

        if registration:
            cursor.execute("""
                UPDATE REGISTRATION
                SET RegisteredAt = %s,
                    RegistrationStatus = %s
                WHERE StudentID = %s
                  AND EventID = %s
            """, (now, new_status, student_id, event_id))
        else:
            cursor.execute("""
                INSERT INTO REGISTRATION (StudentID, EventID, RegisteredAt, RegistrationStatus)
                VALUES (%s, %s, %s, %s)
            """, (student_id, event_id, now, new_status))

        conn.commit()
        flash(f"Registration updated: {event['title']} ({new_status}).", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not process registration right now. Please try again.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/unregister-event", methods=["POST"])
def unregister_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    event_id = request.form.get("event_id", "").strip()
    if not event_id:
        flash("Choose a valid event to unregister.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        registration = fetch_registration_record(cursor, student_id, event_id)
        if not registration:
            flash("No registration record was found for that event.", "info")
            return redirect(url_for("my_signups"))

        if registration["registrationStatus"] == "Cancelled":
            flash("You are already unregistered from that event.", "info")
            return redirect(url_for("my_signups"))

        cursor.execute("""
            UPDATE REGISTRATION
            SET RegistrationStatus = 'Cancelled'
            WHERE StudentID = %s
              AND EventID = %s
        """, (student_id, event_id))
        conn.commit()
        flash("You have been unregistered from the event.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not process unregistration right now. Please try again.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/api/dashboard")
def api_dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    data = {
        "students": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                FirstName AS firstName,
                LastName AS lastName,
                Email AS email,
                ClassYear AS classYear,
                Major AS major,
                AccountStatus AS accountStatus
            FROM STUDENT
            ORDER BY StudentID
        """),
        "administrators": fetch_all_dict(cursor, """
            SELECT
                AdminID AS adminId,
                FirstName AS firstName,
                LastName AS lastName,
                Email AS email,
                Department AS department,
                AdminStatus AS adminStatus
            FROM ADMINISTRATOR
            ORDER BY AdminID
        """),
        "organizations": fetch_all_dict(cursor, """
            SELECT
                OrgID AS orgId,
                OrgName AS orgName,
                Description AS description,
                ContactEmail AS contactEmail,
                OrgStatus AS orgStatus
            FROM ORGANIZATION
            ORDER BY OrgID
        """),
        "organizationOfficers": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                OrgID AS orgId,
                StartDate AS startDate,
                RoleTitle AS roleTitle,
                EndDate AS endDate
            FROM ORGANIZATION_OFFICER
            ORDER BY OrgID, StudentID, StartDate
        """),
        "memberships": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                OrgID AS orgId,
                JoinDate AS joinDate,
                LeaveDate AS leaveDate,
                MemberRole AS memberRole
            FROM MEMBERSHIP
            ORDER BY OrgID, StudentID
        """),
        "locations": fetch_all_dict(cursor, """
            SELECT
                LocationID AS locationId,
                LocationName AS locationName,
                Building AS building,
                Room AS room,
                Address AS address,
                IsVirtual AS isVirtual,
                VirtualLink AS virtualLink,
                Capacity AS capacity
            FROM LOCATION
            ORDER BY LocationID
        """),
        "categories": fetch_all_dict(cursor, """
            SELECT
                CategoryID AS categoryId,
                CategoryName AS categoryName,
                Description AS description
            FROM EVENT_CATEGORY
            ORDER BY CategoryID
        """),
        "events": fetch_all_dict(cursor, """
            SELECT
                EventID AS eventId,
                OrgID AS orgId,
                LocationID AS locationId,
                CategoryID AS categoryId,
                TermID AS termId,
                Title AS title,
                Description AS description,
                Capacity AS capacity,
                StartDateTime AS startDateTime,
                EndDateTime AS endDateTime,
                EventStatus AS eventStatus
            FROM EVENT
            ORDER BY StartDateTime, EventID
        """),
        "registrations": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                EventID AS eventId,
                RegisteredAt AS registeredAt,
                RegistrationStatus AS registrationStatus
            FROM REGISTRATION
            ORDER BY RegisteredAt, StudentID, EventID
        """),
        "attendance": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                EventID AS eventId,
                CheckInTime AS checkInTime,
                AttendanceFlag AS attendanceFlag,
                RecordedByOfficerStudentID AS recordedByOfficerStudentId,
                RecordedByOfficerOrgID AS recordedByOfficerOrgId,
                RecordedByOfficerStartDate AS recordedByOfficerStartDate
            FROM ATTENDANCE
            ORDER BY CheckInTime, StudentID, EventID
        """),
        "approvals": fetch_all_dict(cursor, """
            SELECT
                EventID AS eventId,
                SubmittedByOfficerStudentID AS submittedByOfficerStudentId,
                SubmittedByOfficerOrgID AS submittedByOfficerOrgId,
                SubmittedByOfficerStartDate AS submittedByOfficerStartDate,
                ReviewedByAdminID AS reviewedByAdminId,
                SubmittedAt AS submittedAt,
                ReviewedAt AS reviewedAt,
                DecisionStatus AS decisionStatus,
                DecisionNotes AS decisionNotes
            FROM APPROVAL
            ORDER BY SubmittedAt DESC, EventID
        """),
    }

    academic_terms = fetch_all_dict(cursor, """
        SELECT
            TermID AS termId,
            TermName AS termName,
            StartDate AS startDate,
            EndDate AS endDate
        FROM ACADEMIC_TERM
        ORDER BY StartDate DESC
        LIMIT 1
    """)

    data["academicTerm"] = academic_terms[0] if academic_terms else {}
    data["reports"] = build_reports(cursor)

    cursor.close()
    conn.close()

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
