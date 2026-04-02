from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'phase5_secret_key'  # Required for session management


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="bradroot#",
        database="campus_event_db"
    )


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/events")
def events():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                e.EventID,
                e.Title,
                e.Description,
                e.StartDateTime,
                e.EndDateTime,
                e.Capacity,
                e.EventStatus,
                o.OrgName,
                l.LocationName,
                ec.CategoryName,
                t.TermName
            FROM EVENT e
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            JOIN LOCATION l ON e.LocationID = l.LocationID
            JOIN EVENT_CATEGORY ec ON e.CategoryID = ec.CategoryID
            JOIN ACADEMIC_TERM t ON e.TermID = t.TermID
            WHERE e.EventStatus IN ('Approved', 'Scheduled')
            ORDER BY e.StartDateTime
        """)

        events_data = cursor.fetchall()
        return render_template("events.html", events=events_data)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/add-student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        conn = None
        cursor = None
        try:
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            email = request.form["email"]
            class_year = request.form["class_year"]
            major = request.form["major"]
            account_status = request.form["account_status"]

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT MAX(StudentID) FROM STUDENT")
            max_id = cursor.fetchone()[0]
            new_student_id = 1 if max_id is None else max_id + 1

            sql = """
                INSERT INTO STUDENT
                (StudentID, FirstName, LastName, Email, ClassYear, Major, AccountStatus)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                new_student_id,
                first_name,
                last_name,
                email,
                class_year,
                major,
                account_status
            )

            cursor.execute(sql, values)
            conn.commit()

            return render_template(
                "message.html",
                title="Success",
                message=f"Student added successfully with StudentID {new_student_id}."
            )

        except Error as e:
            return render_template("message.html", title="Error", message=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template("add_student.html")


@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT EventID, Title, EventStatus
            FROM EVENT
            WHERE EventID = %s
        """, (event_id,))
        event = cursor.fetchone()

        if not event:
            return render_template("message.html", title="Error", message="Event not found.")

        if request.method == "POST":
            student_id = request.form["student_id"]

            cursor.execute("SELECT * FROM STUDENT WHERE StudentID = %s", (student_id,))
            student = cursor.fetchone()

            if not student:
                return render_template("message.html", title="Error", message="Student ID does not exist.")

            cursor.execute("""
                SELECT * FROM REGISTRATION
                WHERE StudentID = %s AND EventID = %s
            """, (student_id, event_id))
            existing = cursor.fetchone()

            if existing:
                return render_template("message.html", title="Notice", message="Student is already registered for this event.")

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO REGISTRATION (StudentID, EventID, RegisteredAt, RegistrationStatus)
                VALUES (%s, %s, NOW(), %s)
            """, (student_id, event_id, "Registered"))
            conn.commit()

            return render_template(
                "message.html",
                title="Success",
                message=f"Student {student_id} successfully registered for event {event_id}."
            )

        return render_template("register.html", event=event)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            org_id = request.form["org_id"]
            location_id = request.form["location_id"]
            category_id = request.form["category_id"]
            term_id = request.form["term_id"]
            title = request.form["title"]
            description = request.form["description"]
            capacity = request.form["capacity"]
            start_datetime = request.form["start_datetime"]
            end_datetime = request.form["end_datetime"]

            cursor.execute("SELECT MAX(EventID) FROM EVENT")
            max_id = cursor.fetchone()["MAX(EventID)"]
            new_event_id = 1 if max_id is None else max_id + 1

            insert_cursor = conn.cursor()
            insert_cursor.execute("""
                INSERT INTO EVENT
                (EventID, OrgID, LocationID, CategoryID, TermID, Title, Description, Capacity,
                 StartDateTime, EndDateTime, EventStatus)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                new_event_id,
                org_id,
                location_id,
                category_id,
                term_id,
                title,
                description,
                capacity,
                start_datetime,
                end_datetime,
                "Submitted"
            ))
            conn.commit()
            insert_cursor.close()

            return render_template(
                "message.html",
                title="Success",
                message=f"Event created successfully with EventID {new_event_id}. Status set to Submitted."
            )

        cursor.execute("SELECT OrgID, OrgName FROM ORGANIZATION ORDER BY OrgName")
        organizations = cursor.fetchall()

        cursor.execute("SELECT LocationID, LocationName FROM LOCATION ORDER BY LocationName")
        locations = cursor.fetchall()

        cursor.execute("SELECT CategoryID, CategoryName FROM EVENT_CATEGORY ORDER BY CategoryName")
        categories = cursor.fetchall()

        cursor.execute("SELECT TermID, TermName FROM ACADEMIC_TERM ORDER BY StartDate")
        terms = cursor.fetchall()

        return render_template(
            "create_event.html",
            organizations=organizations,
            locations=locations,
            categories=categories,
            terms=terms
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/admin/approvals")
def admin_approvals():

    if session.get("user_role") != "admin":
        return render_template(
        "message.html",
        title="Access Denied",
        message="You must be logged in as an administrator to perform this action."
    )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                e.EventID,
                e.Title,
                e.StartDateTime,
                e.EndDateTime,
                e.EventStatus,
                o.OrgName
            FROM EVENT e
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            WHERE e.EventStatus = 'Submitted'
            ORDER BY e.StartDateTime
        """)
        submitted_events = cursor.fetchall()

        return render_template("admin_approvals.html", events=submitted_events)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/admin/approve/<int:event_id>", methods=["POST"])
