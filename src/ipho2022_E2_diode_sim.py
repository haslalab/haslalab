#!/usr/bin/env python3
"""IPhO 2022 (Switzerland, online) -- Experimental Problem 2: Cylindrical Diode.

Re-implementation of the official command-line simulator Exp2.exe / Exp2.Linux /
Exp2.Linux64.  The official source was never released; the model below is the
Langmuir-Blodgett space-charge law for a cylindrical diode,

    I_inf = C * (L_E / R_C) * V^(3/2) * beta2(10) / beta2(R_C/R_E)

with the finite-length correction of the problem statement,

    I = I_inf * F(x),   x = R_C / L_E

The two free constants are pinned to the official solutions:

  * C = 16.5 uA/V^(3/2) at R_C = 10 R_E   (official B.1 answer, window 16.2-16.8)
  * F(x) = 1 + 0.1242 x + 0.0287 x^2, a fit to the official Part C data table,
    normalised to F -> 1 for L_E >> R_C so that Eq. (1) is the F = 1 limit.

Consequently the exponents recovered from this program are gamma = 1.50,
beta ~ 0.98 and alpha ~ -0.98, exactly as in the official solutions, F grows
with R_C, falls with L_E and is independent of V and R_E, and the Part C slope
comes out near the official B = 0.176.

beta2 is Langmuir's function, obtained by integrating
    phi'' + (4/3) phi' + (4/9) phi = phi^(-1/2),  phi ~ (9/4)^(2/3) s^(4/3)
and setting beta^2 = (4/9) phi^(3/2); it reproduces the textbook value
beta^2(R_C/R_E = 10) = 0.98.

Ammeter behaviour (3 significant figures, mA/A autoranging, 40 A burn-out) and
the +-0.5 mm / +-0.5 V input uncertainties follow the problem statement.

Run:  python ipho2022_e2_cylindrical_diode.py
Quit: Ctrl+C
"""

import bisect
import math
import random
import sys

AUTH_KEY = "12345678.888"      # printed in the official exam paper

EPS0 = 8.8541878128e-12
E_CHG = 1.602176634e-19
M_E = 9.1093837015e-31

C_COEFF = 16.5e-6              # A / V^(3/2), at R_C = 10 R_E
I_MAX = 40.0                   # ammeter rating [A]

LEN_SIGMA = 0.0005 / math.sqrt(3)   # m, "as much as 0.5 mm" in any length
V_SIGMA = 0.5 / math.sqrt(3)        # V, "as much as 0.5 V"

# --- Langmuir's beta^2, tabulated in ln(R_C/R_E) ------------------------------
_LN = [0.00, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90,
       1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80, 1.90, 2.00, 2.10,
       2.20, 2.302585, 2.40, 2.60, 2.80, 3.00, 3.50, 4.00, 4.50, 5.00]
_B2 = [0.00000, 0.00240, 0.00924, 0.01997, 0.03412, 0.07095, 0.11664, 0.16861,
       0.22475, 0.28333, 0.34295, 0.40245, 0.46098, 0.51783, 0.57245, 0.62449,
       0.67365, 0.71976, 0.76273, 0.80252, 0.83913, 0.87264, 0.90312, 0.93070,
       0.95549, 0.97819, 0.99732, 1.02982, 1.05425, 1.07181, 1.09288, 1.09258,
       1.08133, 1.06585]
_B2_AT_10 = 0.97819


def beta2(ratio):
    """Langmuir's beta^2 for R_C/R_E."""
    g = math.log(max(ratio, 1.0 + 1e-9))
    if g >= _LN[-1]:
        return _B2[-1]
    i = bisect.bisect_right(_LN, g) - 1
    i = min(max(i, 0), len(_LN) - 2)
    f = (g - _LN[i]) / (_LN[i + 1] - _LN[i])
    return _B2[i] + f * (_B2[i + 1] - _B2[i])


def f_correction(x):
    """Finite-emitter-length correction, x = R_C / L_E."""
    return 1.0 + 0.1242 * x + 0.0287 * x * x


def current(rc_m, re_m, le_m, volt):
    """Maximum diode current [A] for collector radius rc, emitter radius re,
    emitter length le (all in metres) and collector potential volt [V]."""
    if volt <= 0 or rc_m <= re_m:
        return 0.0
    b2 = beta2(rc_m / re_m)
    if b2 <= 0:
        return 0.0
    i_inf = C_COEFF * (le_m / rc_m) * volt ** 1.5 * _B2_AT_10 / b2
    return i_inf * f_correction(rc_m / le_m)


