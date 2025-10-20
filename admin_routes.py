from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
from db_config import get_db_connection
import logging
from datetime import datetime

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Session validation (enhanced: check for admin role and basic expiration)
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admin access required. Please login as admin.", "danger")
        session.clear()
        return redirect(url_for('login.login'))
    
    # Optional: Simple session timeout check (if login_time is set in login routes)
    if 'login_time' in session:
        login_time = datetime.fromisoformat(session['login_time'])
        if (datetime.now() - login_time).total_seconds() > 3600:
            flash("Session expired. Please login again.", "warning")
            session.clear()
            return redirect(url_for('login.login'))
    
    alerts = []
    resources = []
    deliveries = []

    if request.method == 'POST':
        # Handle assign volunteer to SOS
        sos_id = request.form.get('sos_id', '').strip()
        volunteer_name = request.form.get('volunteer_name', '').strip()
        
        if sos_id and volunteer_name:
            try:
                sos_id_int = int(sos_id)
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE sos_requests SET status = 'assigned', assigned_to = ? WHERE id = ?", 
                               (volunteer_name, sos_id_int))
                affected_rows = cursor.rowcount
                conn.commit()
                conn.close()
                
                if affected_rows > 0:
                    flash(f"SOS {sos_id} assigned to {volunteer_name}!", "success")
                    logger.info(f"SOS {sos_id} assigned to volunteer: {volunteer_name}")
                    
                    # Real-time update via SocketIO
                    try:
                        from app import socketio
                        if socketio:
                            conn_socket = get_db_connection()
                            cursor_socket = conn_socket.cursor()
                            cursor_socket.execute("""
                                SELECT sr.id, u.username, sr.latitude, sr.longitude, sr.description, sr.status, sr.assigned_to, sr.risk_level, sr.timestamp
                                FROM sos_requests sr JOIN users u ON sr.user_id = u.id
                                WHERE sr.id = ?
                            """, (sos_id_int,))
                            updated_sos_raw = cursor_socket.fetchone()
                            conn_socket.close()
                            
                            if updated_sos_raw:
                                updated_sos = dict(zip([
                                    'id', 'username', 'latitude', 'longitude', 'description', 
                                    'status', 'assigned_to', 'risk_level', 'timestamp'
                                ], updated_sos_raw))
                                logger.debug(f"Emitting sos_status_updated: {updated_sos}")
                                
                                socketio.emit('sos_status_updated', updated_sos, 
                                            room='volunteer-room', 
                                            broadcast=True, 
                                            include_self=False)
                                socketio.emit('sos_status_updated', updated_sos, 
                                            room='admin-room', 
                                            broadcast=True, 
                                            include_self=False)
                                
                                logger.info(f"✅ Real-time SOS update broadcasted for ID {sos_id} to admin and volunteer rooms")
                            else:
                                logger.warning(f"No SOS found with ID {sos_id} for broadcast")
                        else:
                            logger.warning("SocketIO instance not available – skipping real-time broadcast")
                    except ImportError:
                        logger.warning("SocketIO not available (ImportError) – skipping real-time broadcast")
                    except Exception as emit_e:
                        logger.error(f"⚠️ SocketIO broadcast failed for SOS update {sos_id}: {emit_e}")
                else:
                    flash("No SOS found with that ID.", "danger")
                    logger.warning(f"Assignment failed: No SOS with ID {sos_id}")
            except ValueError:
                flash("Invalid SOS ID.", "danger")
                logger.warning("Invalid SOS ID in assignment")
            except Exception as e:
                flash(f"Error assigning SOS: {e}", "danger")
                logger.error(f"Database error in SOS assignment: {e}")
        else:
            flash("SOS ID and volunteer name are required.", "danger")
    
    # Fetch data for dashboard
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all alerts with proper coordinate casting
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
            ORDER BY sr.timestamp DESC
        """)
        alerts_raw = cursor.fetchall()
        alerts = [dict(row) for row in alerts_raw]
        
        logger.info(f"Admin dashboard fetch: {len(alerts_raw)} raw alerts fetched from DB")
        for alert in alerts[:3]:
            lat = float(alert.get('latitude', 0)) if alert.get('latitude') else None
            lng = float(alert.get('longitude', 0)) if alert.get('longitude') else None
            logger.info(f"Sample alert ID {alert.get('id')}: lat={lat}, lng={lng}, status={alert.get('status')}, desc='{alert.get('description', '')[:50]}...'")
            if lat is None or lng is None or lat == 0 or lng == 0:
                logger.warning(f"⚠️ Invalid coords for alert ID {alert.get('id')}: lat={alert.get('latitude')}, lng={alert.get('longitude')} - Marker will be skipped in JS")

        # Fetch all resources
        cursor.execute("SELECT id, resource_name, quantity, status FROM resources ORDER BY resource_name")
        resources_raw = cursor.fetchall()
        resources = [dict(row) for row in resources_raw]

        # Fetch all pending deliveries
        try:
            cursor.execute("""
                SELECT delivery_id as id, volunteer_username, item, quantity, status 
                FROM resource_deliveries 
                WHERE status = 'pending'
                ORDER BY timestamp DESC
            """)
            deliveries_raw = cursor.fetchall()
            deliveries = [dict(row) for row in deliveries_raw]
            logger.info(f"Fetched {len(deliveries)} pending deliveries for admin dashboard")
        except Exception as del_e:
            logger.warning(f"No resource_deliveries table or error fetching deliveries: {del_e}. Using empty list.")
            deliveries = []
        
        conn.close()
        logger.info(f"✅ Admin dashboard data ready: {len(alerts)} alerts, {len(resources)} resources, {len(deliveries)} deliveries")
    except Exception as db_e:
        logger.error(f"Database error fetching dashboard data: {db_e}")
        flash("Error loading dashboard data. Please try again.", "danger")
        alerts = []
        resources = []
        deliveries = []
        if 'conn' in locals():
            conn.rollback()
    
    logger.info(f"Admin dashboard loaded for {session.get('username')}: {len(alerts)} alerts, {len(resources)} resources, {len(deliveries)} deliveries")
    return render_template('admin_dashboard.html', alerts=alerts, resources=resources, deliveries=deliveries, username=session.get('username'), role=session.get('role'))

# NEW: API endpoint for live map data (admin sees all SOS locations)
@admin_bp.route('/api/sos_map_data', methods=['GET'])
def get_sos_map_data():
    """Returns all SOS requests with coordinates for live map plotting"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
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
            ORDER BY sr.timestamp DESC
        """)
        sos_data_raw = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts for JSON serialization
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
        
        logger.info(f"API: Returned {len(sos_data)} SOS locations for admin map")
        return jsonify(sos_data)
    except Exception as e:
        logger.error(f"Error fetching SOS map data: {e}")
        return jsonify({'error': 'Failed to fetch map data'}), 500

# Add a new resource
@admin_bp.route('/add_resource', methods=['POST'])
def add_resource():
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        session.clear()
        return redirect(url_for('login.login'))
    
    resource_name = request.form.get('resource_name', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    status = request.form.get('status', '').strip()

    if not resource_name or not quantity_str or not status:
        flash("All resource fields are required!", "danger")
        return redirect(url_for('admin.dashboard'))
    
    try:
        quantity = int(quantity_str)
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO resources (resource_name, quantity, status) VALUES (?, ?, ?)",
                       (resource_name, quantity, status))
        conn.commit()
        conn.close()
        flash(f"Resource '{resource_name}' added successfully!", "success")
        logger.info(f"Resource added: {resource_name} (Qty: {quantity}, Status: {status})")
    except ValueError as ve:
        flash(f"Invalid input: {ve}", "danger")
        logger.warning(f"Invalid input in add_resource: {ve}")
    except Exception as e:
        flash(f"Error adding resource: {e}", "danger")
        logger.error(f"Error adding resource: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    
    return redirect(url_for('admin.dashboard'))

# Update an existing resource
@admin_bp.route('/update_resource', methods=['POST'])
def update_resource():
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        session.clear()
        return redirect(url_for('login.login'))
    
    res_id_str = request.form.get('res_id', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    status = request.form.get('status', '').strip()

    if not res_id_str or not quantity_str or not status:
        flash("All update fields are required!", "danger")
        return redirect(url_for('admin.dashboard'))
    
    try:
        res_id = int(res_id_str)
        quantity = int(quantity_str)
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE resources SET quantity = ?, status = ? WHERE id = ?",
                       (quantity, status, res_id))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected_rows > 0:
            flash(f"Resource ID {res_id} updated successfully!", "success")
            logger.info(f"Resource updated: ID {res_id} (Qty: {quantity}, Status: {status})")
        else:
            flash("No resource found with that ID.", "danger")
            logger.warning(f"Update failed: No resource with ID {res_id}")
    except ValueError as ve:
        flash(f"Invalid input: {ve}", "danger")
        logger.warning(f"Invalid input in update_resource: {ve}")
    except Exception as e:
        flash(f"Error updating resource: {e}", "danger")
        logger.error(f"Error updating resource: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    
    return redirect(url_for('admin.dashboard'))
