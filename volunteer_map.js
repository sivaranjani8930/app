// Volunteer Dashboard Live Map Script
// Save this as: static/js/volunteer_map.js

let volunteerMap = null;
let volunteerMarkers = {};
let volunteerMapInitialized = false;
let currentVolunteerUsername = ''; // To store the logged-in volunteer's username

// Initialize the map for volunteer dashboard
function initVolunteerMap() {
    if (volunteerMapInitialized) return;
    
    // Get username from data attribute
    currentVolunteerUsername = document.body.querySelector('[data-username]').dataset.username;
    console.log('Volunteer map initializing for:', currentVolunteerUsername);

    // Default center (India - adjust as needed)
    const defaultCenter = [20.5937, 78.9629];
    const defaultZoom = 5;
    
    // Initialize Leaflet map
    volunteerMap = L.map('volunteer-live-map').setView(defaultCenter, defaultZoom);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(volunteerMap);
    
    volunteerMapInitialized = true;
    console.log('Volunteer map initialized');
    
    // Load initial SOS markers
    loadVolunteerSOSMarkers();
}

// Load and display SOS markers on volunteer map
function loadVolunteerSOSMarkers() {
    if (!volunteerMap) {
        console.error('Volunteer map not initialized');
        return;
    }
    
    fetch('/volunteer/api/sos_map_data')
        .then(response => {
            if (!response.ok) {
                console.error(`Error fetching volunteer SOS data: ${response.status} ${response.statusText}`);
                throw new Error('Failed to fetch SOS data');
            }
            return response.json();
        })
        .then(sosData => {
            console.log(`Loaded ${sosData.length} SOS alerts for volunteer map`);
            
            // Clear existing markers
            Object.values(volunteerMarkers).forEach(marker => {
                volunteerMap.removeLayer(marker);
            });
            volunteerMarkers = {};
            
            // Add new markers
            sosData.forEach(sos => {
                addVolunteerSOSMarker(sos);
            });
            
            // Auto-fit bounds if markers exist
            if (sosData.length > 0) {
                const validCoords = sosData.filter(s => s.latitude && s.longitude && s.latitude !== 0 && s.longitude !== 0);
                if (validCoords.length > 0) {
                    const bounds = L.latLngBounds(validCoords.map(s => [s.latitude, s.longitude]));
                    volunteerMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
                }
            }
        })
        .catch(error => {
            console.error('Error loading volunteer SOS markers:', error);
        });
}

// Add a single SOS marker to volunteer map
function addVolunteerSOSMarker(sos) {
    const lat = parseFloat(sos.latitude);
    const lng = parseFloat(sos.longitude);
    
    // Skip invalid coordinates
    if (isNaN(lat) || isNaN(lng) || lat === 0 || lng === 0) {
        console.warn(`Skipping invalid coordinates for SOS ID ${sos.id}: lat=${sos.latitude}, lng=${sos.longitude}`);
        return;
    }
    
    // Determine marker color based on status and risk level
    let markerColor = 'blue';
    let markerClass = ''; // For pulsing animation
    
    if (sos.status === 'pending') {
        markerColor = 'red'; // Urgent - needs assignment
        markerClass = 'pulse-red'; // Custom CSS for pulsing
    } else if (sos.status === 'assigned' && sos.assigned_to === currentVolunteerUsername) {
        markerColor = 'orange'; // Assigned to current volunteer
        markerClass = 'pulse-orange'; // Custom CSS for pulsing
    } else if (sos.status === 'resolved') {
        markerColor = 'green'; // Completed
    }

    // Adjust color based on risk level if not resolved
    if (sos.status !== 'resolved') {
        if (sos.risk_level === 'High') {
            markerColor = 'red';
            markerClass = 'pulse-red';
        } else if (sos.risk_level === 'Medium') {
            markerColor = 'orange';
            markerClass = 'pulse-orange';
        }
    }
    
    // Create custom icon with pulsing effect
    const markerIcon = L.divIcon({
        className: `custom-marker ${markerClass}`,
        html: `<div style="background-color: ${markerColor}; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">${sos.id}</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    // Create marker
    const marker = L.marker([lat, lng], { icon: markerIcon }).addTo(volunteerMap);
    
    // Create popup content with "Get Directions"
    const popupContent = `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">SOS Alert #${sos.id}</h4>
            <p style="margin: 5px 0;"><strong>User:</strong> ${sos.username}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: ${markerColor}; font-weight: bold;">${sos.status.toUpperCase()}</span></p>
            <p style="margin: 5px 0;"><strong>Risk Level:</strong> ${sos.risk_level}</p>
            <p style="margin: 5px 0;"><strong>Assigned To:</strong> ${sos.assigned_to || 'Not assigned'}</p>
            <p style="margin: 5px 0;"><strong>Description:</strong> ${sos.description}</p>
            <p style="margin: 5px 0; font-size: 11px; color: #666;"><strong>Time:</strong> ${new Date(sos.timestamp).toLocaleString()}</p>
            <hr style="margin: 10px 0;">
            <a href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}" target="_blank" class="btn btn-sm btn-primary w-100">Get Directions</a>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    
    // Store marker reference
    volunteerMarkers[sos.id] = marker;
    
    console.log(`Added marker for SOS #${sos.id} at [${lat}, ${lng}] - Status: ${sos.status}`);
}

// Update a single SOS marker (for real-time updates via SocketIO)
function updateVolunteerSOSMarker(sos) {
    console.log('Updating volunteer marker for SOS:', sos);
    
    // Remove old marker if exists
    if (volunteerMarkers[sos.id]) {
        volunteerMap.removeLayer(volunteerMarkers[sos.id]);
        delete volunteerMarkers[sos.id];
    }
    
    // Only add if it's still relevant to this volunteer (pending or assigned to them)
    if (sos.status === 'pending' || sos.assigned_to === currentVolunteerUsername) {
        addVolunteerSOSMarker(sos);
    }
}

// Refresh map data periodically (fallback if SocketIO fails)
function startVolunteerMapPolling() {
    setInterval(() => {
        loadVolunteerSOSMarkers();
    }, 30000); // Refresh every 30 seconds
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if map container exists
    if (document.getElementById('volunteer-live-map')) {
        console.log('Volunteer map container found, initializing...');
        
        // Small delay to ensure DOM is ready
        setTimeout(() => {
            initVolunteerMap();
            startVolunteerMapPolling();
        }, 500);
    }
    
    // SocketIO real-time updates (if available)
    if (typeof socket !== 'undefined') {
        socket.on('new_sos_alert', function(data) {
            console.log('New SOS alert received via SocketIO:', data);
            // If a new SOS is pending, show it to all volunteers
            if (volunteerMap && data.status === 'pending') {
                addVolunteerSOSMarker(data);
            }
        });
        
        socket.on('sos_status_updated', function(data) {
            console.log('SOS status updated via SocketIO:', data);
            if (volunteerMap) {
                updateVolunteerSOSMarker(data);
            }
        });
    }
});

// Manual refresh button handler
function refreshVolunteerMap() {
    console.log('Manually refreshing volunteer map...');
    loadVolunteerSOSMarkers();
}