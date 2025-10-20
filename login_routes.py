from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime  # Added for potential session timeout logging

login_bp = Blueprint('login', __name__)
logger = logging.getLogger(__name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in (minor enhancement: prevent re-login)
    if 'username' in session:
        role = session.get('role', 'user')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'volunteer':
            return redirect(url_for('volunteer.volunteer_dashboard'))
        elif role == 'user':
            return redirect(url_for('user.user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template('login.html')
        
        # Check credentials in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            # Successful login
            session['username'] = username
            session['user_id'] = user[0]
            session['role'] = user[2]
            session['login_time'] = datetime.now().isoformat()  # Minor enhancement: Track login time for logging
            
            logger.info(f"✅ User logged in: {username} (Role: {user[2]}, ID: {user[0]})")
            
            # Role-based redirect (CONFIRMED CORRECT: Matches blueprint registrations in app.py)
            if user[2] == 'admin':
                flash("Welcome back, admin!", "success")
                return redirect(url_for('admin.dashboard'))  # Correct: /admin/dashboard
            elif user[2] == 'volunteer':
                flash("Welcome back, volunteer!", "success")
                return redirect(url_for('volunteer.volunteer_dashboard'))  # Correct: /volunteer/volunteer_dashboard
            elif user[2] == 'user':
                flash("Welcome back!", "success")
                return redirect(url_for('user.user_dashboard'))  # Correct: /user/dashboard (which redirects to SOS)
            else:
                # Minor enhancement: Clear session on invalid role for security
                flash("Invalid role. Contact admin.", "danger")
                session.clear()
                logger.warning(f"Invalid role detected for user: {username} (Role: {user[2]})")
                return redirect(url_for('login.login'))  # Correct: /auth/login
        else:
            flash("Invalid username or password.", "danger")
            logger.warning(f"Failed login attempt for: {username} at {datetime.now().isoformat()}")
            return render_template('login.html')
    
    # GET: Show login form
    # Minor enhancement: Clear any old session data on GET request
    if 'username' in session:
        session.clear()
    return render_template('login.html')
