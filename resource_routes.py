from flask import Blueprint, render_template, session, redirect, url_for, flash
from db_config import get_db_connection
import logging

resource_bp = Blueprint('resources', __name__, url_prefix='/resources')
logger = logging.getLogger(__name__)

@resource_bp.route('/', methods=['GET'])  # Endpoint: 'resources.inventory' (matches template url_for)
def inventory():
    if 'username' not in session:
        flash("Please login first.", "danger")
        return redirect(url_for('login.login'))
    
    username = session.get('username')
    role = session.get('role', 'user')
    
    resources = []  # Load from DB
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, contact, category FROM resources ORDER BY category")
            resources = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info(f"Loaded {len(resources)} resources for {username}")
    except Exception as e:
        logger.error(f"Error loading resources: {e}")
        flash("Error loading resources. Please try again.", "danger")
        resources = [
            ("Emergency Hotline", "National Disaster Response: 112", "112", "Hotline"),
            ("Shelter Info", "Local shelters for floods/earthquakes", "Contact local admin", "Shelter"),
            ("Medical Aid", "Red Cross Emergency Services", "108", "Medical")
        ]  # Fallback dummy data
    
    return render_template('resources.html', username=username, resources=resources, role=role)

# Optional: Add more routes if needed (e.g., search resources)
@resource_bp.route('/search', methods=['GET', 'POST'])
def search_resources():
    # Similar to above - implement if needed
    return redirect(url_for('resources.inventory'))