def approve_event(event_id):
    conn = None
    cursor = None
    try:
        reviewed_by_admin_id = request.form["admin_id"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT EventID, OrgID
            FROM EVENT
            WHERE EventID = %s
        """, (event_id,))
        event = cursor.fetchone()

        if not event:
            return render_template("message.html", title="Error", message="Event not found.")

        cursor.execute("""
            SELECT StudentID, OrgID, StartDate
            FROM ORGANIZATION_OFFICER
            WHERE OrgID = %s
            ORDER BY StartDate
            LIMIT 1
        """, (event["OrgID"],))
        officer = cursor.fetchone()

        if not officer:
            return render_template("message.html", title="Error", message="No organization officer found for this event's organization.")

        update_cursor = conn.cursor()
        update_cursor.execute("""
            UPDATE EVENT
            SET EventStatus = 'Approved'
            WHERE EventID = %s
        """, (event_id,))

        update_cursor.execute("""
            INSERT INTO APPROVAL
            (EventID, SubmittedByOfficerStudentID, SubmittedByOfficerOrgID, SubmittedByOfficerStartDate,
             ReviewedByAdminID, SubmittedAt, ReviewedAt, DecisionStatus, DecisionNotes)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                ReviewedByAdminID = VALUES(ReviewedByAdminID),
                ReviewedAt = VALUES(ReviewedAt),
                DecisionStatus = VALUES(DecisionStatus),
                DecisionNotes = VALUES(DecisionNotes)
        """, (
            event_id,
            officer["StudentID"],
            officer["OrgID"],
            officer["StartDate"],
            reviewed_by_admin_id,
            "Approved",
            "Approved through admin interface"
        ))

        conn.commit()
        update_cursor.close()

        return redirect(url_for("admin_approvals"))

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/admin/reject/<int:event_id>", methods=["POST"])
def reject_event(event_id):
    conn = None
    cursor = None
    try:
        reviewed_by_admin_id = request.form["admin_id"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT EventID, OrgID
            FROM EVENT
            WHERE EventID = %s
        """, (event_id,))
        event = cursor.fetchone()

        if not event:
            return render_template("message.html", title="Error", message="Event not found.")

        cursor.execute("""
            SELECT StudentID, OrgID, StartDate
            FROM ORGANIZATION_OFFICER
            WHERE OrgID = %s
            ORDER BY StartDate
            LIMIT 1
        """, (event["OrgID"],))
        officer = cursor.fetchone()

        if not officer:
            return render_template("message.html", title="Error", message="No organization officer found for this event's organization.")

        update_cursor = conn.cursor()
        update_cursor.execute("""
            UPDATE EVENT
            SET EventStatus = 'Rejected'
            WHERE EventID = %s
        """, (event_id,))

        update_cursor.execute("""
            INSERT INTO APPROVAL
            (EventID, SubmittedByOfficerStudentID, SubmittedByOfficerOrgID, SubmittedByOfficerStartDate,
             ReviewedByAdminID, SubmittedAt, ReviewedAt, DecisionStatus, DecisionNotes)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                ReviewedByAdminID = VALUES(ReviewedByAdminID),
                ReviewedAt = VALUES(ReviewedAt),
                DecisionStatus = VALUES(DecisionStatus),
                DecisionNotes = VALUES(DecisionNotes)
        """, (
            event_id,
            officer["StudentID"],
            officer["OrgID"],
            officer["StartDate"],
            reviewed_by_admin_id,
            "Rejected",
            "Rejected through admin interface"
        ))

        conn.commit()
        update_cursor.close()

        return redirect(url_for("admin_approvals"))

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/students")
def students():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT StudentID, FirstName, LastName, Email, ClassYear, Major, AccountStatus
            FROM STUDENT
            ORDER BY LastName, FirstName
        """)
        students_data = cursor.fetchall()

        return render_template("students.html", students=students_data)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/student/<int:student_id>")
def student_profile(student_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT StudentID, FirstName, LastName, Email, ClassYear, Major, AccountStatus
            FROM STUDENT
            WHERE StudentID = %s
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            return render_template("message.html", title="Error", message="Student not found.")

        return render_template("student_profile.html", student=student)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/student/<int:student_id>/registrations")
def student_registrations(student_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT StudentID, FirstName, LastName
            FROM STUDENT
            WHERE StudentID = %s
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            return render_template("message.html", title="Error", message="Student not found.")

        cursor.execute("""
            SELECT 
                r.EventID,
                r.RegisteredAt,
                r.RegistrationStatus,
                e.Title,
                e.StartDateTime,
                e.EndDateTime,
                e.EventStatus,
                o.OrgName,
                l.LocationName
            FROM REGISTRATION r
            JOIN EVENT e ON r.EventID = e.EventID
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            JOIN LOCATION l ON e.LocationID = l.LocationID
            WHERE r.StudentID = %s
            ORDER BY e.StartDateTime
        """, (student_id,))
        registrations = cursor.fetchall()

        return render_template(
            "student_registrations.html",
            student=student,
            registrations=registrations
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/student/<int:student_id>/memberships")
def student_memberships(student_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT StudentID, FirstName, LastName
            FROM STUDENT
            WHERE StudentID = %s
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            return render_template("message.html", title="Error", message="Student not found.")

        cursor.execute("""
            SELECT
                m.OrgID,
                m.JoinDate,
                m.LeaveDate,
                m.MemberRole,
                o.OrgName,
                o.Description,
                o.OrgStatus
            FROM MEMBERSHIP m
            JOIN ORGANIZATION o ON m.OrgID = o.OrgID
            WHERE m.StudentID = %s
            ORDER BY o.OrgName
        """, (student_id,))
        memberships = cursor.fetchall()

        return render_template(
            "student_memberships.html",
            student=student,
            memberships=memberships
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/student/events")
def student_event_search():
    conn = None
    cursor = None
    try:
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        organization = request.args.get("organization", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT CategoryID, CategoryName
            FROM EVENT_CATEGORY
            ORDER BY CategoryName
        """)
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT OrgID, OrgName
            FROM ORGANIZATION
            ORDER BY OrgName
        """)
        organizations = cursor.fetchall()

        query = """
            SELECT
                e.EventID,
                e.Title,
                e.Description,
                e.StartDateTime,
                e.EndDateTime,
                e.Capacity,
                e.EventStatus,
                o.OrgName,
                l.LocationName,
                ec.CategoryName,
                t.TermName
            FROM EVENT e
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            JOIN LOCATION l ON e.LocationID = l.LocationID
            JOIN EVENT_CATEGORY ec ON e.CategoryID = ec.CategoryID
            JOIN ACADEMIC_TERM t ON e.TermID = t.TermID
            WHERE e.EventStatus IN ('Approved', 'Scheduled')
        """

        params = []

        if search:
            query += " AND (e.Title LIKE %s OR e.Description LIKE %s)"
            like_value = f"%{search}%"
            params.extend([like_value, like_value])

        if category:
            query += " AND e.CategoryID = %s"
            params.append(category)

        if organization:
            query += " AND e.OrgID = %s"
            params.append(organization)

        query += " ORDER BY e.StartDateTime"

        cursor.execute(query, params)
        events = cursor.fetchall()

        return render_template(
            "student_event_search.html",
            events=events,
            categories=categories,
            organizations=organizations,
            selected_search=search,
            selected_category=category,
            selected_organization=organization
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/student/register", methods=["GET", "POST"])
def student_self_register():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            student_id = request.form["student_id"]
            event_id = request.form["event_id"]

            cursor.execute("""
                SELECT StudentID, FirstName, LastName
                FROM STUDENT
                WHERE StudentID = %s
            """, (student_id,))
            student = cursor.fetchone()

            if not student:
                return render_template("message.html", title="Error", message="Student ID does not exist.")

            cursor.execute("""
                SELECT EventID, Title, EventStatus
                FROM EVENT
                WHERE EventID = %s
            """, (event_id,))
            event = cursor.fetchone()

            if not event:
                return render_template("message.html", title="Error", message="Selected event does not exist.")

            if event["EventStatus"] not in ("Approved", "Scheduled"):
                return render_template("message.html", title="Error", message="Only approved or scheduled events may be registered for.")

            cursor.execute("""
                SELECT *
                FROM REGISTRATION
                WHERE StudentID = %s AND EventID = %s
            """, (student_id, event_id))
            existing = cursor.fetchone()

            if existing:
                return render_template("message.html", title="Notice", message="This student is already registered for the selected event.")

            insert_cursor = conn.cursor()
            insert_cursor.execute("""
                INSERT INTO REGISTRATION (StudentID, EventID, RegisteredAt, RegistrationStatus)
                VALUES (%s, %s, NOW(), %s)
            """, (student_id, event_id, "Registered"))
            conn.commit()
            insert_cursor.close()

            return render_template(
                "message.html",
                title="Success",
                message=f"{student['FirstName']} {student['LastName']} was successfully registered for {event['Title']}."
            )

        cursor.execute("""
            SELECT
                e.EventID,
                e.Title,
                e.StartDateTime,
                e.EndDateTime,
                o.OrgName,
                l.LocationName,
                ec.CategoryName
            FROM EVENT e
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            JOIN LOCATION l ON e.LocationID = l.LocationID
            JOIN EVENT_CATEGORY ec ON e.CategoryID = ec.CategoryID
            WHERE e.EventStatus IN ('Approved', 'Scheduled')
            ORDER BY e.StartDateTime
        """)
        events = cursor.fetchall()

        return render_template("student_self_register.html", events=events)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/student/<int:student_id>/cancel-registration/<int:event_id>", methods=["POST"])
def cancel_registration(student_id, event_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM REGISTRATION
            WHERE StudentID = %s AND EventID = %s
        """, (student_id, event_id))
        registration = cursor.fetchone()

        if not registration:
            return render_template(
                "message.html",
                title="Error",
                message="Registration record not found."
            )

        update_cursor = conn.cursor()
        update_cursor.execute("""
            UPDATE REGISTRATION
            SET RegistrationStatus = 'Cancelled'
            WHERE StudentID = %s AND EventID = %s
        """, (student_id, event_id))
        conn.commit()
        update_cursor.close()

        return render_template(
            "message.html",
            title="Success",
            message=f"Registration for student {student_id} and event {event_id} was cancelled successfully."
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/admin")
def admin_dashboard():

    if session.get("user_role") != "admin":
        return render_template(
        "message.html",
        title="Access Denied",
        message="You must be logged in as an administrator to perform this action."
    )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS submitted_count
            FROM EVENT
            WHERE EventStatus = 'Submitted'
        """)
        submitted_count = cursor.fetchone()["submitted_count"]

        cursor.execute("""
            SELECT COUNT(*) AS approved_count
            FROM EVENT
            WHERE EventStatus = 'Approved'
        """)
        approved_count = cursor.fetchone()["approved_count"]

        cursor.execute("""
            SELECT COUNT(*) AS rejected_count
            FROM EVENT
            WHERE EventStatus = 'Rejected'
        """)
        rejected_count = cursor.fetchone()["rejected_count"]

        cursor.execute("""
            SELECT COUNT(*) AS admin_count
            FROM ADMINISTRATOR
        """)
        admin_count = cursor.fetchone()["admin_count"]

        return render_template(
            "admin_dashboard.html",
            submitted_count=submitted_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            admin_count=admin_count
        )

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/admin/events")
def admin_events():

    if session.get("user_role") != "admin":
        return render_template(
        "message.html",
        title="Access Denied",
        message="You must be logged in as an administrator to perform this action."
    )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                e.EventID,
                e.Title,
                e.StartDateTime,
                e.EndDateTime,
                e.EventStatus,
                o.OrgName,
                l.LocationName,
                ec.CategoryName
            FROM EVENT e
            JOIN ORGANIZATION o ON e.OrgID = o.OrgID
            JOIN LOCATION l ON e.LocationID = l.LocationID
            JOIN EVENT_CATEGORY ec ON e.CategoryID = ec.CategoryID
            ORDER BY e.StartDateTime
        """)
        events = cursor.fetchall()

        return render_template("admin_events.html", events=events)

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/login", methods=["GET", "POST"])
def login():
    conn = None
    cursor = None
    try:
        if request.method == "POST":
            user_type = request.form["user_type"]
            user_id = request.form["user_id"]

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if user_type == "admin":
                cursor.execute("""
                    SELECT AdminID, FirstName, LastName
                    FROM ADMINISTRATOR
                    WHERE AdminID = %s
                """, (user_id,))
                user = cursor.fetchone()

                if user:
                    session["user_id"] = user["AdminID"]
                    session["user_role"] = "admin"
                    session["user_name"] = f"{user['FirstName']} {user['LastName']}"
                    return redirect(url_for("admin_dashboard"))

            elif user_type == "student":
                cursor.execute("""
                    SELECT StudentID, FirstName, LastName
                    FROM STUDENT
                    WHERE StudentID = %s
                """, (user_id,))
                user = cursor.fetchone()

                if user:
                    session["user_id"] = user["StudentID"]
                    session["user_role"] = "student"
                    session["user_name"] = f"{user['FirstName']} {user['LastName']}"
                    return redirect(url_for("students"))

            return render_template("message.html", title="Login Failed", message="Invalid ID or role.")

        return render_template("login.html")

    except Error as e:
        return render_template("message.html", title="Database Error", message=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)