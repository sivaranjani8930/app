# app
The Disaster Relief Management System is a web-based emergency app where volunteers send distress messages with live location. Admins monitor alerts via a dashboard. Built using HTML, CSS, JS (frontend), Python Flask (backend), and Oracle Database for secure, real-time emergency management.
⚙️ Key Features:

Role-Based Login System:

Admin: Logs in with fixed credentials (Username: shiva, Password: admin) to access the dashboard.

Volunteer: Can register or log in with custom credentials to send SOS alerts.

SOS Alert Module:

Volunteers can enter their name and message.

Automatically captures geolocation (latitude & longitude) from the browser.

Sends alert details to the backend server.

Admin Dashboard:

Displays all SOS alerts from volunteers in real-time.

Shows the user’s name, message, location, and time of the alert.

Database Integration:

SOS alerts are stored in an Oracle Database for permanent access.

Data includes username, message, location, and timestamp.

Backend API (Flask):

Handles data exchange between the web interface and Oracle DB.

Uses RESTful routes /save_sos and /get_sos for communication.

🧠 Technologies Used:
Layer	Technology
Frontend	HTML, CSS, JavaScript
Backend	Python (Flask Framework)
Database	Oracle SQL
APIs	RESTful API for data communication
Others	Geolocation API for live location tracking

🔒 Advantages:

Quick emergency communication and response.

Real-time data storage and retrieval.

Secure role-based access (Admin vs Volunteer).

Easily expandable to include mobile support or push notifications.
