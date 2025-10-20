from flask import Blueprint, request, render_template, redirect, url_for, flash, session
import os
import numpy as np
import random
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO)

predict_bp = Blueprint("predict", __name__, url_prefix='/predict')

# Path to the trained ML model
# Ensure 'models' directory exists in your project root
model_path = os.path.join("models", "disaster_model.pkl")
model = None
risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'} # Default labels

# Function to train and save a dummy model if not found
def train_and_save_dummy_model():
    logging.warning("⚠️ No trained model found. Training a dummy model for prediction.")
    # Create dummy data for training
    data = {
        'rainfall': [10, 50, 100, 5, 80, 60, 20, 150, 30, 70],
        'temperature': [25, 30, 35, 20, 40, 28, 32, 38, 27, 33],
        'humidity': [60, 80, 90, 50, 95, 70, 65, 98, 75, 88],
        'risk_level': ['Low', 'Medium', 'High', 'Low', 'High', 'Medium', 'Low', 'High', 'Medium', 'High']
    }
    df = pd.DataFrame(data)

    # Map risk levels to numerical values for training
    risk_mapping = {'Low': 0, 'Medium': 1, 'High': 2}
    df['risk_encoded'] = df['risk_level'].map(risk_mapping)

    X = df[['rainfall', 'temperature', 'humidity']]
    y = df['risk_encoded']

    # Train a simple RandomForestClassifier
    dummy_model = RandomForestClassifier(n_estimators=10, random_state=42)
    dummy_model.fit(X, y)

    # Save the dummy model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(dummy_model, model_path)
    logging.info("✅ Dummy disaster prediction model trained and saved.")
    return dummy_model, {v: k for k, v in risk_mapping.items()} # Return model and inverse mapping

# Load the trained ML model or train a dummy one
try:
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'} # Assuming this mapping
        logging.info("✅ Disaster prediction model loaded successfully.")
    else:
        model, risk_level_labels = train_and_save_dummy_model()
except Exception as e:
    logging.error(f"⚠️ Error loading model: {e}. Falling back to dummy mode.")
    model = None # Ensure model is None if loading fails

# ---------------------------
# 🔹 AI Prediction Route
# ---------------------------
@predict_bp.route("/", methods=["GET", "POST"]) # Changed to '/' for direct access
def predict():
    # Ensure user is logged in
    if 'username' not in session:
        flash("Please log in to access AI Prediction.", "danger")
        return redirect(url_for('login.login'))
    
    # Only 'user' role can access this feature
    if session.get('role') != 'user':
        flash("Access denied: Users only for AI Prediction.", "danger")
        return redirect(url_for('login.login'))

    result = None
    if request.method == 'POST':
        try:
            rainfall = float(request.form.get("rainfall"))
            temperature = float(request.form.get("temperature"))
            humidity = float(request.form.get("humidity"))

            if model:
                # Real ML prediction
                X = np.array([[rainfall, temperature, humidity]])
                prediction_encoded = model.predict(X)[0]
                result = risk_level_labels.get(prediction_encoded, 'Unknown')
                logging.info(f"AI Prediction for R:{rainfall}, T:{temperature}, H:{humidity}: {result}")
            else:
                # Dummy risk prediction if model failed to load/train
                risk_levels = ["Low", "Medium", "High"]
                result = random.choice(risk_levels)
                logging.warning(f"Dummy Prediction for R:{rainfall}, T:{temperature}, H:{humidity}: {result} (Model not loaded)")

        except ValueError:
            flash("❌ Invalid input. Please enter numeric values for all fields.", "danger")
            logging.warning("Invalid input for AI prediction: Non-numeric values provided.")
        except Exception as e:
            flash(f"❌ Prediction error: {e}", "danger")
            logging.error(f"Prediction error: {e}")
    
    return render_template("predict.html", result=result, username=session.get('username'))
