// This version adds increased fps control and minimizes UI
// it is a modified version of dopper effect (merged) by Siddhant
// some code has also been refactored

// constants
const speed_of_sound = 330;
const source_frequency = 991;
let detected = false;
let time_step;
let current_time_step;

let reduced_time_step;
const reducing_factor = 200;

// arrays
let signals = [];
let detectors = [];
let timestamps = [];

// objects
let source;
let graph = undefined;

// counters
let current_frame;
let current_time;

function addDoppler() {
    for (let detector of detectors) {
        signals.push(Number.parseFloat(doppler(source, detector)));
        timestamps.push(Number.parseFloat(current_time));
    }
}

function doppler(source, detector) {
    f0 = source_frequency;
    vc = speed_of_sound;

    let t_em = LinAlg.find_em(current_time, vc, source, detector);
    let source_pos = source.position(t_em);
    let detector_pos = detector.position(current_time);
    let source_vel = source.velocity(t_em);
    let detector_vel = detector.velocity(current_time);
    let components_along = LinAlg.comp(source_pos, detector_pos, source_vel, detector_vel);
    if (t_em >= 0) {
        if (!detected) {
            current_time -= current_time_step;
            current_time_step = reduced_time_step;
            current_time -= current_time_step;
            detected = true;
            return NaN;
        }
        else { current_time_step = time_step; }
        return f0 * (vc + components_along[1]) / (vc - components_along[0]);
    }
    else return NaN;
}

function initParams() {
    simul_end_time = Number.parseFloat(simul_end_time_input.value);
    simul_start_time = Number.parseFloat(simul_start_time_input.value);
    time_step = Number.parseFloat(time_step_input.value);

    // handle blanks
    if (Number.isNaN(simul_end_time)) {
        simul_end_time = 0;
        simul_end_time_input.value = "0";
    }
    if (Number.isNaN(simul_start_time)) {
        simul_start_time = 0;
        simul_start_time_input.value = "0";
    }
    if (Number.isNaN(time_step)) {
        time_step = 0.02;
        time_step_input.value = "0.02";
    }

    // handle special cases
    if (simul_start_time < 0) {
        simul_start_time = 0;
        simul_start_time_input.value = "0";
    }
    if (time_step < 0.001) {
        time_step = 0.001;
        time_step_input.value = "0.001";
    }
    if (simul_end_time < simul_start_time) {
        simul_end_time = simul_start_time;
        simul_end_time_input.value = simul_start_time_input.value;
    }
    if ((simul_end_time - simul_start_time) / time_step > 25000) {
        simul_end_time = simul_start_time + 25000 * time_step;
        simul_end_time_input.value = simul_end_time;
    }

    current_time_step = time_step;
    reduced_time_step = time_step / reducing_factor;
    signals = [];
    timestamps = [];
    current_time = simul_start_time;
    current_frame = 0;
    detected = false;
    //table.innerHTML = "<tr><th>Type</th><th>Frequency (Hz)</th><th>Timestamp (s)</th></tr>";


    let dist = Number.parseFloat(dist_input.value);
    let dist_angle = toRadians(Number.parseFloat(dist_angle_input.value));
    let vel = Number.parseFloat(vel_input.value);
    let vel_angle = Number.parseFloat(vel_angle_input.value);

    // handle blanks
    if (Number.isNaN(dist)) {
        dist = 0;
        dist_input.value = "0";
    }
    if (Number.isNaN(dist_angle)) {
        dist_angle = 0;
        dist_angle_input.value = "0";
    }
    if (Number.isNaN(vel)) {
        vel = 0;
        vel_input.value = "0";
    }
    if (Number.isNaN(vel_angle)) {
        vel_angle = 0;
        vel_angle_input.value = "0";
    }

    // handle negatives
    if (dist < 0) {
        dist = 0;
        dist_input.value = "0";
    }

    // SET PARAMS HERE
    // (x, y, z, vx, vy, vz, R, angular_velocity)
    source = new Source(300, 500, 0, 81, 43, 0, 120, 1.5);
    detectors = [];
    detectors.push(new Detector(dist * Math.cos(dist_angle), dist * Math.sin(dist_angle), 0, vel * Math.cos(vel_angle), vel * Math.cos(vel_angle), 0));

    if (graph !== undefined) graph.destroy();

    while (current_time < simul_end_time) {
        // generate signals
        addDoppler(source)
        current_time += current_time_step;
        current_frame += 1;
    }
    //console.log(timestamps);
    //console.log(signals);
    timestamps = timestamps.slice(2);
    signals = signals.slice(2);
    //for checking only
    drawGraph();
    //detectExtrema();
}