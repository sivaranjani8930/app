from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from db_config import get_db_connection
from flask_socketio import emit  # For real-time emit (optional)
import logging
from datetime import datetime

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')
logger = logging.getLogger(__name__)

# Simple keyword-based AI responses (expand as needed)
def generate_ai_response(message):
    message_lower = message.lower().strip()
    
    if 'sos' in message_lower or 'emergency' in message_lower:
        return "🚨 **SOS Feature**: Use the SOS form to report emergencies with your location. Admins/volunteers will respond quickly. Go to /sos to submit."
    elif 'help' in message_lower or 'disaster' in message_lower:
        return "🆘 **Emergency Help**: For floods, earthquakes, or fires, submit an SOS alert. Resources: Check /resources for shelters and hotlines. Stay safe!"
    elif 'weather' in message_lower or 'prediction' in message_lower:
        return "🌦 **Weather/Disaster Prediction**: Use the AI Prediction tool at /predict to assess risks based on your location."
    elif 'login' in message_lower or 'register' in message_lower:
        return "🔐 **Account Help**: Login at /auth/login or register at /auth/register. Default users: admin/admin, user/user."
    elif 'contact' in message_lower or 'help line' in message_lower:
        return "🔐 **Emergency no.**: 90023 90023."
    else:
        return "I'm sorry, I don't have specific advice for that. For emergencies, submit an SOS or contact local authorities. What else can I help with?"

@chatbot_bp.route('/', methods=['GET', 'POST'])
def chatbot():
    if 'username' not in session:
        flash("Please login first to use the chatbot.", "danger")
        return redirect(url_for('login.login'))
    
    username = session.get('username')
    role = session.get('role', 'user')
    if role != 'user':
        flash("Chatbot access restricted to users only.", "danger")
        return redirect(url_for('login.login'))
    
    messages = []  # Chat history (load from DB if exists)
    
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        
        if not user_message:
            flash("Please enter a message.", "warning")
            return render_template('chatbot.html', username=username, messages=messages)
        
        if len(user_message) > 500:  # Limit length
            flash("Message too long. Keep it under 500 characters.", "warning")
            return render_template('chatbot.html', username=username, messages=messages)
        
        try:
            # Generate AI response
            bot_response = generate_ai_response(user_message)
            
            # Log to DB (optional - skip if table missing)
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO chat_logs (user_id, message, response, timestamp)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (session.get('user_id'), user_message, bot_response))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"Chat logged for user {username}: {user_message}")
            except Exception as db_e:
                logger.warning(f"DB log failed for chat (non-critical): {db_e}")  # FIXED: No crash if DB fails
            
            # Flash responses (for template display)
            flash(f"You: {user_message}", "info")
            flash(f"Bot: {bot_response}", "success")
            
            # Real-time emit via SocketIO (optional, for JS clients)
            try:
                emit('chat_response', {
                    'message': bot_response,
                    'user': username,
                    'timestamp': datetime.now().isoformat()
                }, broadcast=True)
                logger.info(f"✅ Chat response emitted for {username}: {user_message}")
            except Exception as emit_e:
                logger.warning(f"SocketIO emit failed (non-critical): {emit_e}")
            
        except Exception as e:
            logger.error(f"Chatbot error for {username}: {e}")
            flash("An error occurred while processing your message. Please try again.", "danger")
            bot_response = "Sorry, something went wrong. Try rephrasing your question."
            flash(f"Bot: {bot_response}", "success")
        
        # Redirect to self to show updated flashes/history
        return redirect(url_for('chatbot.chatbot'))
    
    # GET: Load page with welcome (load history if DB exists)
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message, response, timestamp FROM chat_logs 
                WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10
            """, (session.get('user_id'),))
            rows = cursor.fetchall()
            messages = [{'user': row[0], 'bot': row[1], 'time': row[2]} for row in rows]
            cursor.close()
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to load chat history: {e}")
        messages = []
    
    welcome_msg = f"Welcome, {username}! (Role: {role}) Ask about emergencies."
    flash(welcome_msg, "info")  # Show on first load
    
    return render_template('chatbot.html', username=username, messages=messages)

# Export blueprint
__all__ = ['chatbot_bp']
