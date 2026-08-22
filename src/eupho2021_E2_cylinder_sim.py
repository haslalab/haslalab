#!/usr/bin/env python3
"""EuPhO 2021 -- Experimental Problem E2: Hot Cylinder.

Re-implementation of the official command-line simulator "rod"
(E2_hot_cylinder_win.exe / _linux / _osx).  The official source was never
published; the 1-D heat-conduction engine below is written from the problem
statement and the hidden material parameters are set to the values the official
solution extracts from the original program:

    c = 115 J/(kg K)     (official answer 114 +- 1, accepted [108, 118])
    k = 400 W/(m K)      (official answer 397,      accepted [378, 438])
    alpha = 2.90 W/(m^2 K) (official answer 2.93,   accepted [2.53, 3.03])
    beta  = 0.30           (official answer 0.304,  accepted [0.28, 0.32])

Geometry and interface follow the problem statement: L = 30 cm, r = 1 cm,
m = 460 g, T0 = 26.9 C, heater over 0 <= x <= 3 cm, up to five sensors,
dt a multiple of 5 s, everything within 0..3600 s, readings mirrored to a .txt
file, and the run displayed about 10x faster than real time.

Run:   python eupho2021_e2_hot_cylinder.py
       python eupho2021_e2_hot_cylinder.py --nowait   (no pacing at all)
Quit:  Ctrl+C
"""

import math
import os
import random
import sys
import time as _time

import numpy as np

# --- hidden material parameters ----------------------------------------------
C_SPEC = 115.0      # specific heat capacity [J/(kg K)]
K_COND = 400.0      # thermal conductivity   [W/(m K)]
ALPHA = 2.90        # convective loss coeff. [W/(m^2 K)]
BETA = 0.30         # emissivity             [-]

# --- geometry / given constants ----------------------------------------------
L_ROD = 0.30        # m
R_ROD = 0.01        # m
L_HEAT = 0.03       # m
MASS = 0.460        # kg
T0_C = 26.9
T0_K = 300.0        # the statement fixes T0 = 26.9 C = 300 K
SIGMA = 5.67e-8

AREA = math.pi * R_ROD ** 2          # cross-section
PERIM = 2.0 * math.pi * R_ROD        # lateral perimeter
RHO = MASS / (AREA * L_ROD)

# --- measurement noise --------------------------------------------------------
SENSOR_POS_SIGMA = 1.0e-3   # m,  Gaussian error in placing a sensor
TEMP_SIGMA = 0.2            # K,  Gaussian error of a temperature reading

# --- numerics -----------------------------------------------------------------
NX = 41                                   # nodes along the rod
DX = L_ROD / (NX - 1)
SPEEDUP = 10.0                            # display runs ~10x faster than real time
REALTIME = "--nowait" not in sys.argv


def simulate(power, heat_duration, t_start, t_end, dt_out, sensor_x, on_sample):
    """Explicit 1-D FDM of the rod. Calls on_sample(t, [T...]) for each output row."""
    diff = K_COND / (RHO * C_SPEC)
    dt = 0.4 * DX * DX / diff
    dt = min(dt, 0.05)

    T = np.full(NX, T0_K)
    x = np.linspace(0.0, L_ROD, NX)
    heater_mask = x <= L_HEAT
    n_heat = int(heater_mask.sum())
    # volumetric heating rate inside the heater section [W/m^3]
    q_vol = power / (AREA * (n_heat - 0.5) * DX) if n_heat else 0.0

    idx = [min(NX - 1, max(0, int(round(xs / DX)))) for xs in sensor_x]

    t = 0.0
    next_out = t_start
    while t < t_end - 1e-12:
        lap = np.empty_like(T)
        lap[1:-1] = (T[2:] - 2 * T[1:-1] + T[:-2]) / (DX * DX)
        # insulated ends except for the end-cap losses handled below
        lap[0] = 2.0 * (T[1] - T[0]) / (DX * DX)
        lap[-1] = 2.0 * (T[-2] - T[-1]) / (DX * DX)

        loss = PERIM * (ALPHA * (T - T0_K) + BETA * SIGMA * (T ** 4 - T0_K ** 4)) / AREA
        # end caps (area AREA each) spread over the first/last half cell
        cap0 = (ALPHA * (T[0] - T0_K) + BETA * SIGMA * (T[0] ** 4 - T0_K ** 4)) / (0.5 * DX)
        capN = (ALPHA * (T[-1] - T0_K) + BETA * SIGMA * (T[-1] ** 4 - T0_K ** 4)) / (0.5 * DX)

        src = np.zeros(NX)
        if t < heat_duration:
            src[heater_mask] = q_vol

        dTdt = (K_COND * lap - loss + src) / (RHO * C_SPEC)
        dTdt[0] -= cap0 / (RHO * C_SPEC)
        dTdt[-1] -= capN / (RHO * C_SPEC)

        step = min(dt, t_end - t)
        T = T + dTdt * step
        t += step

        while next_out <= t + 1e-9 and next_out <= t_end:
            vals = []
            for i in idx:
                vals.append(T[i] - T0_K + T0_C + random.gauss(0.0, TEMP_SIGMA))
            on_sample(next_out, vals)
            next_out += dt_out


