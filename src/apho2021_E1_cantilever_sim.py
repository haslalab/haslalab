#!/usr/bin/env python3
"""APhO 2021 (Taipei, online) -- Experimental Problem 1: Elasticity of a cantilever.

The official programs 1A-1D were graphical (draggable optics, PSD readout,
heater, sample selector) and were never published, so this is a reconstruction
of the same measurements from the official problem statement.  It gives the same
physics and the same observable -- the position d of the reflected laser spot on
the PSD -- so the whole analysis chain of parts A to D can be carried out.

Given by the problem: L = 100 um, w = 35 um, t2 = 0.20 um, t1 = 0.04 um,
E_Si = 280 GPa, I1 = 1.867e-28 m^4, I2 = 2.333e-26 m^4,
alpha1 = 14.2e-6/K, alpha2 = 0.8e-6/K, EI* = 1.84e-13 N m^2, room T = 300 K.

What the program hides from you - the Young's modulus of metal X, the constant
C2 and the coverage ratios of samples 2 and 3 - is what parts C and D ask for;
the values are in the constants at the top of this file if you want to check
your answers afterwards.

Commands:
    force F [D]     apply a point load of F nN            (program 1B)
    temp  T [D]     set the heater to T kelvin            (program 1C)
    sample N [D]    select protein sample N = 0..3        (program 1D)
    scan force FROM TO STEP [D]     sweep a series of loads
    scan temp  FROM TO STEP [D]     sweep a series of temperatures
    D is the cantilever-to-PSD distance in mm (default 50).  D sets the gain of
    the optical lever: a large D resolves small deflections, a small D keeps the
    spot on the PSD over a wide range - part C in particular needs D around 10 mm
    to fit five well-spaced temperatures inside the +-1 mm window.
    quit
"""

import math
import random
import sys

L_C, W_C = 100e-6, 35e-6
T1, T2 = 0.04e-6, 0.20e-6
E_SI = 280e9
I1, I2 = 1.867e-28, 2.333e-26
ALPHA1, ALPHA2 = 14.2e-6, 0.8e-6
EI_STAR = 1.84e-13
PSD_RANGE = 1.0e-3
PSD_NOISE = 3e-9
T_ROOM = 300.0
D0_OFFSET = 1.23e-5          # fixed offset of the aligned spot [m]

E_METAL = 70e9
C2_HID = 0.05
CR = {0: 0.0, 1: 0.0100, 2: 0.0035, 3: 0.0072}


def spot(delta, dist):
    """Optical lever: the free end tilts by 3 delta / (2 L), the reflected ray
    turns by twice that, so the spot moves by 3 delta D / L."""
    return 3.0 * delta * dist / L_C


def deflection_force(force_n):
    return force_n * L_C ** 3 / (3.0 * E_SI * I2)


def deflection_thermal(temp_k):
    h = T1 + T2
    num = (ALPHA1 - ALPHA2) * (temp_k - T_ROOM)
    den = (2.0 / (h * W_C) *
           ((T1 * E_METAL + T2 * E_SI) / (T1 * E_METAL * T2 * E_SI)) *
           (E_METAL * I1 + E_SI * I2) + 0.5 * h)
    return num / den * L_C ** 2


def deflection_protein(sample):
    return C2_HID * CR[sample] / EI_STAR * L_C ** 4


def reading(delta, dist_mm):
    d = D0_OFFSET + spot(delta, dist_mm * 1e-3) + random.gauss(0.0, PSD_NOISE)
    if abs(d) > PSD_RANGE:
        return None
    return d


def report(label, delta, dist_mm):
    d = reading(delta, dist_mm)
    if d is None:
        print("  %-22s spot off the PSD (|d| > 1 mm)" % label)
        return
    print("  %-22s d = %10.4f mm   (delta d = %9.4f mm)"
          % (label, d * 1e3, (d - D0_OFFSET) * 1e3))


def main():
    print(__doc__.split("What the program hides")[0].strip())
    print()
    print("Type 'help' for the command list. The reference reading d0 is the one "
          "you get with\nzero load, room temperature and sample 0.")
    dist = 50.0
    while True:
        sys.stdout.write("cantilever> ")
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
            if cmd == "force":
                f = float(p[1])
                if len(p) > 2:
                    dist = float(p[2])
                report("F = %g nN" % f, deflection_force(f * 1e-9), dist)
            elif cmd == "temp":
                t = float(p[1])
                if t < T_ROOM:
                    print("  the heater cannot go below room temperature, 300 K")
                    continue
                if len(p) > 2:
                    dist = float(p[2])
                report("T = %g K" % t, deflection_thermal(t), dist)
            elif cmd == "sample":
                n = int(p[1])
                if n not in CR:
                    print("  samples are 0, 1, 2 and 3")
                    continue
                if len(p) > 2:
                    dist = float(p[2])
                report("sample %d" % n, deflection_protein(n), dist)
            elif cmd == "scan":
                what = p[1].lower()
                a, b, st = float(p[2]), float(p[3]), float(p[4])
                if len(p) > 5:
                    dist = float(p[5])
                n = int(abs((b - a) / st)) + 1
                for i in range(n):
                    v = a + i * st
                    if what == "force":
                        report("F = %g nN" % v, deflection_force(v * 1e-9), dist)
                    elif what == "temp":
                        report("T = %g K" % v, deflection_thermal(v), dist)
                    else:
                        print("  scan force|temp FROM TO STEP")
                        break
            else:
                print("  unknown command; type 'help'")
        except (IndexError, ValueError):
            print("  bad arguments; type 'help'")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("part B, D = 50 mm:")
        for f in (0.5, 1.0, 1.5, 2.0, 2.5):
            report("F = %g nN" % f, deflection_force(f * 1e-9), 50)
        print("C1 = delta / delta_d = %.4e" % (L_C / (3 * 0.05)))
        print("part C, D = 50 mm:")
        for t in (300, 301, 302, 303, 304):
            report("T = %g K" % t, deflection_thermal(t), 50)
        print("part D, D = 50 mm:")
        for s in (0, 1, 2, 3):
            report("sample %d" % s, deflection_protein(s), 50)
        sys.exit(0)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
