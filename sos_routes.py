from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from db_config import get_db_connection
import logging
import os
import numpy as np
import random
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sos_bp = Blueprint('sos', __name__, url_prefix='/sos')
logger = logging.getLogger(__name__)

# --- AI Prediction Model Integration ---
model_path = os.path.join("models", "disaster_model.pkl")
prediction_model = None
risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'}

def train_and_save_dummy_model_for_sos():
    logger.warning("⚠️ No trained model found for SOS prediction. Training a dummy model.")
    data = {
        'rainfall': [10, 50, 100, 5, 80, 60, 20, 150, 30, 70],
        'temperature': [25, 30, 35, 20, 40, 28, 32, 38, 27, 33],
        'humidity': [60, 80, 90, 50, 95, 70, 65, 98, 75, 88],
        'risk_level': ['Low', 'Medium', 'High', 'Low', 'High', 'Medium', 'Low', 'High', 'Medium', 'High']
    }
    df = pd.DataFrame(data)
    risk_mapping = {'Low': 0, 'Medium': 1, 'High': 2}
    df['risk_encoded'] = df['risk_level'].map(risk_mapping)
    X = df[['rainfall', 'temperature', 'humidity']]
    y = df['risk_encoded']
    dummy_model = RandomForestClassifier(n_estimators=10, random_state=42)
    dummy_model.fit(X, y)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(dummy_model, model_path)
    logger.info("✅ Dummy disaster prediction model trained and saved for SOS.")
    return dummy_model, {v: k for k, v in risk_mapping.items()}

try:
    if os.path.exists(model_path):
        prediction_model = joblib.load(model_path)
        risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'}
        logger.info("✅ Disaster prediction model loaded successfully for SOS.")
    else:
        prediction_model, risk_level_labels = train_and_save_dummy_model_for_sos()
except Exception as e:
    logger.error(f"⚠️ Error loading model for SOS prediction: {e}. Falling back to dummy mode.")
    prediction_model = None

def get_environmental_data(latitude, longitude):
    if 10 <= latitude <= 15 and 75 <= longitude <= 85:
        rainfall = random.uniform(50, 150)
        temperature = random.uniform(25, 35)
        humidity = random.uniform(70, 95)
    elif 20 <= latitude <= 25 and 70 <= longitude <= 80:
        rainfall = random.uniform(10, 80)
        temperature = random.uniform(30, 40)
        humidity = random.uniform(50, 80)
    else:
        rainfall = random.uniform(0, 100)
        temperature = random.uniform(20, 40)
        humidity = random.uniform(40, 90)
    return rainfall, temperature, humidity

@sos_bp.route('/', methods=['GET', 'POST'])  # URL: /sos (simple, no sub-path 404)
def sos_form():
    if 'username' not in session:
        flash("Please login first.", "danger")
        return redirect(url_for('login.login'))
    
    username = session.get('username')
    role = session.get('role', 'user')
    if role != 'user':
        flash("Access restricted to users only.", "danger")
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        lat = request.form.get('latitude', 13.0827)  # Default Chennai coords
        lng = request.form.get('longitude', 80.2707)
        
        if not description or len(description) < 10:
            flash("Description must be at least 10 characters.", "danger")
            return render_template('sos_form.html', username=username)
        
        try:
            lat = float(lat)
            lng = float(lng)
            # FIXED: Complete the syntax - closed all parentheses
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError("Invalid coordinates")
        except ValueError:
            flash("Invalid latitude/longitude. Use decimal degrees.", "danger")
            return render_template('sos_form.html', username=username)
        
        predicted_risk_level = 'Unknown'
        try:
            rainfall, temperature, humidity = get_environmental_data(lat, lng)
            if prediction_model:
                X = np.array([[rainfall, temperature, humidity]])
                prediction_encoded = prediction_model.predict(X)[0]
                predicted_risk_level = risk_level_labels.get(prediction_encoded, 'Unknown')
                logger.info(f"Auto-predicted risk for SOS at ({lat}, {lng}): {predicted_risk_level}")
            else:
                predicted_risk_level = random.choice(['Low', 'Medium', 'High'])
                logger.warning(f"Dummy auto-prediction for SOS: {predicted_risk_level} (Model not loaded)")
        except Exception as e:
            logger.error(f"Error during auto-prediction for SOS: {e}")
            predicted_risk_level = 'Error'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sos_requests (user_id, username, latitude, longitude, description, status, risk_level, timestamp)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, datetime('now'))
        """, (session['user_id'], username, lat, lng, description, predicted_risk_level))
        conn.commit()
        sos_id = cursor.lastrowid
        
        # Fetch the timestamp from the newly inserted row for the emit
        cursor.execute("SELECT timestamp FROM sos_requests WHERE id = ?", (sos_id,))
        timestamp = cursor.fetchone()[0]
        
        conn.close()
        
        flash(f"SOS alert sent successfully! ID: {sos_id}. Predicted Risk: {predicted_risk_level}. Help is on the way! 🚨", "success")
        
        # SocketIO emit with error handling
        try:
            # FIXED: Import socketio instance from app.py and use it explicitly
            from app import socketio
            if socketio:
                emitted_data = {
                    'id': sos_id,
                    'username': username,
                    'description': description,
                    'latitude': lat,
                    'longitude': lng,
                    'status': 'pending',
                    'risk_level': predicted_risk_level,
                    'timestamp': timestamp,
                    'assigned_to': None
                }
                logger.debug(f"Emitting new_sos_alert: {emitted_data}")
                socketio.emit('new_sos_alert', emitted_data, broadcast=True, include_self=False) # Use socketio.emit
                logger.info(f"✅ Real-time SOS alert broadcasted for ID {sos_id} by {username}")
            else:
                logger.warning("SocketIO instance not available for emit.")
        except ImportError:
            logger.warning("SocketIO not available (ImportError) – skipping real-time broadcast")
        except Exception as e:
            logger.error(f"⚠️ SocketIO broadcast failed for SOS {sos_id}: {e}")
        
        return redirect(url_for('sos.sos_form'))
    
    # GET: Render SOS form (with optional SOS button for dashboard integration)
    return render_template('sos_form.html', username=username)