def _ask_float(prompt, lo, hi, multiple=None):
    while True:
        sys.stdout.write(prompt + " ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        s = line.strip()
        if s.lower() == "restart":
            return None
        try:
            v = float(s)
        except ValueError:
            print("Invalid input, please enter a number.")
            continue
        if not (lo <= v <= hi):
            print("Value out of range, must be between %g and %g." % (lo, hi))
            continue
        if multiple and abs(v / multiple - round(v / multiple)) > 1e-9:
            print("Value must be a multiple of %g s." % multiple)
            continue
        return v


def _ask_pair(prompt):
    while True:
        sys.stdout.write(prompt + " ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        parts = line.split()
        if len(parts) != 2:
            print("Please enter exactly two numbers separated by a space.")
            continue
        try:
            a, b = float(parts[0]), float(parts[1])
        except ValueError:
            print("Invalid input, please enter two numbers.")
            continue
        if not (0 <= a <= 3600 and 0 <= b <= 3600):
            print("Times must be between 0 and 3600 s.")
            continue
        if b < a:
            print("The finishing time must not be before the starting time.")
            continue
        return a, b


def _ask_sensors():
    while True:
        sys.stdout.write("Enter up to 5 locations for the sensors (in cm), "
                         "between L=0 and L=30cm, separated by spaces: ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        parts = line.split()
        if len(parts) > 5:
            print("At most five sensors are available.")
            continue
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            print("Invalid input, please enter numbers separated by spaces.")
            continue
        if any(v < 0 or v > 30 for v in vals):
            print("Sensor locations must be between 0 and 30 cm.")
            continue
        return vals


def one_experiment():
    power = _ask_float("Enter P (W), between 0 and 300:", 0, 300)
    if power is None:
        return
    dur = _ask_float("Enter heating duration (s), between 0 and 3600s:", 0, 3600)
    if dur is None:
        return
    t_start, t_end = _ask_pair(
        "Enter the starting and finishing time for the measurements (s), "
        "separated by a space. Must be between 0 and 3600s:")
    dt_out = _ask_float("Enter dt (s), between 5 and 3600s and a multiple of 5s:",
                        5, 3600, multiple=5)
    if dt_out is None:
        return
    sensors_cm = _ask_sensors()

    sys.stdout.write("Enter the output file name: ")
    sys.stdout.flush()
    fname = (sys.stdin.readline() or "").strip() or "rod"
    fname += ".txt"

    sys.stdout.write('Press return to start the experiment, or type "restart": ')
    sys.stdout.flush()
    if (sys.stdin.readline() or "").strip().lower() == "restart":
        return

    # real sensor positions differ slightly from the requested ones
    real_x = [min(L_ROD, max(0.0, v * 0.01 + random.gauss(0.0, SENSOR_POS_SIGMA)))
              for v in sensors_cm]

    header = "  t(s)  " + "".join("   T%d(C)  " % (i + 1) for i in range(len(sensors_cm)))
    print()
    print("Experiment: P = %g W for %g s; measurements from %g s to %g s every %g s."
          % (power, dur, t_start, t_end, dt_out))
    print("Sensors at " + ", ".join("%g cm" % v for v in sensors_cm) + ".")
    print()
    print(header)

    rows = ["EuPhO 2021 - Experiment 2 (Hot Cylinder)",
            "",
            "P = %g W, heating duration = %g s" % (power, dur),
            "measurements %g s .. %g s, dt = %g s" % (t_start, t_end, dt_out),
            "sensors (cm): " + " ".join("%g" % v for v in sensors_cm),
            "",
            header]

    wall0 = _time.monotonic()

    def emit(t, vals):
        line = "%7.1f " % t + "".join("%9.2f " % v for v in vals)
        if REALTIME:
            target = (t - t_start) / SPEEDUP
            while _time.monotonic() - wall0 < target:
                _time.sleep(0.01)
        print(line)
        rows.append(line)

    simulate(power, dur, t_start, t_end, dt_out, real_x, emit)

    try:
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")
        print("\nReadings saved to %s" % os.path.abspath(fname))
    except OSError:
        print("\nInvalid file name -- readings were not saved.")


def main():
    print("EuPhO 2021 - Experiment 2: Hot Cylinder")
    print("L = 30 cm, r = 1 cm, m = 460 g, T0 = 26.9 C, heater over 0..3 cm.")
    print()
    while True:
        one_experiment()
        print()
        sys.stdout.write('Type "restart" and press return for a new experiment, '
                         'or Ctrl+C to quit: ')
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            break
        print()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
