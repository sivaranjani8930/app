from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
from db_config import get_db_connection
import logging
import os
import numpy as np
import random
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

volunteer_bp = Blueprint('volunteer', __name__)
logger = logging.getLogger(__name__)

# --- AI Prediction Model Integration ---
model_path = os.path.join("models", "disaster_model.pkl")
prediction_model = None
risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'}

def train_and_save_dummy_model_for_volunteer():
    logger.warning("⚠️ No trained model found for volunteer dashboard. Training a dummy model.")
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
    logger.info("✅ Dummy disaster prediction model trained and saved for volunteer.")
    return dummy_model, {v: k for k, v in risk_mapping.items()}

try:
    if os.path.exists(model_path):
        prediction_model = joblib.load(model_path)
        risk_level_labels = {0: 'Low', 1: 'Medium', 2: 'High'}
        logger.info("✅ Disaster prediction model loaded successfully for volunteer.")
    else:
        prediction_model, risk_level_labels = train_and_save_dummy_model_for_volunteer()
except Exception as e:
    logger.error(f"⚠️ Error loading model for volunteer prediction: {e}. Falling back to dummy mode.")
    prediction_model = None


@volunteer_bp.route('/dashboard')
def volunteer_dashboard():
    if 'username' not in session or session.get('role') != 'volunteer':
        flash("Volunteer access required. Please login as volunteer.", "danger")
        return redirect(url_for('login.login'))
    
    username = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch assigned or pending alerts for this volunteer
    cursor.execute("""
        SELECT 
            sr.id, 
            u.username, 
            CAST(sr.latitude AS REAL) as latitude,
            CAST(sr.longitude AS REAL) as longitude,
            sr.description, 
            sr.status, 
            sr.timestamp, 
            sr.assigned_to, 
            sr.risk_level
        FROM sos_requests sr
        JOIN users u ON sr.user_id = u.id
        WHERE (sr.assigned_to = ? OR sr.status = 'pending')
        ORDER BY sr.timestamp DESC
    """, (username,))
    alerts_raw = cursor.fetchall()
    alerts = [dict(row) for row in alerts_raw]

    logger.info(f"Volunteer dashboard fetch for {username}: {len(alerts_raw)} raw alerts fetched from DB")

    # FIXED: Fetch ALL available resources (not just status='available')
    # The issue was the WHERE clause filtering too strictly
    try:
        cursor.execute("""
            SELECT id, resource_name, quantity, status 
            FROM resources 
            WHERE quantity > 0
            ORDER BY resource_name
        """)
        resources_raw = cursor.fetchall()
        resources = [dict(row) for row in resources_raw]
        logger.info(f"✅ Fetched {len(resources)} resources for volunteer {username}")
        
        # Debug log to see what resources are available
        if len(resources) == 0:
            logger.warning(f"⚠️ No resources found in database with quantity > 0")
            # Try without filter to see all resources
            cursor.execute("SELECT id, resource_name, quantity, status FROM resources ORDER BY resource_name")
            all_resources = cursor.fetchall()
            logger.info(f"📊 Total resources in DB (including 0 quantity): {len(all_resources)}")
            for res in all_resources:
                logger.info(f"  - {dict(res)}")
    except Exception as res_e:
        logger.error(f"❌ Error fetching resources for volunteer {username}: {res_e}")
        resources = []

    # Fetch volunteer's own pending deliveries
    try:
        cursor.execute("""
            SELECT delivery_id as id, volunteer_username, item, quantity, status 
            FROM resource_deliveries 
            WHERE volunteer_username = ? AND status = 'pending'
            ORDER BY timestamp DESC
        """, (username,))
        deliveries_raw = cursor.fetchall()
        deliveries = [dict(row) for row in deliveries_raw]
        logger.info(f"Fetched {len(deliveries)} pending deliveries for volunteer {username}")
    except Exception as del_e:
        logger.warning(f"No resource_deliveries table or error fetching deliveries: {del_e}. Using empty list.")
        deliveries = []

    conn.close()
    logger.info(f"✅ Volunteer dashboard data ready for {username}: {len(alerts)} alerts, {len(resources)} resources, {len(deliveries)} deliveries")
    
    return render_template('volunteer_dashboard.html', alerts=alerts, resources=resources, deliveries=deliveries, username=username, role=session.get('role'))


