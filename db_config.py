import sqlite3
import os
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

# Database file path
DATABASE = 'drms.db'

def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
    return conn

def init_db():
    """Initialize the database by creating all necessary tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table (for authentication and roles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'volunteer', 'user')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create SOS requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sos_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'in_progress', 'resolved')),
            risk_level TEXT DEFAULT 'N/A' CHECK (risk_level IN ('Low', 'Medium', 'High', 'N/A')),
            assigned_to TEXT DEFAULT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create notifications table (for real-time alerts, if needed)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            sos_id INTEGER,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (sos_id) REFERENCES sos_requests (id)
        )
    ''')
    
    # FIXED: Updated resources table schema for inventory management
    # Drop existing table if it has the old schema to apply new one
    cursor.execute("DROP TABLE IF EXISTS resources")
    cursor.execute('''
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Available', 'Low', 'Out of Stock')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized successfully.")

def ensure_users_schema():
    """Check and fix users table schema if needed (dev migration)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        logger.warning("⚠️ Users table missing. Recreating...")
        init_db()  # This will create it
        return
    
    # Check if 'id' column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]  # Column names
    if 'id' not in columns:
        logger.warning("⚠️ 'id' column missing in users table. Dropping and recreating table (data will be lost).")
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        init_db()  # Recreate with correct schema
    else:
        logger.info("✅ Users table schema is correct.")
    
    conn.close()

def create_default_users():
    """Create default users for admin, volunteer, and user roles if they don't exist."""
    # Ensure schema is correct first
    ensure_users_schema()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Default credentials (change these in production!)
    default_users = [
        ('admin', 'admin123', 'admin'),
        ('volunteer', 'volunteer123', 'volunteer'),
        ('user', 'user123', 'user')
    ]
    
    for username, password, role in default_users:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            logger.info(f"✅ Default user created: {username} (role: {role})")
        else:
            logger.info(f"ℹ️ Default user already exists: {username} (role: {role})")
    
    conn.commit()
    conn.close()
    logger.info("✅ Default users setup completed.")

# Ensure database file exists in the project root (auto-init on import)
# This block will now drop and recreate the 'resources' table if it exists
if not os.path.exists(DATABASE):
    init_db()
    create_default_users()
else:
    # If DB exists, ensure resources table is updated.
    # This is a simple way to force schema update for 'resources' table.
    # For production, use proper schema migration tools (e.g., Alembic).
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS resources") # Drop the old one
    cursor.execute('''
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Available', 'Low', 'Out of Stock')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ Existing database 'resources' table schema updated.")
    create_default_users() # Ensure default users are still there
