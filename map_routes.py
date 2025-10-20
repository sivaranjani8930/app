# routes/map_routes.py
from flask import Blueprint, jsonify, render_template
from db_config import get_db_connection

map_bp = Blueprint('map', __name__)

@map_bp.route('/')
def map_home():
    """Render the map page."""
    return render_template('map.html')

@map_bp.route('/sos_locations')
def sos_locations():
    """Return all SOS requests with coordinates for map plotting."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, latitude, longitude, description, status, risk_level FROM sos_requests")
    
    sos_data_raw = cursor.fetchall() # FIX: Fetch raw rows
    # FIX: Convert sqlite3.Row objects to dictionaries for JSON serialization
    sos_data = [
        {
            "id": row['id'], # Access by column name
            "username": row['username'],
            "latitude": row['latitude'],
            "longitude": row['longitude'],
            "description": row['description'],
            "status": row['status'],
            "risk_level": row['risk_level']
        }
        for row in sos_data_raw # Iterate over raw rows
    ]
    
    conn.close()
    return jsonify(sos_data)
