// Admin Dashboard Live Map Script
// Save this as: static/js/admin_map.js

let adminMap = null;
let adminMarkers = {};
let adminMapInitialized = false;

// Initialize the map for admin dashboard
function initAdminMap() {
    if (adminMapInitialized) return;
    
    // Default center (India - adjust as needed)
    const defaultCenter = [20.5937, 78.9629];
    const defaultZoom = 5;
    
    // Initialize Leaflet map
    adminMap = L.map('admin-live-map').setView(defaultCenter, defaultZoom);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(adminMap);
    
    adminMapInitialized = true;
    console.log('Admin map initialized');
    
    // Load initial SOS markers
    loadAdminSOSMarkers();
}

// Load and display SOS markers on admin map
function loadAdminSOSMarkers() {
    if (!adminMap) {
        console.error('Admin map not initialized');
        return;
    }
    
    fetch('/admin/api/sos_map_data')
        .then(response => {
            if (!response.ok) {
                console.error(`Error fetching admin SOS data: ${response.status} ${response.statusText}`);
                throw new Error('Failed to fetch SOS data');
            }
            return response.json();
        })
        .then(sosData => {
            console.log(`Loaded ${sosData.length} SOS alerts for admin map`);
            
            // Clear existing markers
            Object.values(adminMarkers).forEach(marker => {
                adminMap.removeLayer(marker);
            });
            adminMarkers = {};
            
            // Add new markers
            sosData.forEach(sos => {
                addAdminSOSMarker(sos);
            });
            
            // Auto-fit bounds if markers exist
            if (sosData.length > 0) {
                const validCoords = sosData.filter(s => s.latitude && s.longitude && s.latitude !== 0 && s.longitude !== 0);
                if (validCoords.length > 0) {
                    const bounds = L.latLngBounds(validCoords.map(s => [s.latitude, s.longitude]));
                    adminMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
                }
            }
        })
        .catch(error => {
            console.error('Error loading admin SOS markers:', error);
        });
}

// Add a single SOS marker to admin map
function addAdminSOSMarker(sos) {
    const lat = parseFloat(sos.latitude);
    const lng = parseFloat(sos.longitude);
    
    // Skip invalid coordinates
    if (isNaN(lat) || isNaN(lng) || lat === 0 || lng === 0) {
        console.warn(`Skipping invalid coordinates for SOS ID ${sos.id}: lat=${sos.latitude}, lng=${sos.longitude}`);
        return;
    }
    
    // Determine marker color based on status and risk level
    let markerColor = 'blue';
    if (sos.status === 'pending') {
        markerColor = 'red'; // Urgent - needs assignment
    } else if (sos.status === 'assigned') {
        markerColor = 'orange'; // In progress
    } else if (sos.status === 'resolved') {
        markerColor = 'green'; // Completed
    }
    
    // Adjust color based on risk level
    if (sos.risk_level === 'High') {
        markerColor = 'red';
    } else if (sos.risk_level === 'Medium' && sos.status !== 'resolved') {
        markerColor = 'orange';
    }
    
    // Create custom icon
    const markerIcon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="background-color: ${markerColor}; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">${sos.id}</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    // Create marker
    const marker = L.marker([lat, lng], { icon: markerIcon }).addTo(adminMap);
    
    // Create popup content
    const popupContent = `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">SOS Alert #${sos.id}</h4>
            <p style="margin: 5px 0;"><strong>User:</strong> ${sos.username}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: ${markerColor}; font-weight: bold;">${sos.status.toUpperCase()}</span></p>
            <p style="margin: 5px 0;"><strong>Risk Level:</strong> ${sos.risk_level}</p>
            <p style="margin: 5px 0;"><strong>Assigned To:</strong> ${sos.assigned_to || 'Not assigned'}</p>
            <p style="margin: 5px 0;"><strong>Description:</strong> ${sos.description}</p>
            <p style="margin: 5px 0; font-size: 11px; color: #666;"><strong>Time:</strong> ${new Date(sos.timestamp).toLocaleString()}</p>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    
    // Store marker reference
    adminMarkers[sos.id] = marker;
    
    console.log(`Added marker for SOS #${sos.id} at [${lat}, ${lng}] - Status: ${sos.status}`);
}

// Update a single SOS marker (for real-time updates via SocketIO)
function updateAdminSOSMarker(sos) {
    console.log('Updating admin marker for SOS:', sos);
    
    // Remove old marker if exists
    if (adminMarkers[sos.id]) {
        adminMap.removeLayer(adminMarkers[sos.id]);
        delete adminMarkers[sos.id];
    }
    
    // Add updated marker
    addAdminSOSMarker(sos);
}

// Refresh map data periodically (fallback if SocketIO fails)
function startAdminMapPolling() {
    setInterval(() => {
        loadAdminSOSMarkers();
    }, 30000); // Refresh every 30 seconds
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if map container exists
    if (document.getElementById('admin-live-map')) {
        console.log('Admin map container found, initializing...');
        
        // Small delay to ensure DOM is ready
        setTimeout(() => {
            initAdminMap();
            startAdminMapPolling();
        }, 500);
    }
    
    // SocketIO real-time updates (if available)
    if (typeof socket !== 'undefined') {
        socket.on('new_sos_alert', function(data) {
            console.log('New SOS alert received via SocketIO:', data);
            if (adminMap) {
                addAdminSOSMarker(data);
            }
        });
        
        socket.on('sos_status_updated', function(data) {
            console.log('SOS status updated via SocketIO:', data);
            if (adminMap) {
                updateAdminSOSMarker(data);
            }
        });
    }
});

// Manual refresh button handler
function refreshAdminMap() {
    console.log('Manually refreshing admin map...');
    loadAdminSOSMarkers();
}