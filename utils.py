from flask_socketio import emit
import logging

def emit_new_sos(sos_data):
    """
    Emit a new SOS alert to all connected clients via SocketIO.
    This function can be called from any route or the main app.
    """
    logging.info(f"Emitting new_sos_alert: {sos_data}")
    emit('new_sos_alert', sos_data, namespace='/')
