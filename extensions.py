
# extensions.py - NEW: Shared SocketIO instance to fix circular import
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")  # Init with basic config; customize as needed
