#!/usr/bin/env python3
"""EuPhO 2020 Online -- Experimental Problem 1: Hidden Charge.

Faithful Python port of the official C++ simulator (Exp1-WIN.exe / Exp1-Linux /
Exp1-OSX), reconstructed from the officially published source code
(sources.zip -> Experiment_1/, by Taavet Kalda & Paul Stanley).

The hidden parameters, the integrator, the adaptive time step, the 0.5 mm
Gaussian beam-placement error and the console wording are all identical to the
original, so the answers extracted from this program match the official
solutions.

Run:  python eupho2020_e1_hidden_charge.py
Quit: Ctrl+C
"""

import math
import random
import sys

# --- hidden parameters (charge.cpp) ------------------------------------------
R_P = (0.05435205, -0.0259338, -0.1150416)   # position of the hidden charge [m]
Q_P = -8.62193e-11                           # hidden charge [C]

# --- physical constants (charge.cpp) -----------------------------------------
M_E = 9.10938356e-31
E_0 = 1.60217662e-19
K_E = 8.9875517923e9

# --- limits (charge.h, main.cpp) ---------------------------------------------
XY_MIN, XY_MAX = -0.2, 0.2          # screen half-size [m]
V_MAX = 10000.0
DESIRED_NUMBER_OF_STEPS = 2_000_000
RADIAL_ERROR = 0.0005               # 0.5 mm Gaussian beam placement error
DT_CONST = 100.0                    # adaptive step: dt = DT_CONST / |a|

SEP = "------------------------------------------------"


def _acc(rx, ry, rz):
    """Acceleration of the electron at displacement r from the hidden charge."""
    r_sq = rx * rx + ry * ry + rz * rz
    c = -K_E * Q_P * E_0 / (r_sq * math.sqrt(r_sq)) / M_E
    return c * rx, c * ry, c * rz


def _solve(x0, y0, v0):
    """Integrate one electron; return (hit, x_f, y_f) with positions in metres."""
    dx, dy, dz = x0 - R_P[0], y0 - R_P[1], -10.0 - R_P[2]
    vx, vy, vz = 0.0, 0.0, v0

    for _ in range(2 * DESIRED_NUMBER_OF_STEPS):
        rx, ry, rz = dx + R_P[0], dy + R_P[1], dz + R_P[2]
        if math.sqrt(rx * rx + ry * ry + rz * rz) > 1000.0:
            break

        ax, ay, az = _acc(dx, dy, dz)
        dt = DT_CONST / math.sqrt(ax * ax + ay * ay + az * az)

        bx, by, bz = _acc(dx + vx * dt, dy + vy * dt, dz + vz * dt)
        ex, ey, ez = 0.5 * (ax + bx), 0.5 * (ay + by), 0.5 * (az + bz)

        half = 0.5 * dt * dt
        dx += vx * dt + ex * half
        dy += vy * dt + ey * half
        dz += vz * dt + ez * half
        vx += ex * dt
        vy += ey * dt
        vz += ez * dt

        rz = dz + R_P[2]
        if rz > 0.0:
            rx, ry = dx + R_P[0], dy + R_P[1]
            if XY_MIN <= rx <= XY_MAX and XY_MIN <= ry <= XY_MAX:
                return True, rx, ry
            return False, rx, ry

    return False, 0.0, 0.0


def _read_double(prompt):
    """Read one number; non-numeric input maps to the sentinel -10000 (as in C++)."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    tok = line.split()
    if not tok:
        return -10000.0
    try:
        return float(tok[0])
    except ValueError:
        return -10000.0


def main():
    while True:
        v = _read_double("Beam accelerating voltage in V: ")
        while not (0.0 <= v <= V_MAX):
            v = _read_double("Invalid entry.  Voltage must be between 1 and 10000: ")

        x = _read_double("x-coordinate of the electron beam in cm: ") / 100.0
        while not (XY_MIN <= x <= XY_MAX):
            x = _read_double(
                "Invalid entry.  x-coordinate must be between -20 and 20: ") / 100.0

        y = _read_double("y-coordinate of the electron beam in cm: ") / 100.0
        while not (XY_MIN <= y <= XY_MAX):
            y = _read_double(
                "Invalid entry.  y-coordinate must be between -20 and 20: ") / 100.0

        print("Electron beam fired with parameters (x, y, V) = "
              "({:g}cm, {:g}cm, {:g}V)".format(x * 100, y * 100, v))

        # limited precision of placing the beam
        xr = x + random.gauss(0.0, RADIAL_ERROR)
        yr = y + random.gauss(0.0, RADIAL_ERROR)

        v0 = math.sqrt(2.0 * v * E_0 / M_E)
        hit, xf, yf = _solve(xr, yr, v0)
        if hit:
            print("Electron detected at (x, y) = ({:.1f}cm, {:.1f}cm)".format(
                xf * 100, yf * 100))
        else:
            print("Electron not detected...")
        print(SEP)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
