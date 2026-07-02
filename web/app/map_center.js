const latVal = document.getElementById('lat-val');
const lonVal = document.getElementById('lon-val');

function updateCoords() {
    const center = map.getCenter();
    latVal.textContent = center.lat.toFixed(6);
    lonVal.textContent = center.lng.toFixed(6);
}

map.on('move', updateCoords);
updateCoords();
