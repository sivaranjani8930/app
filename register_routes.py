from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import logging

register_bp = Blueprint('register', __name__)
logger = logging.getLogger(__name__)

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Fetch form data (No email – matches schema)
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')  # Default to 'user'; from dropdown
        
        # Validation
        if not username or len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template('register.html')
        
        if not password or len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template('register.html')
        
        if role not in ['user', 'admin', 'volunteer']:
            flash("Invalid role selected.", "danger")
            return render_template('register.html')
        
        # Check if username already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            flash("Username already exists. Please choose another.", "danger")
            conn.close()
            return render_template('register.html')
        
        # Hash the password
        password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
        
        # Insert new user (No email)
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, role) 
                VALUES (?, ?, ?)
            """, (username, password_hash, role))
            conn.commit()
            new_user_id = cursor.lastrowid
            conn.close()
            
            # Set session for auto-login
            session['username'] = username
            session['role'] = role
            session['user_id'] = new_user_id
            
            logger.info(f"✅ New user registered: {username} (Role: {role}, ID: {new_user_id})")
            
            # Role-based redirect (FIXED: Correct volunteer endpoint)
            if role == 'user':
                flash("Registration successful! Welcome to your dashboard.", "success")
                return redirect(url_for('user.user_dashboard'))  # Correct: 'user.user_dashboard'
            elif role == 'volunteer':
                flash("Registration successful! Access your volunteer dashboard.", "success")
                flash("Note: Volunteer role activated – contact admin for verification.", "warning")
                return redirect(url_for('volunteer.volunteer_dashboard'))  # FIXED: 'volunteer.volunteer_dashboard'
            elif role == 'admin':
                flash("Registration successful! Admin access granted.", "success")
                logger.warning(f"⚠️ New admin self-registered: {username} – Manual verification recommended.")
                flash("Admin role assigned – Please verify with system admin for security.", "warning")
                return redirect(url_for('admin.dashboard'))  # Correct: 'admin.dashboard'
        
        except Exception as e:
            if 'conn' in locals() and conn:  # Ensure connection is closed on error
                conn.close()
            flash(f"Registration failed: {str(e)}", "danger")
            logger.error(f"Registration error for {username}: {e}")
            return render_template('register.html')
    
    # GET: Show registration form
    return render_template('register.html')
