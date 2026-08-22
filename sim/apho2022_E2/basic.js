let screen_width = window.innerWidth, screen_height = window.innerHeight;
let canvas_width, canvas_height;
let paused = false;
let mobile;

if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    mobile = true;
} else {
    mobile = false;
}

let graph_canvas = document.getElementById("graph-canvas");
let graph_context = graph_canvas.getContext("2d");

let angles_display = document.getElementById("angles-display");
let freq_display = document.getElementById("freq-display");
let scale_display = document.getElementById("scale-display");

let pause_button = document.getElementById("pause-button");

let table = document.getElementById("table");

let dist_input = document.getElementById("dist-input");
let dist_angle_input = document.getElementById("dist-angle-input");
let vel_input = document.getElementById("vel-input");
let vel_angle_input = document.getElementById("vel-angle-input");

let simul_start_time_input = document.getElementById("simul-start-time-input");
let simul_end_time_input = document.getElementById("simul-end-time-input");
let time_step_input = document.getElementById("time-step-input");

window.onload = function () {
    defaultParams();
}

function defaultParams() {
    dist_input.value = 0;
    dist_angle_input.value = 0;
    vel_input.value = 0;
    vel_angle_input.value = 0;
    simul_start_time_input.value = 0;
    simul_end_time_input.value = 25;
    time_step_input.value = 0.02;
    initParams();
}