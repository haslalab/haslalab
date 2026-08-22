#!/usr/bin/env python3
"""IPhO 2022 (Switzerland, online) -- Experimental Problem 1: Planet.

Re-implementation of the official command-line simulator Exp1.exe / Exp1.Linux /
Exp1.Linux64 (the Mac build lives inside ExperimentOSX-v1.dmg).  The official
source code was never released, so the integrator below is written from the
problem statement, and the hidden planet is set to the parameter set that the
official solutions extract:

    g      = 15.8  m/s^2      (official answer 15.7 +- 0.5)
    T_p    = 28000 s ~ 7.8 h  (official answer 28000 s +- 0.2 h)
    u      = 1.31  m/s        wind along the equator
    rho_a0 = 0.60  kg/m^3     (official answer 0.60 +- 0.07)
    H_0    = 7500  m          (official answer 7500 m)
    gamma  = 1.4
    -> mu  = 72 g/mol, p0 = 20.3 kPa, both matching the official answers.

Consistency checks reproduced by this program:
    terminal speed at the surface for r = 5 cm, rho = 0.1 g/cm^3 -> 27.0 m/s
    (official solution: v_t0 = 27.0 m/s)

Interface, ranges, rounding and the authorization key are those of the original
(the key is printed in the official Q1 PDF).

Run:  python ipho2022_e1_planet.py
Quit: Ctrl+C
"""

import math
import random
import sys

AUTH_KEY = "12345678.888"      # printed in the official exam paper

# --- hidden planet ------------------------------------------------------------
G_ACC = 15.8            # free-fall acceleration [m/s^2]
T_DAY = 28000.0         # length of a day [s]
OMEGA = 2.0 * math.pi / T_DAY
WIND = 1.31             # uniform wind along the equator [m/s]
RHO_A0 = 0.60           # air density at the base of the tower [kg/m^3]
H_ATM = 7500.0          # thickness of the adiabatic atmosphere [m]
GAMMA = 1.4
T0_C = 20.0             # ground temperature [deg C]

# --- given / fixed ------------------------------------------------------------
H_TOWER = 2000.0
R_MIN, R_MAX = 5.0, 50.0          # cm
RHO_MIN, RHO_MAX = 0.1, 10.0      # g/cm^3
CD = 0.24                         # F_d = 0.24 A rho_a v^2

# --- measurement noise --------------------------------------------------------
SIGMA_T = 0.01          # s
SIGMA_S = 0.05          # m

BAR = "=" * 48


def air_density(z):
    if z >= H_ATM:
        return 0.0
    return RHO_A0 * (1.0 - z / H_ATM) ** (1.0 / (GAMMA - 1.0))


def drop(h, r_cm, rho_gcc):
    """Return (fall time [s], horizontal deflection [m])."""
    r = r_cm * 1e-2
    rho = rho_gcc * 1e3
    area = math.pi * r * r
    mass = 4.0 / 3.0 * math.pi * r ** 3 * rho
    kdrag = CD * area / mass

    x, z = 0.0, h
    vx, vz = 0.0, 0.0
    t = 0.0

    def deriv(state):
        _x, _z, _vx, _vz = state
        ra = air_density(_z)
        rx, rz = _vx - WIND, _vz                    # velocity relative to the air
        vrel = math.hypot(rx, rz)
        ax = -kdrag * ra * vrel * rx - 2.0 * OMEGA * _vz
        az = -kdrag * ra * vrel * rz - G_ACC + 2.0 * OMEGA * _vx
        return _vx, _vz, ax, az

    dt = 2.0e-3
    state = (x, z, vx, vz)
    while state[1] > 0.0:
        step = dt
        # never overshoot the ground by much
        if state[3] < 0 and state[1] / (-state[3]) < step:
            step = max(state[1] / (-state[3]) * 0.5, 1e-6)
        k1 = deriv(state)
        s2 = tuple(state[i] + 0.5 * step * k1[i] for i in range(4))
        k2 = deriv(s2)
        s3 = tuple(state[i] + 0.5 * step * k2[i] for i in range(4))
        k3 = deriv(s3)
        s4 = tuple(state[i] + step * k3[i] for i in range(4))
        k4 = deriv(s4)
        state = tuple(state[i] + step / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
                      for i in range(4))
        t += step
        if t > 1.0e5:
            break

    return t, abs(state[0])


def _prompt(label, lo, hi, unit_lo, unit_hi, quant):
    line = "%3s < %-13s < %-5s | %13s: " % (unit_lo, label, unit_hi, label)
    while True:
        sys.stdout.write(line)
        sys.stdout.flush()
        raw = sys.stdin.readline()
        if not raw:
            raise EOFError
        try:
            v = float(raw.strip())
        except ValueError:
            print("Value entered is not a number.")
            continue
        if not (lo <= v <= hi):
            print("Value out of range.")
            continue
        return round(v / quant) * quant


def main():
    sys.stdout.write("Enter Valid Authorization Key: ")
    sys.stdout.flush()
    key = (sys.stdin.readline() or "").strip()
    if key != AUTH_KEY:
        print("Invalid key -- the program is now in test mode; restart it and use "
              "the authorization key printed in the exam paper.")
        return
    print()

    while True:
        h = _prompt("h (m)", 0.0, H_TOWER, "  0", "2000", 1.0)
        r = _prompt("r (cm)", R_MIN, R_MAX, "  5", "  50", 1.0)
        rho = _prompt("rho (g/cm^3)", RHO_MIN, RHO_MAX, "0.1", "10.0", 0.01)
        print("...")

        t, s = drop(h, r, rho)
        t += random.gauss(0.0, SIGMA_T)
        s += random.gauss(0.0, SIGMA_S)
        print("t (s) = %.1f, s (m) = %.1f" % (t, s))
        print(BAR)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("terminal speed check (r=5cm, rho=0.1): expect ~27.0 m/s")
        r, rho = 0.05, 100.0
        m = 4 / 3 * math.pi * r ** 3 * rho
        a = math.pi * r * r
        print("  v_t0 = %.1f m/s" % math.sqrt(m * G_ACC / (CD * a * RHO_A0)))
        mu = GAMMA / (GAMMA - 1) * 8.314 * (T0_C + 273.15) / (G_ACC * H_ATM)
        print("  mu   = %.0f g/mol" % (mu * 1000))
        print("  p0   = %.0f Pa" % (RHO_A0 * 8.314 * (T0_C + 273.15) / mu))
        for hh, rr, dd in ((2000, 50, 10), (1000, 50, 10), (500, 5, 0.1), (2000, 5, 0.1)):
            tt, ss = drop(hh, rr, dd)
            print("  h=%4d r=%2d rho=%4.1f -> t=%6.2f s, s=%6.2f m" % (hh, rr, dd, tt, ss))
        sys.exit(0)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
