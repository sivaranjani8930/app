from flask import Blueprint, render_template, session, redirect, url_for
from extensions import socketio  # Optional

notify_bp = Blueprint('notify', __name__)

@notify_bp.route('/dashboard')
def notify_dashboard():
    if 'username' not in session or session['role'] not in ['admin', 'volunteer']:
        return redirect(url_for('login.login'))
    
    # Fetch notifications from DB (example)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE role = ?", (session['role'],))
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('notifications.html', notifications=notifications)

@notify_bp.route('/send', methods=['POST'])
def send_notification():
    # Example: Send via SocketIO
    message = request.form.get('message')
    socketio.emit('send_notification', {'message': message, 'from': session['username']})
    flash("Notification sent!", "success")
    return redirect(url_for('notify.notify_dashboard'))
