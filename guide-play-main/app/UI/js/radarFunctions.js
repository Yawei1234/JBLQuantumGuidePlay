function blink (id, color, colorLight) {
    const found = JOY_MASTER.find(element => element.id === id);
    if (!found) return;
    const blinker = document.getElementById(id+'Blink');
    blinker.style.backgroundColor = colorLight;
    setTimeout(() => {
        blinker.style.backgroundColor = color;
    }, 50);
}
function calculateDistanceCartesian(x1, y1, x2, y2) {
  return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
}
function calculateAngleCartesian(x1, y1, x2, y2) {
  return Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
}
function calculateAnglePolar(r1, a1, r2, a2) {
  return Math.abs(a1 - a2);
}
function radiansToDegrees(radians) {
  return radians * 180 / Math.PI;
}
function degreesToRadians(degrees) {
  return degrees * Math.PI / 180;
}
function getSilence(dist, maxDist) {
    // 0 - 1 
    const silence = ((dist / maxDist) * 100) * 0.01
    return silence
}
function getSilenceSeconds (dist, maxDist) {
    const silence = getSilence(dist, maxDist)
    return silence * 10
}
function silenceToSeconds (silence, maxSeconds) {
    return silence * maxSeconds
}

function heatMapColorforValue(value) {

    // 0    : blue   (hsl(240, 100%, 50%))
    // 0.25 : cyan   (hsl(180, 100%, 50%))
    // 0.5  : green  (hsl(120, 100%, 50%))
    // 0.75 : yellow (hsl(60, 100%, 50%))
    // 1    : red    (hsl(0, 100%, 50%))


    var h = (1.0 - value) * 240
    return "hsl(" + h + ", 100%, 50%)";
}


function getVolume(x, y, multiplier=0.5) {
    
    const dist = calculateDistanceCartesian(0, 0, parseFloat(x), parseFloat(y))
    const percent = (dist / maxDist) * 100
    const amt = Math.abs(1.0 - percent * 0.01)
    
    return amt
}
