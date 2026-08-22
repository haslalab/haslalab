function toRadians(degrees) {
    return Math.PI * degrees / 180;
}

function toDegrees(radians) {
    return radians * 180 / Math.PI;
}

function detectExtrema() {
    let start_index = get_start_index(signals);

    addEntry("Initial", signals[start_index], timestamps[start_index]);
    for (let i = start_index; i < signals.length - 1; i++) {
        if (signals[i - 1] < signals[i] && signals[i + 1] < signals[i]) {
            addEntry("Maxima", signals[i], timestamps[i]);
        }
        else if (signals[i - 1] > signals[i] && signals[i + 1] > signals[i]) {
            addEntry("Minima", signals[i], timestamps[i]);
        }
    }
}

function addEntry(type, freq, time) {
    table.innerHTML += ``;//`<tr><td>${type}</td><td>${freq.toFixed(4)}</td><td>${time}</td></tr>`;
}

function get_start_index(signals) {
    for (let i = 0; i < signals.length; i++) {
        if (!Number.isNaN(signals[i])) {
            return i;
        }
    }
}