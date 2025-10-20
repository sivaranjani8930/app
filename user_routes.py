from flask import Blueprint, render_template, session, redirect, url_for, flash
import logging

user_bp = Blueprint('user', __name__, url_prefix='/user')
logger = logging.getLogger(__name__)

@user_bp.route('/user_dashboard', methods=['GET'])  # Endpoint: 'user.user_dashboard' (for back links)
def user_dashboard():
    if 'username' not in session:
        flash("Please login first.", "danger")
        return redirect(url_for('login.login'))
    
    username = session.get('username')
    role = session.get('role', 'user')
    if role != 'user':
        flash("Access restricted to users only.", "danger")
        return redirect(url_for('login.login'))
    
    logger.info(f"User  dashboard loaded for {username}")
    return render_template('sos_form.html', username=username)  # Assumes sos_form.html is your dashboard template
