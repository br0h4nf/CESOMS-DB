import mysql.connector
from mysql.connector import Error


def main():
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="bradroot#",
            database="campus_event_db"
        )

        if conn.is_connected():
            print("Connected to database.")
        else:
            print("Failed to connect to database.")
            return

        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO STUDENT
        (StudentID, FirstName, LastName, Email, ClassYear, Major, AccountStatus)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        new_student = (
            7,
            "Reid",
            "Howe",
            "reid@vt.edu",
            "Junior",
            "CS",
            "Active"
        )

        cursor.execute(insert_sql, new_student)
        conn.commit()

        print(f"{cursor.rowcount} row inserted successfully.")

        cursor.execute("SELECT * FROM STUDENT WHERE StudentID = %s", (6,))
        result = cursor.fetchone()

        print("Inserted row:")
        print(result)

    except Error as e:
        print("Database error:", e)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()