def display_current(amp):
    """Auto-ranging ammeter with three significant figures."""
    if amp >= 1.0:
        return "%s A" % _sig3(amp)
    return "%s mA" % _sig3(amp * 1000.0)


def _sig3(v):
    if v == 0:
        return "0.00"
    d = math.floor(math.log10(abs(v)))
    dec = max(0, 2 - int(d))
    return "%.*f" % (dec, round(v, dec))


def _ask(prompt, lo, hi, step):
    while True:
        sys.stdout.write(prompt)
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
        return round(v / step) * step


def main():
    sys.stdout.write("Enter Valid Authorization Key: ")
    sys.stdout.flush()
    if (sys.stdin.readline() or "").strip() != AUTH_KEY:
        print("Invalid key -- the program is now in test mode; restart it and use "
              "the authorization key printed in the exam paper.")
        return
    print()

    burnt = False
    while True:
        rc = _ask(" 0.1 <  Rc (cm) < 20.0 |  Rc (cm): ", 0.1, 20.0, 0.1)
        re = _ask(" 0.1 <  Re (cm) < 20.0 |  Re (cm): ", 0.1, 20.0, 0.1)
        le = _ask(" 1.0 <  Le (cm) < 99.0 |  Le (cm): ", 1.0, 99.0, 0.1)
        v = _ask("   0 <   V (V)  < 2000 |   V (V) : ", 0.0, 2000.0, 1.0)
        print("...")

        if re >= rc:
            print("The emitter must fit inside the collector.")
            print("=" * 48)
            continue

        rc_m = rc * 1e-2 + random.gauss(0.0, LEN_SIGMA)
        re_m = re * 1e-2 + random.gauss(0.0, LEN_SIGMA)
        le_m = le * 1e-2 + random.gauss(0.0, LEN_SIGMA)
        v_r = max(0.0, v + random.gauss(0.0, V_SIGMA))

        amp = current(rc_m, re_m, le_m, v_r)
        if amp > I_MAX:
            print("The ammeter has burnt out! It has been replaced for the next "
                  "measurement.")
            burnt = True
        else:
            print("I = %s" % display_current(amp))
        print("=" * 48)
        if burnt:
            burnt = False


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("beta^2(10) = %.4f  (textbook 0.98)" % beta2(10.0))
        rows = [(20, 2, 10, 2000), (20, 2, 15, 2000), (20, 2, 20, 2000),
                (20, 2, 30, 2000), (20, 2, 40, 2000), (6, 0.6, 10, 2000),
                (8, 0.8, 10, 2000), (10, 1, 10, 2000), (15, 1.5, 10, 2000),
                (10, 1, 99, 2000)]
        print(" Rc   Re   Le     V        I        x       F")
        for rc, re, le, v in rows:
            amp = current(rc * 1e-2, re * 1e-2, le * 1e-2, v)
            x = rc / le
            print("%4.0f %4.1f %4.0f %5.0f %9s %8.3f %7.3f"
                  % (rc, re, le, v, display_current(amp), x, f_correction(x)))
        print("\nexponent check (Rc=10, Re=1, Le=99):")
        import math as _m
        i1 = current(0.10, 0.01, 0.99, 1000.0)
        i2 = current(0.10, 0.01, 0.99, 2000.0)
        print("  gamma = %.3f" % (_m.log(i2 / i1) / _m.log(2.0)))
        j1 = current(0.10, 0.01, 0.20, 2000.0)
        j2 = current(0.10, 0.01, 0.99, 2000.0)
        print("  beta  = %.3f" % (_m.log(j2 / j1) / _m.log(0.99 / 0.20)))
        k1 = current(0.05, 0.005, 0.99, 2000.0)
        k2 = current(0.20, 0.020, 0.99, 2000.0)
        print("  alpha = %.3f" % (_m.log(k2 / k1) / _m.log(0.20 / 0.05)))
        c = current(0.10, 0.01, 0.99, 2000.0) / ((0.99 / 0.10) * 2000.0 ** 1.5)
        print("  C     = %.2f uA/V^1.5" % (c * 1e6))
        sys.exit(0)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
