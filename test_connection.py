import cx_Oracle

# Replace with your actual credentials and service name
dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE")  # or "ORCL"
try:
    conn = cx_Oracle.connect(user="system", password="new_password", dsn=dsn)
    cursor = conn.cursor()
    cursor.execute("SELECT 'Connection Successful' FROM dual")
    result = cursor.fetchone()
    print(result[0])
    conn.close()
except cx_Oracle.DatabaseError as e:
    error, = e.args
    print("Connection failed:")
    print("Code:", error.code)
    print("Message:", error.message)
