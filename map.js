function initMap() {
  fetch('/get_sos')
    .then(res => res.json())
    .then(data => {
      const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 5,
        center: { lat: 20.5937, lng: 78.9629 } // Centered on India
      });

      data.forEach(sos => {
        new google.maps.Marker({
          position: {
            lat: parseFloat(sos.latitude),
            lng: parseFloat(sos.longitude)
          },
          map: map,
          title: "SOS Request"
        });
      });
    });
}

window.onload = initMap;