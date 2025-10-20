from db_config import get_db_connection  # Assumes your db_config.py

# SQL to create table and insert data
sql_create = """
CREATE TABLE IF NOT EXISTS resource_deliveries (
    delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_username TEXT NOT NULL,
    item TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (volunteer_username) REFERENCES users(username)
);
"""

sql_insert = """
INSERT OR IGNORE INTO resource_deliveries (volunteer_username, item, quantity, status) 
VALUES ('volunteer', 'Water Bottles', 10, 'pending');
INSERT OR IGNORE INTO resource_deliveries (volunteer_username, item, quantity, status) 
VALUES ('volunteer', 'Medical Kit', 5, 'pending');
"""

conn = get_db_connection()
cursor = conn.cursor()

try:
    cursor.execute(sql_create)
    cursor.executescript(sql_insert)  # Multiple inserts
    conn.commit()
    print("✅ Table 'resource_deliveries' created and sample data inserted!")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()
