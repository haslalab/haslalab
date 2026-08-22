#!/usr/bin/env python3
"""APhO 2021 (Taipei, online) -- Experimental Problem 2:
Exploring the spatial structure of a sample with optical methods.

The official programs 2A-2E were graphical (draggable laser sources, movable
screen, click-to-place photodetector) and were never published, so this is a
reconstruction of the same measurements from the official problem statement.
The observable is the same: the photodetector voltage at a point (x, y) of the
screen, for a chosen wavelength and screen distance L.

The structure of the sample is hidden; see the constants at the top of this file
if you want to check your answers afterwards.

Commands:
    slit X Y                 part A: the double slit at sample position (X, Y) mm,
                             screen fixed at 50 cm; prints the fringe profile
    point LAMBDA L X Y       one photodetector reading, wavelengths in nm,
                             L in cm, X and Y in cm
    scan LAMBDA L X Y ANG N STEP
                             sweep the detector from (X, Y) along ANG degrees,
                             N points spaced STEP cm apart
    quit

Visible lasers: 450, 532, 633 nm.  Infrared (part D): 1310, 1550 nm.
"""

import math
import random
import sys

A_SPHERE = 5.0e-6
L_RECT, W_RECT = 60e-6, 40e-6
DX_GRID, DY_GRID = 300e-6, 200e-6
PHI = 25.0
N_CELLS = 6

SLIT_SEP, SLIT_WIDTH = 100e-6, 20e-6
BEST_X, BEST_Y = 0.5e-3, -0.3e-3
ALIGN_TOL = 0.6e-3

METER_MAX = 10.0


def _sinc2(z):
    if abs(z) < 1e-12:
        return 1.0
    s = math.sin(z) / z
    return s * s


def _dirichlet(z, n):
    den = math.sin(z)
    if abs(den) < 1e-9:
        return 1.0
    r = math.sin(n * z) / (n * den)
    return r * r


def intensity_sample(lam, dist, x, y):
    u, v = x / dist, y / dist
    p = math.radians(PHI)
    up = u * math.cos(p) + v * math.sin(p)
    vp = -u * math.sin(p) + v * math.cos(p)

    env = _sinc2(math.pi * L_RECT * up / lam) * _sinc2(math.pi * W_RECT * vp / lam)
    lat = (_dirichlet(math.pi * DX_GRID * up / lam, N_CELLS) *
           _dirichlet(math.pi * DY_GRID * vp / lam, N_CELLS))

    r = math.hypot(u, v)
    ring = 0.0
    for m in (1, 2, 3):
        r0 = m * lam / A_SPHERE
        if r0 > 0.6:
            break
        z = (r - r0) / 0.0035
        ring += (0.09 / m) * math.exp(-z * z)

    return METER_MAX * env * lat + ring


def intensity_slit(lam, dist, x, sx, sy):
    u = x / dist
    off = math.hypot(sx - BEST_X, sy - BEST_Y)
    vis = math.exp(-(off / ALIGN_TOL) ** 2)
    base = (_sinc2(math.pi * SLIT_WIDTH * u / lam) *
            math.cos(math.pi * SLIT_SEP * u / lam) ** 2)
    return METER_MAX * vis * base


def _meter(value):
    v = max(0.0, min(METER_MAX, value + random.gauss(0.0, 0.004)))
    return round(v, 2)


def main():
    print(__doc__.split("The structure")[0].strip())
    print()
    print("Type 'help' for the command list.")
    while True:
        sys.stdout.write("optics> ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            break
        p = line.split()
        if not p:
            continue
        cmd = p[0].lower()
        if cmd in ("quit", "exit"):
            break
        if cmd == "help":
            print("Commands:" + __doc__.split("Commands:")[1])
            continue
        try:
            if cmd == "slit":
                sx, sy = float(p[1]) * 1e-3, float(p[2]) * 1e-3
                lam = 632.8e-9
                print("  double slit, lambda = 632.8 nm, L = 50.0 cm, "
                      "sample at (%g, %g) mm" % (sx * 1e3, sy * 1e3))
                print("      x (cm)     V (V)")
                x = -1.5
                while x <= 1.5001:
                    print("  %10.2f %9.2f"
                          % (x, _meter(intensity_slit(lam, 0.50, x * 1e-2, sx, sy))))
                    x += 0.05
            elif cmd == "point":
                lam, dist = float(p[1]) * 1e-9, float(p[2]) * 1e-2
                x, y = round(float(p[3]), 2), round(float(p[4]), 2)
                if not (0.10 <= dist <= 1.00):
                    print("  L must be between 10 and 100 cm")
                    continue
                print("  V = %.2f V at (%.2f, %.2f) cm"
                      % (_meter(intensity_sample(lam, dist, x * 1e-2, y * 1e-2)), x, y))
            elif cmd == "scan":
                lam, dist = float(p[1]) * 1e-9, float(p[2]) * 1e-2
                x0, y0 = float(p[3]), float(p[4])
                ang = math.radians(float(p[5]))
                n, stp = int(p[6]), float(p[7])
                if not (0.10 <= dist <= 1.00):
                    print("  L must be between 10 and 100 cm")
                    continue
                print("      s (cm)    x (cm)    y (cm)     V (V)")
                best = (None, -1)
                for i in range(n):
                    s = (i - (n - 1) / 2.0) * stp
                    x = round(x0 + s * math.cos(ang), 2)
                    y = round(y0 + s * math.sin(ang), 2)
                    v = _meter(intensity_sample(lam, dist, x * 1e-2, y * 1e-2))
                    print("  %10.3f %9.2f %9.2f %9.2f" % (s, x, y, v))
                    if v > best[1]:
                        best = ((x, y), v)
                print("  brightest point: %.2f V at (%.2f, %.2f) cm"
                      % (best[1], best[0][0], best[0][1]))
            else:
                print("  unknown command; type 'help'")
        except (IndexError, ValueError):
            print("  bad arguments; type 'help'")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("expected feature positions (small-angle, L = 90 cm, 633 nm):")
        lam, dist = 633e-9, 0.90
        print("  microsphere ring   S = %.2f cm" % (dist * lam / A_SPHERE * 100))
        print("  crossed fringes    dS_l = %.3f cm, dS_w = %.3f cm"
              % (dist * lam / L_RECT * 100, dist * lam / W_RECT * 100))
        print("  fine grid spots    dS_x = %.3f cm, dS_y = %.3f cm"
              % (dist * lam / DX_GRID * 100, dist * lam / DY_GRID * 100))
        print("  orientation        phi = %g deg" % PHI)
        sys.exit(0)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
