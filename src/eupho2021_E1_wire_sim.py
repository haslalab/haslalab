#!/usr/bin/env python3
"""EuPhO 2021 -- Experimental Problem E1: Hidden wire.

Re-implementation of the official command-line simulator
(E1_hidden_wire_win.exe / _linux / _osx).  The official source code was never
published, so the physics engine here is written from the problem statement and
the hidden parameters are taken from the official solution, which states that
h = 5.0 mm and B_E = 4.0e-5 T "coincide with the values preset in the simulation
program", and that the wire projection is y = -0.58 x + 75.3 mm.

Cross-check against the official solution's data:
    I = +5 A at (0 mm, 75 mm)   ->  PHI = -143 deg   (official Table 2/3)
    I = +5 A at (20 mm, 75 mm)  ->  PHI =  -75 deg   (official Table 2)

Prompts, rounding, ranges and the 0.5 mm compass placement error follow the
problem statement exactly.

Run:  python eupho2021_e1_hidden_wire.py
Quit: Ctrl+C
"""

import math
import random
import sys

# --- hidden parameters --------------------------------------------------------
A_WIRE = -0.58          # y = a*x + b  (projection of the wire, mm)
B_WIRE = 75.3           # mm
H_DEPTH = 5.0e-3        # depth of the wire below the surface [m]
B_EARTH = 4.0e-5        # horizontal component of the Earth's field [T]

MU0 = 4e-7 * math.pi
L_SIDE = 100.0          # side of the square surface [mm]
I_MAX = 5.0
POS_SIGMA = 0.5         # mm, "limited precision when you place an object"

SEP = "-------------------------------"


def phi_degrees(current, x_mm, y_mm):
    """Deflection angle of the needle (deg, positive = Eastward)."""
    theta = math.atan(A_WIRE)                       # direction of positive current
    tx, ty = math.cos(theta), math.sin(theta)       # unit vector along +I

    # vector from a point of the wire to the compass, in metres
    x0 = 0.0
    rx = (x_mm - x0) * 1e-3
    ry = (y_mm - (A_WIRE * x0 + B_WIRE)) * 1e-3
    rz = H_DEPTH                                    # compass is above the wire

    # perpendicular component
    dot = rx * tx + ry * ty
    px, py, pz = rx - dot * tx, ry - dot * ty, rz
    d = math.sqrt(px * px + py * py + pz * pz)

    # B = mu0 I /(2 pi d) * (t_hat x p_hat)
    coeff = MU0 * current / (2.0 * math.pi * d * d)
    bx = coeff * (ty * pz - 0.0 * py)
    by = coeff * (0.0 * px - tx * pz)

    return math.degrees(math.atan2(bx, by + B_EARTH))


def _ask(prompt, lo, hi):
    while True:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        try:
            v = float(line.strip())
        except ValueError:
            print("Invalid input.")
            continue
        if lo <= v <= hi:
            return v
        print("Value out of range.")


def main():
    while True:
        current = _ask("Enter I (A) between -5.0 and 5.0: ", -I_MAX, I_MAX)
        x = _ask("Enter X (mm) between 0 and 100: ", 0.0, L_SIDE)
        y = _ask("Enter Y (mm) between 0 and 100: ", 0.0, L_SIDE)

        current = round(current, 1)
        x = round(x)
        y = round(y)

        # the real position differs from the entered one by about 0.5 mm
        xr = x + random.gauss(0.0, POS_SIGMA)
        yr = y + random.gauss(0.0, POS_SIGMA)

        print("PHI = %d degrees" % round(phi_degrees(current, xr, yr)))
        print(SEP)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        for cur, xx, yy in ((5, 0, 75), (5, 20, 75), (-5, 0, 75), (1, 0, 75), (5, 10, 75)):
            print("I=%+g x=%g y=%g -> PHI = %d deg"
                  % (cur, xx, yy, round(phi_degrees(cur, xx, yy))))
        sys.exit(0)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
