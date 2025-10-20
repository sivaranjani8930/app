import cx_Oracle

def get_db_connection():
    # Replace with your actual Oracle DB credentials
    dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE")  # or "ORCL"
    conn = cx_Oracle.connect(user="system", password="new_password", dsn=dsn)
    return conn

def get_pending_requests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sos_requests WHERE status = 'pending'")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# Test the function
if __name__ == "__main__":
    try:
        pending_requests = get_pending_requests()
        if pending_requests:
            print("Pending SOS Requests:")
            for request in pending_requests:
                print(request)
        else:
            print("No pending SOS requests found.")
    except cx_Oracle.DatabaseError as e:
        print("Database error occurred:", e)