@volunteer_bp.route('/request_resource', methods=['POST'])
def request_resource():
    if 'username' not in session or session.get('role') != 'volunteer':
        flash("Volunteer access required.", "danger")
        return redirect(url_for('login.login'))
    
    username = session['username']
    item = request.form.get('item', '').strip()
    quantity_str = request.form.get('quantity', '').strip()

    logger.info(f"📦 Resource request received from {username}: item='{item}', quantity='{quantity_str}'")

    if not item or not quantity_str:
        flash("Item and quantity are required!", "danger")
        logger.warning(f"⚠️ Missing item or quantity in request from {username}")
        return redirect(url_for('volunteer.volunteer_dashboard'))
    
    try:
        quantity = int(quantity_str)
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED: Check resource by resource_name, not just status
        cursor.execute("SELECT id, quantity, status FROM resources WHERE resource_name = ?", (item,))
        stock_result = cursor.fetchone()
        
        if not stock_result:
            flash(f"Resource '{item}' not found in inventory!", "danger")
            logger.warning(f"⚠️ Resource '{item}' not found for volunteer {username}")
            conn.close()
            return redirect(url_for('volunteer.volunteer_dashboard'))
        
        available_quantity = stock_result[1]
        logger.info(f"📊 Resource '{item}' check: Available={available_quantity}, Requested={quantity}")
        
        if available_quantity < quantity:
            flash(f"Insufficient stock for '{item}'. Available: {available_quantity}, Requested: {quantity}", "danger")
            logger.warning(f"⚠️ Insufficient stock for '{item}': Available={available_quantity}, Requested={quantity}")
            conn.close()
            return redirect(url_for('volunteer.volunteer_dashboard'))
        
        # Create delivery request (don't reduce stock yet - admin will approve)
        cursor.execute("""
            INSERT INTO resource_deliveries (volunteer_username, item, quantity, status, timestamp)
            VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (username, item, quantity))
        delivery_id = cursor.lastrowid
        
        # OPTIONAL: Reduce stock immediately (or wait for admin approval)
        # Comment out these lines if you want admin to approve first
        cursor.execute("UPDATE resources SET quantity = quantity - ? WHERE resource_name = ?",
                       (quantity, item))
        
        conn.commit()
        conn.close()
        
        flash(f"✅ Resource request submitted! {quantity}x '{item}' (Request ID: {delivery_id})", "success")
        logger.info(f"✅ Resource request created: {username} requested {quantity}x {item} (Delivery ID: {delivery_id})")
        
        # Optional: Notify admin via SocketIO
        try:
            from app import socketio
            if socketio:
                socketio.emit('new_resource_request', {
                    'delivery_id': delivery_id,
                    'volunteer': username,
                    'item': item,
                    'quantity': quantity,
                    'timestamp': str(pd.Timestamp.now())
                }, room='admin-room', broadcast=True)
                logger.info(f"📡 Resource request notification sent to admin via SocketIO")
        except Exception as socket_e:
            logger.warning(f"⚠️ Failed to send SocketIO notification: {socket_e}")
        
    except ValueError as ve:
        flash(f"Invalid input: {ve}", "danger")
        logger.warning(f"Invalid input in request_resource by {username}: {ve}")
    except Exception as e:
        flash(f"Error requesting resource: {e}", "danger")
        logger.error(f"Error in request_resource by {username}: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    
    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/update_delivery', methods=['POST'])
def update_delivery():
    if 'username' not in session or session.get('role') != 'volunteer':
        flash("Volunteer access required.", "danger")
        return redirect(url_for('login.login'))
    
    username = session['username']
    delivery_id_str = request.form.get('delivery_id', '').strip()
    status = request.form.get('status', '').strip()

    if not delivery_id_str or not status:
        flash("Delivery ID and status are required!", "danger")
        return redirect(url_for('volunteer.volunteer_dashboard'))
    
    try:
        delivery_id = int(delivery_id_str)
        if status not in ['delivered', 'cancelled']:
            raise ValueError("Invalid status")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch delivery details first
        cursor.execute("""
            SELECT item, quantity FROM resource_deliveries 
            WHERE delivery_id = ? AND volunteer_username = ?
        """, (delivery_id, username))
        delivery_info = cursor.fetchone()
        
        if not delivery_info:
            flash("No delivery found with that ID.", "danger")
            conn.close()
            return redirect(url_for('volunteer.volunteer_dashboard'))
        
        item = delivery_info[0]
        quantity = delivery_info[1]
        
        # Update delivery status
        cursor.execute("""
            UPDATE resource_deliveries 
            SET status = ? 
            WHERE delivery_id = ? AND volunteer_username = ?
        """, (status, delivery_id, username))
        
        # If cancelled, return stock
        if status == 'cancelled':
            cursor.execute("UPDATE resources SET quantity = quantity + ? WHERE resource_name = ?", (quantity, item))
            logger.info(f"🔄 Returned {quantity}x {item} to inventory (cancelled)")
        
        conn.commit()
        conn.close()
        
        flash(f"Delivery {delivery_id} updated to '{status}'!", "success")
        logger.info(f"Delivery {delivery_id} updated by {username} to '{status}'")
        
    except ValueError as ve:
        flash(f"Invalid input: {ve}", "danger")
        logger.warning(f"Invalid input in update_delivery by {username}: {ve}")
    except Exception as e:
        flash(f"Error updating delivery: {e}", "danger")
        logger.error(f"Error in update_delivery by {username}: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    
    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/acknowledge_sos', methods=['POST'])
def acknowledge_sos():
    if 'username' not in session or session.get('role') != 'volunteer':
        flash("Volunteer access required.", "danger")
        return redirect(url_for('login.login'))
    
    username = session['username']
    sos_id_str = request.form.get('sos_id', '').strip()

    if not sos_id_str:
        flash("SOS ID is required!", "danger")
        return redirect(url_for('volunteer.volunteer_dashboard'))
    
    try:
        sos_id = int(sos_id_str)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sos_requests 
            SET status = 'resolved' 
            WHERE id = ? AND assigned_to = ?
        """, (sos_id, username))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected_rows > 0:
            flash(f"SOS {sos_id} marked as resolved!", "success")
            logger.info(f"SOS {sos_id} acknowledged/resolved by volunteer {username}")
            
            try:
                from app import socketio
                if socketio:
                    conn_socket = get_db_connection()
                    cursor_socket = conn_socket.cursor()
                    cursor_socket.execute("""
                        SELECT sr.id, u.username, sr.latitude, sr.longitude, sr.description, sr.status, sr.assigned_to, sr.risk_level, sr.timestamp
                        FROM sos_requests sr JOIN users u ON sr.user_id = u.id
                        WHERE sr.id = ?
                    """, (sos_id,))
                    updated_sos_raw = cursor_socket.fetchone()
                    conn_socket.close()
                    
                    if updated_sos_raw:
                        updated_sos = dict(zip([
                            'id', 'username', 'latitude', 'longitude', 'description', 
                            'status', 'assigned_to', 'risk_level', 'timestamp'
                        ], updated_sos_raw))
                        
                        socketio.emit('sos_status_updated', updated_sos, 
                                    room='admin-room', 
                                    broadcast=True, 
                                    include_self=False)
                        logger.info(f"✅ Real-time SOS resolution broadcasted for ID {sos_id} to admin room")
            except Exception as emit_e:
                logger.error(f"⚠️ SocketIO broadcast failed for SOS resolution {sos_id}: {emit_e}")
        else:
            flash("No assigned SOS found with that ID.", "danger")
            logger.warning(f"Acknowledge failed: No SOS {sos_id} assigned to {username}")
    except ValueError as ve:
        flash(f"Invalid SOS ID: {ve}", "danger")
        logger.warning(f"Invalid SOS ID in acknowledge_sos by {username}: {ve}")
    except Exception as e:
        flash(f"Error acknowledging SOS: {e}", "danger")
        logger.error(f"Error in acknowledge_sos by {username}: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    
    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/api/sos_map_data', methods=['GET'])
def get_sos_map_data():
    """Returns SOS requests for the logged-in volunteer (pending or assigned) for live map plotting"""
    if 'username' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                sr.id,
                u.username,
                CAST(sr.latitude AS REAL) as latitude,
                CAST(sr.longitude AS REAL) as longitude,
                sr.description,
                sr.status,
                sr.risk_level,
                sr.assigned_to,
                sr.timestamp
            FROM sos_requests sr
            JOIN users u ON sr.user_id = u.id
            WHERE (sr.assigned_to = ? OR sr.status = 'pending')
            ORDER BY sr.timestamp DESC
        """, (username,))
        sos_data_raw = cursor.fetchall()
        conn.close()
        
        sos_data = [
            {
                'id': row['id'],
                'username': row['username'],
                'latitude': float(row['latitude']) if row['latitude'] else 0,
                'longitude': float(row['longitude']) if row['longitude'] else 0,
                'description': row['description'],
                'status': row['status'],
                'risk_level': row['risk_level'],
                'assigned_to': row['assigned_to'],
                'timestamp': row['timestamp']
            }
            for row in sos_data_raw
        ]
        
        logger.info(f"API: Returned {len(sos_data)} SOS locations for volunteer {username}'s map")
        return jsonify(sos_data)
    except Exception as e:
        logger.error(f"Error fetching volunteer SOS map data for {username}: {e}")
        return jsonify({'error': 'Failed to fetch map data'}), 500
