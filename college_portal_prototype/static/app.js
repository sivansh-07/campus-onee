function getLocation() {
  const result = document.getElementById("attendanceResult");
  if (!navigator.geolocation) {
    result.innerHTML = '<div class="alert alert-warning">Geolocation is not supported. Enter coordinates manually.</div>';
    return;
  }
  result.innerHTML = '<div class="alert alert-info">Requesting location permission...</div>';
  navigator.geolocation.getCurrentPosition(
    p => {
      document.getElementById("lat").value = p.coords.latitude.toFixed(6);
      document.getElementById("lon").value = p.coords.longitude.toFixed(6);
      result.innerHTML = '<div class="alert alert-success">Location captured. Press Check In.</div>';
    },
    e => result.innerHTML = '<div class="alert alert-warning">Location unavailable. Enter coordinates manually.</div>'
  );
}

async function checkIn() {
  const result = document.getElementById("attendanceResult");
  const latitude = document.getElementById("lat").value;
  const longitude = document.getElementById("lon").value;
  const courseId = document.getElementById("courseId").value;

  if (!latitude || !longitude) {
    result.innerHTML = '<div class="alert alert-warning">Please provide latitude and longitude.</div>';
    return;
  }

  const response = await fetch("/api/attendance/checkin", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({latitude, longitude, courseId})
  });
  const data = await response.json();
  result.innerHTML = `<div class="alert alert-${data.success ? "success" : "danger"}">${data.message}</div>`;
}
