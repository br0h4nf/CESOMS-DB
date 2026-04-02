from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import mysql.connector
from datetime import date, datetime

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "bradroot#",
    "database": "campus_event_db"
}


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
        record = {}
        for i, col in enumerate(columns):
            record[col] = serialize_value(row[i])
        results.append(record)

    return results


def fetch_one(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchone()


def build_reports():
    return [
        {
            "reportType": "Participation Trend",
            "summary": "Student registration activity is being tracked live from current event and registration records.",
            "generatedAt": datetime.now().isoformat(),
            "generatedByAdminId": "ADM-01",
        },
        {
            "reportType": "Organization Activity",
            "summary": "Organizations with approved and scheduled events are highlighted in the dashboard.",
            "generatedAt": datetime.now().isoformat(),
            "generatedByAdminId": "ADM-01",
        },
    ]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    data = {}

    data["students"] = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        ORDER BY LastName, FirstName
    """)

    data["administrators"] = fetch_all_dict(cursor, """
        SELECT
            AdminID AS adminId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            Department AS department,
            AdminStatus AS adminStatus
        FROM ADMINISTRATOR
        ORDER BY LastName, FirstName
    """)

    data["organizations"] = fetch_all_dict(cursor, """
        SELECT
            OrgID AS orgId,
            OrgName AS orgName,
            Description AS description,
            ContactEmail AS contactEmail,
            OrgStatus AS orgStatus
        FROM ORGANIZATION
        ORDER BY OrgName
    """)

    data["organizationOfficers"] = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            OrgID AS orgId,
            StartDate AS startDate,
            RoleTitle AS roleTitle,
            EndDate AS endDate
        FROM ORGANIZATION_OFFICER
        ORDER BY StartDate DESC
    """)

    data["memberships"] = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            OrgID AS orgId,
            JoinDate AS joinDate,
            LeaveDate AS leaveDate,
            MemberRole AS memberRole
        FROM MEMBERSHIP
        ORDER BY JoinDate DESC
    """)

    data["locations"] = fetch_all_dict(cursor, """
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
        ORDER BY LocationName
    """)

    data["categories"] = fetch_all_dict(cursor, """
        SELECT
            CategoryID AS categoryId,
            CategoryName AS categoryName,
            Description AS description
        FROM EVENT_CATEGORY
        ORDER BY CategoryName
    """)

    data["events"] = fetch_all_dict(cursor, """
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
        ORDER BY StartDateTime
    """)

    data["registrations"] = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            EventID AS eventId,
            RegisteredAt AS registeredAt,
            RegistrationStatus AS registrationStatus
        FROM REGISTRATION
        ORDER BY RegisteredAt DESC
    """)

    data["attendance"] = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            EventID AS eventId,
            CheckInTime AS checkInTime,
            AttendanceFlag AS attendanceFlag,
            RecordedByOfficerStudentID AS recordedByOfficerStudentId,
            RecordedByOfficerOrgID AS recordedByOfficerOrgId,
            RecordedByOfficerStartDate AS recordedByOfficerStartDate
        FROM ATTENDANCE
        ORDER BY CheckInTime DESC
    """)

    data["approvals"] = fetch_all_dict(cursor, """
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
        ORDER BY SubmittedAt DESC
    """)

    term_rows = fetch_all_dict(cursor, """
        SELECT
            TermID AS termId,
            TermName AS termName,
            StartDate AS startDate,
            EndDate AS endDate
        FROM ACADEMIC_TERM
        ORDER BY StartDate DESC
        LIMIT 1
    """)

    data["academicTerm"] = term_rows[0] if term_rows else {}
    data["reports"] = build_reports()

    cursor.close()
    conn.close()

    return jsonify(data)


@app.route("/api/register", methods=["POST"])
def register_event():
    body = request.get_json(silent=True) or {}
    student_id = body.get("studentId")
    event_id = body.get("eventId")

    if not student_id or not event_id:
        return jsonify({"error": "studentId and eventId are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        event_row = fetch_one(cursor, """
            SELECT Capacity, EventStatus
            FROM EVENT
            WHERE EventID = %s
        """, (event_id,))

        if not event_row:
            return jsonify({"error": f"Event {event_id} not found"}), 404

        capacity, event_status = event_row

        if event_status not in ("Approved", "Scheduled"):
            return jsonify({"error": f"Event status is {event_status}, not open for registration"}), 400

        student_row = fetch_one(cursor, """
            SELECT StudentID
            FROM STUDENT
            WHERE StudentID = %s
        """, (student_id,))

        if not student_row:
            return jsonify({"error": f"Student {student_id} not found"}), 404

        existing_row = fetch_one(cursor, """
            SELECT RegistrationStatus
            FROM REGISTRATION
            WHERE StudentID = %s AND EventID = %s
        """, (student_id, event_id))

        registered_count_row = fetch_one(cursor, """
            SELECT COUNT(*)
            FROM REGISTRATION
            WHERE EventID = %s AND RegistrationStatus = 'Registered'
        """, (event_id,))

        registered_count = registered_count_row[0] if registered_count_row else 0
        new_status = "Registered" if registered_count < capacity else "Waitlisted"

        if existing_row:
            old_status = existing_row[0]

            if old_status == "Registered":
                return jsonify({"status": "Registered"})

            if old_status == "Waitlisted":
                return jsonify({"status": "Waitlisted"})

            cursor.execute("""
                UPDATE REGISTRATION
                SET RegisteredAt = NOW(),
                    RegistrationStatus = %s
                WHERE StudentID = %s AND EventID = %s
            """, (new_status, student_id, event_id))
        else:
            cursor.execute("""
                INSERT INTO REGISTRATION (StudentID, EventID, RegisteredAt, RegistrationStatus)
                VALUES (%s, %s, NOW(), %s)
            """, (student_id, event_id, new_status))

        conn.commit()
        return jsonify({"status": new_status})

    except mysql.connector.Error as e:
        conn.rollback()
        print("MYSQL REGISTER ERROR:", e)
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        conn.rollback()
        print("GENERAL REGISTER ERROR:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route("/api/cancel-registration", methods=["POST"])
def cancel_registration():
    body = request.get_json(silent=True) or {}
    student_id = body.get("studentId")
    event_id = body.get("eventId")

    if not student_id or not event_id:
        return jsonify({"error": "studentId and eventId are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        existing_row = fetch_one(cursor, """
            SELECT RegistrationStatus
            FROM REGISTRATION
            WHERE StudentID = %s AND EventID = %s
        """, (student_id, event_id))

        if not existing_row:
            return jsonify({"error": "Registration not found"}), 404

        cursor.execute("""
            UPDATE REGISTRATION
            SET RegistrationStatus = 'Cancelled'
            WHERE StudentID = %s AND EventID = %s
        """, (student_id, event_id))

        # Promote first waitlisted student, if there is space now
        capacity_row = fetch_one(cursor, """
            SELECT Capacity
            FROM EVENT
            WHERE EventID = %s
        """, (event_id,))

        registered_count_row = fetch_one(cursor, """
            SELECT COUNT(*)
            FROM REGISTRATION
            WHERE EventID = %s AND RegistrationStatus = 'Registered'
        """, (event_id,))

        capacity = capacity_row[0] if capacity_row else 0
        registered_count = registered_count_row[0] if registered_count_row else 0

        if registered_count < capacity:
            waitlisted_row = fetch_one(cursor, """
                SELECT StudentID
                FROM REGISTRATION
                WHERE EventID = %s AND RegistrationStatus = 'Waitlisted'
                ORDER BY RegisteredAt ASC
                LIMIT 1
            """, (event_id,))

            if waitlisted_row:
                promoted_student_id = waitlisted_row[0]
                cursor.execute("""
                    UPDATE REGISTRATION
                    SET RegistrationStatus = 'Registered'
                    WHERE StudentID = %s AND EventID = %s
                """, (promoted_student_id, event_id))

        conn.commit()
        return jsonify({"status": "Cancelled"})

    except mysql.connector.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)