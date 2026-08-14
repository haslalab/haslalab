#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APhO 2023 (Ulaanbaatar) Experimental Problem 1
"Hertzian Contact Stress"

Pendulum bench + oscilloscope simulator.

------------------------------------------------------------------------
[ LAYOUT ]   (apparatus photograph, Figure 2 of Q1-3)
    base platform            extruded rail with the blue tape scale
    angle measuring screens  two fans, pivot at the top centre, 0 deg
                             straight down, growing to 90 deg either side
    pendulum 1 / 2           hanger unit slides in the slot   -> d_x
                             string tuning knob sets the wire -> d_z
    photogate                slides along the rail
    electromagnetic holder   on its own rod stand, sets phi0
    electric junction box    CH1 = photogate | ball wires
    oscilloscope             Siglent SDS 1202X-E

    Balls: a BIG one (d = 31.75 mm, m = 131.48 g) is already hung on each
    hanger and two SMALL ones (d = 25.42 mm, m = 67.55 g) come in the box,
    which is exactly what Q1-10 quotes.

[ PHYSICAL MODEL ]
    Each ball is a rigid body on a UNILATERAL wire - the thread pulls but
    cannot push, so an oblique impact that throws a ball upwards really
    lets the wire go slack.  The pair interacts through a Hertzian normal
    force  F = k delta^1.5,  k = (4/3) E' sqrt(R1R2/(R1+R2)), plus Coulomb
    friction, integrated with the step cut to tau/400 during contact.
    Everything the problem asks about comes out of these equations:

        T(phi0) = 4 sqrt(l/g) K(sin^2(phi0/2))
        1/dt    = 2 sqrt(gl)/d * sin(phi0/2)          -> A.1 gradient
        T       = T0 (1 + a sin^2 + b sin^4 + ...)    -> a = 1/4, b = 9/64
        tau     = A (R1+R2)/c (c/v)^(1/5)             -> A = 2.40

[ CALIBRATION ]  (against APhO_2023_S4, the official solution)
        grad(1/dt)  110.77 s^-1     simulated 110.1
        k_v         3.517 m/s       simulated 3.497
        T0          1.1267 s        simulated 1.1264
        alpha,beta  0.251 / 0.149   simulated 0.262 / 0.137
        g_UB        9.804 m/s^2     simulated 9.75
        tau(70 deg) 81.7 us         simulated 81.0
        A           2.40            simulated 2.37
    The contact stiffness carries +12 % over the ideal Hertz value (finite
    half space, curvature, oxide film).  The student still analyses the
    data with the nominal E = 200 GPa, nu = 0.3 of the question sheet.

[ ERROR MODEL   (drawn once per release) ]
  . protractor / hanger setting   phi0 +- 0.25 deg
  . wire length tolerance         l    +- 0.12 %
  . air damping                   Q = 2600 +- 6 %
  . electromagnet release         the FIRST crossing is slowed by ~2 % by
                                  residual magnetisation and wire
                                  elasticity and delayed by ~6 ms
                                  -> never use pulse 1
  . wire ring after release       1.4 mm at 11.5 Hz, decaying in 0.16 s
  . photogate comparator jitter   +- 4 us
  . contact bounce                a tilted line of centres opens the
                                  circuit for a fraction of the breathing
                                  period of the balls, 138 / 172 kHz

[ THE OSCILLOSCOPE IS A REAL ACQUISITION CHAIN ]
    fs   = acquisition memory / (14 x Time/div), snapped to 1-2-2.5-5 and
           limited to 1 GSa/s
    ADC  = 8 bit over the 8 vertical divisions selected at the shot
    the record is FROZEN by Single, so turning Time/div afterwards only
    zooms into memory - it never resamples
    rendering = sin(x)/x below ~2 samples per pixel, peak detect above
  so an 80 us contact pulse caught on a slow time base is rebuilt out of
  one or two samples and comes out as a sinc, often split into two humps.

[ HOW TO WORK ]
  . there is no table, no graph and no analysis here.  You read the
    instrument and write the numbers on your own answer sheet.
  . the screen carries the same 14 x 8 graticule as the real one with a
    0.1 division minor grid, and there is no zoom beyond the real Time/div
    and Volts/div.  Put the half amplitude of the edge on the centre line
    and read M Pos, exactly as the General Instructions describe.
------------------------------------------------------------------------
"""

import time
import copy
import math
import threading
import random

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.patches import (Circle, Rectangle, Wedge,
                                FancyBboxPatch)
from matplotlib.collections import LineCollection
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --------------------------- apparatus constants -----------------------
G_UB = 9.804                 # m/s^2, free fall acceleration in Ulaanbaatar
L_PEND = 0.315405            # m, wire length that gives T0 = 1.1267 s
E_YOUNG = 200.0e9            # Pa, steel
NU_POISSON = 0.30
E_REDUCED = 1.0 / (2.0 * (1.0 - NU_POISSON ** 2) / E_YOUNG)
C_SOUND = 5180.0             # m/s, sqrt(E'/rho) as used by the organisers
C_TAU = 2.755                # fitted to the whole official Part D / E table

BALLS = [
    ("big ball    d = 31.75 mm   m = 131.48 g", 31.75e-3, 131.48e-3),
    ("small ball  d = 25.42 mm   m =  67.55 g", 25.42e-3, 67.55e-3),
]

SEL_NAMES = {"univ": "UNIVERSAL (M Pos, fine)",
             "hpos": "HORIZONTAL POSITION (M Pos)",
             "hscale": "TIME/DIV", "vpos": "CH1 vertical POSITION",
             "vscale": "CH1 VOLTS/DIV", "vpos2": "CH2 vertical POSITION",
             "vscale2": "CH2 VOLTS/DIV", "trig": "TRIGGER LEVEL"}

V_LOW = -0.1                # the photogate rest level

LEG_X, LEG_W = np.polynomial.legendre.leggauss(96)


def eng(v, unit=""):
    """Format a time the way the instrument prints it."""
    if v is None:
        return "----"
    a = abs(v)
    if a >= 1.0:
        return "%.6f %s" % (v, unit)
    if a >= 1e-3:
        return "%.4f m%s" % (v * 1e3, unit)
    if a >= 1e-6:
        return "%.3f u%s" % (v * 1e6, unit)
    return "%.1f n%s" % (v * 1e9, unit)


def hertz_contact_time(m1, m2, R1, R2, v_rel):
    """
    Hertzian contact time of two elastic spheres.
        tau = C (mu^2 / (R* E'^2 v))^(1/5)
    with C = 2.755 fitted to the whole official Part D / Part E table.
    Equivalent to  tau = 2.40 (R1+R2)/c (c/v_1c)^(1/5)  for equal balls.
    """
    if v_rel <= 0:
        return None
    mu = m1 * m2 / (m1 + m2)
    Rs = R1 * R2 / (R1 + R2)
    return C_TAU * (mu ** 2 / (Rs * E_REDUCED ** 2 * v_rel)) ** 0.2


def sphere_mode_frequency(R):
    """
    Lowest spheroidal (breathing) mode of a solid steel sphere,
    f = 0.844 c / (2R).  For the supplied balls this is 138 - 243 kHz, i.e.
    the balls ring 11 to 24 times during one Hertzian contact, which is why
    a badly aligned collision can momentarily break the electrical contact.
    """
    return 0.844 * C_SOUND / (2.0 * R)


# ==========================================================================
#  Q1 - THE APPARATUS :  state of the 2D bench + full dynamic simulation
# ==========================================================================
# The measured contact stiffness of the real balls sits about 10 % above the
# ideal Hertz value (finite half space, surface curvature, thin oxide film).
# Using it here makes the SIMULATED contact time reproduce the official
# Part D table, while the students still analyse their own data with the
# nominal E = 200 GPa / nu = 0.3 quoted in the question sheet.
E_CONTACT = E_REDUCED * 1.1220

#  SDS1202X-E, from the user manual and datasheet:
#    time base 1 ns/div .. 100 s/div in a 1-2-5 sequence
#    vertical 500 uV/div .. 10 V/div in a 1-2-5 sequence
#    memory 14k / 140k / 1.4M / 14M, 1 GSa/s single channel
#    Roll is available at 50 ms/div and slower
TIME_DIVS = ([v * 10.0 ** k for k in range(-9, 2) for v in (1.0, 2.0, 5.0)]
             + [100.0])
VOLT_DIVS = ([5.0e-4]
             + [v * 10.0 ** k for k in range(-3, 1) for v in (1.0, 2.0, 5.0)]
             + [10.0])
ROLL_MIN_TDIV = 0.05
MEM_DEPTHS = [14_000, 140_000, 1_400_000, 14_000_000]
FS_MAX = 1.0e9


def tdiv_label(v):
    if v >= 1.0:
        return "%.0f s" % v
    if v >= 1e-3:
        return "%g ms" % (v * 1e3)
    if v >= 1e-6:
        return "%g us" % (v * 1e6)
    return "%g ns" % (v * 1e9)


def mem_label(n):
    if n >= 1_000_000:
        return "%gM" % (n / 1e6)
    if n >= 1000:
        return "%gk" % (n / 1e3)
    return "%d" % n


def fs_label(fs):
    if fs >= 1e9:
        return "%.3g GSa/s" % (fs / 1e9)
    if fs >= 1e6:
        return "%.3g MSa/s" % (fs / 1e6)
    if fs >= 1e3:
        return "%.3g kSa/s" % (fs / 1e3)
    return "%.3g Sa/s" % fs


def snap_fs(fs, fs_max=FS_MAX):
    fs = min(fs, fs_max)
    if fs <= 1.0:
        return 1.0
    dec = 10.0 ** math.floor(math.log10(fs))
    best = dec / 10.0
    for d in (dec / 10.0, dec, dec * 10.0):
        for m in (1.0, 2.0, 2.5, 5.0):
            c = m * d
            if c <= fs * (1.0 + 1e-9) and c > best:
                best = c
    return min(best, fs_max)


def sinx_x(rec, t0, fs, t, ntaps=16):
    """sin(x)/x reconstruction of the frozen record (Siglent default)."""
    n = len(rec)
    idx = (t - t0) * fs
    k0 = np.floor(idx).astype(np.int64)
    out = np.zeros_like(t, dtype=float)
    for j in range(-ntaps, ntaps + 1):
        k = k0 + j
        u = idx - k
        w = np.sinc(u) * np.sinc(u / (ntaps + 1.0))
        valid = (k >= 0) & (k < n)
        out += np.where(valid, rec[np.clip(k, 0, n - 1)] * w, 0.0)
    return out


def contact_segments(t_a, t_b, R_min, psi, rng):
    """
    Split one Hertzian contact into the sub-contacts that the circuit of
    Fig 6 actually sees.  The balls ring at their lowest breathing mode
    f = 0.844 c / 2R (138 - 243 kHz here), 11 to 24 times inside a single
    contact; when the impact is oblique the surfaces separate for a
    fraction of that period and the circuit really opens.
    """
    tau = t_b - t_a
    f_vib = sphere_mode_frequency(R_min)
    T_vib = 1.0 / f_vib
    lam = 4.5 * (max(psi, 0.0) / math.radians(6.0)) ** 1.5 \
        * (tau * f_vib / 12.0)
    u, acc, k, n = rng.random(), math.exp(-lam), 0, 0
    while u > acc and k < 3:
        k += 1
        acc += math.exp(-lam) * lam ** k / math.factorial(k)
        n = k
    breaks = []
    for _ in range(n):
        tc = rng.uniform(0.22, 0.85) * tau
        breaks.append((tc, min(tc + T_vib * rng.uniform(0.12, 0.45),
                               0.97 * tau)))
    breaks.sort()
    merged = []
    for a, b in breaks:
        if merged and a <= merged[-1][1] + 0.05 * T_vib:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    segs, t = [], 0.0
    for a, b in merged:
        if a > t + 0.03 * tau:
            segs.append((t, a))
        t = b
    segs.append((t, tau))
    segs = [(t_a + a, t_a + b) for a, b in segs if b - a > 0.02 * T_vib]
    return segs or [(t_a, t_b)], f_vib


class Bench:
    """
    State of the two-pendulum bench and its dynamic simulation.

    Geometry (side view, x along the rail, z upwards, pivots at z = 0):
        ball centre i = (xh[i] + l[i] sin th_i , -l[i] cos th_i)

    Everything the user drags on the 2D model - hanger position, wire
    length, ball diameter, photogate position, electromagnet angle - feeds
    straight into this state, and the four panels of Figure 4 come out of
    the geometry by themselves:

        l1 != l2                 ->  vertical offset dz          Fig 4.a
        dxh > R1+R2              ->  free gap                    Fig 4.b
        dxh < R1+R2              ->  hangers touch, wires lean   Fig 4.c
        dxh = R1+R2, l1 = l2     ->  contact, wires parallel     Fig 4.d
    """

    def __init__(self, rng):
        self.rng = rng
        R = BALLS[0][1] / 2.0
        self.xh = [-R, +R]
        self.l = [0.31540, 0.31540]
        self.ball = [0, 0]
        self.active2 = True
        self.x_gate = -R - 0.055
        self.phi0 = 27.0
        self.source = "contact"        # junction box : 'photogate' | 'contact'
        self.g = G_UB
        self.air = 0.0025
        self.result = None

    # ---------------- geometry ----------------
    def R(self, i):
        return BALLS[self.ball[i]][1] / 2.0

    def m(self, i):
        return BALLS[self.ball[i]][2]

    def centre(self, i, th):
        return (self.xh[i] + self.l[i] * math.sin(th),
                -self.l[i] * math.cos(th))

    def k_contact(self):
        R1, R2 = self.R(0), self.R(1)
        return (4.0 / 3.0) * E_CONTACT * math.sqrt(R1 * R2 / (R1 + R2))

    def kv(self, i=0):
        return 2.0 * math.sqrt(self.g * self.l[i])

    # ---------------- static equilibrium ----------------
    def equilibrium(self):
        if not self.active2:
            return [0.0, 0.0]
        R1, R2 = self.R(0), self.R(1)
        k = 1.0e7

        def energy(th):
            c1 = self.centre(0, th[0])
            c2 = self.centre(1, th[1])
            u = (-self.m(0) * self.g * self.l[0] * math.cos(th[0])
                 - self.m(1) * self.g * self.l[1] * math.cos(th[1]))
            d = math.hypot(c2[0] - c1[0], c2[1] - c1[1])
            ov = (R1 + R2) - d
            if ov > 0:
                u += 0.4 * k * ov ** 2.5
            return u

        th, step = [0.0, 0.0], 2e-3
        e0 = energy(th)
        for _ in range(300):
            gr = []
            for j in (0, 1):
                tp = list(th)
                tp[j] += 1e-7
                gr.append((energy(tp) - e0) / 1e-7)
            gn = math.hypot(*gr) or 1.0
            moved = False
            for _ in range(30):
                cand = [th[j] - step * gr[j] / gn for j in (0, 1)]
                e1 = energy(cand)
                if e1 < e0:
                    th, e0, moved = cand, e1, True
                    break
                step *= 0.5
            if not moved or step < 1e-10:
                break
            step *= 1.6
        return th

    def config_name(self):
        if not self.active2:
            return "single pendulum   (Part A / B)"
        R1, R2 = self.R(0), self.R(1)
        th = self.equilibrium()
        c1, c2 = self.centre(0, th[0]), self.centre(1, th[1])
        dz = abs(c2[1] - c1[1])
        gap = (self.xh[1] - self.xh[0]) - (R1 + R2)
        lean = max(abs(th[0]), abs(th[1]))
        if dz > 0.6e-3:
            return ("Fig 4.a    dz = %.1f mm, wires almost parallel   (Part C / D)" % (dz * 1e3))
        if gap > 0.4e-3:
            return ("Fig 4.b    free gap  dx - 2R = %.1f mm   (Part C / D)" % (gap * 1e3))
        if gap < -0.2e-3:
            return ("Fig 4.c    hanger units touching by %.1f mm, wires "
                    "lean %.2f deg   (Part C / D)"
                    % (-gap * 1e3, math.degrees(lean)))
        return ("Fig 4.d    in contact, wires parallel, hangers "
                "separate   (Part C / D)")

    def preset(self, which):
        R1 = BALLS[self.ball[0]][1] / 2.0
        R2 = BALLS[self.ball[1]][1] / 2.0
        L0 = 0.31540
        self.active2 = True
        if which == "a":
            self.l = [L0, L0 - 1.5e-3]
            self.xh = [-R1, R2]
        elif which == "b":
            self.l = [L0, L0]
            self.xh = [-R1 - 0.5e-3, R2 + 0.5e-3]
        elif which == "c":
            self.l = [L0, L0]
            self.xh = [-R1 + 0.9e-3, R2 - 0.9e-3]
        else:
            self.l = [L0, L0]
            self.xh = [-R1, R2]
        self.x_gate = self.xh[0]

    # ---------------- dynamics ----------------
    def simulate(self, tmax=10.0, frame_dt=0.004, max_steps=2_000_000,
                 init=None):
        """
        Full planar simulation of the two pendulums.

        Each ball carries 3 degrees of freedom - x, z and its own spin - and
        hangs on a UNILATERAL wire: the nylon thread can pull but not push,
        so an impact that throws a ball upwards really does let the wire go
        slack and the ball flies free for a moment.  The balls interact
        through a Hertzian normal force plus Coulomb friction at the contact
        point, which is what converts an oblique (dz offset, leaning wire)
        impact into spin and vertical bobbing.  That is the whole content of
        Part C: the four panels of Figure 4 differ only in the direction of
        the line of centres and in where the pivots are, and everything else
        follows from these equations.
        """
        rng = self.rng
        R1, R2 = self.R(0), self.R(1)
        m1, m2 = self.m(0), self.m(1)
        Is1, Is2 = 0.4 * m1 * R1 ** 2, 0.4 * m2 * R2 ** 2
        l1, l2 = self.l
        k = self.k_contact()
        two = self.active2
        mu_f = 0.15
        th_eq = self.equilibrium()

        P1 = (self.xh[0], 0.0)
        P2 = (self.xh[1], 0.0)
        a1 = -math.radians(self.phi0)          # pulled away from ball 2
        p1 = [P1[0] + l1 * math.sin(a1), -l1 * math.cos(a1)]
        p2 = [P2[0] + l2 * math.sin(th_eq[1]), -l2 * math.cos(th_eq[1])]
        v1, v2 = [0.0, 0.0], [0.0, 0.0]
        sp1 = sp2 = 0.0
        if init is not None:
            # carry on from the state the bench is already in, which is
            # what happens when the second pendulum is hung while the
            # first one is still swinging
            (p1[0], p1[1]), (v1[0], v1[1]) = init[0], init[1]
            (p2[0], p2[1]), (v2[0], v2[1]) = init[2], init[3]
            sp1, sp2 = init[4], init[5]

        amp_w = 1.4e-3 * (1.0 + rng.gauss(0.0, 0.25))
        f_w = 11.5 * (1.0 + rng.gauss(0.0, 0.08))
        z_gate = -l1
        c_hc = 0.0
        dt_c = 2.0e-7
        t_c0 = 0.0
        tau_est = 1.0e-4
        Rsum = R1 + R2
        air = self.air
        # 0.5 rho Cd A for each ball, rho = 1.204, Cd = 0.47
        gg = self.g
        CQ1 = 0.5 * 1.204 * 0.47 * math.pi * R1 ** 2
        CQ2 = 0.5 * 1.204 * 0.47 * math.pi * R2 ** 2

        frames_t, frames = [], []
        gate_edges, contact_edges, impacts = [], [], []
        gate_prev = None
        f_prev = 0.0
        ov_prev = -1.0
        in_contact = False
        t = 0.0
        next_frame = 0.0
        steps = 0

        while t < tmax and steps < max_steps:
            steps += 1
            # ---------------- contact ----------------
            F1 = [0.0, -m1 * self.g]
            F2 = [0.0, -m2 * self.g]
            Tq1 = Tq2 = 0.0
            ov = -1.0
            ddot = 0.0
            if two:
                dx, dz = p2[0] - p1[0], p2[1] - p1[1]
                d = math.hypot(dx, dz) or 1e-12
                ov = Rsum - d
                nx, nz = dx / d, dz / d
                ddot = -((v2[0] - v1[0]) * nx + (v2[1] - v1[1]) * nz)
                if ov > 0.0:
                    if not in_contact:
                        v_imp = max(abs(ddot), 0.01)
                        # hardened steel: the restitution is not quite 1
                        # and it falls as the impact gets harder, so each
                        # bounce takes a little energy out of the pair
                        e_rest = min(0.990, 1.0 - 0.038 * v_imp ** 0.25)
                        c_hc = 3.0 * (1.0 - e_rest) / (2.0 * v_imp)
                        tau_est = hertz_contact_time(m1, m2, R1, R2, v_imp)
                        dt_c = min(max(tau_est / 400.0, 2.0e-8), 2.0e-6)
                        t_c0 = t
                        tx, tz = -nz, nx
                        vt = ((v2[0] - v1[0]) * tx + (v2[1] - v1[1]) * tz)
                        impacts.append((t, math.atan2(abs(vt), v_imp)))
                    Fn = max(k * ov ** 1.5 * (1.0 + c_hc * ddot), 0.0)
                    tx, tz = -nz, nx
                    d1x, d1z = R1 * nx, R1 * nz
                    d2x, d2z = -R2 * nx, -R2 * nz
                    u1x = v1[0] + sp1 * (-d1z)
                    u1z = v1[1] + sp1 * (d1x)
                    u2x = v2[0] + sp2 * (-d2z)
                    u2z = v2[1] + sp2 * (d2x)
                    ut = (u1x - u2x) * tx + (u1z - u2z) * tz
                    Ft = -mu_f * Fn * math.tanh(ut / 0.005)
                    f1x, f1z = -Fn * nx + Ft * tx, -Fn * nz + Ft * tz
                    f2x, f2z = Fn * nx - Ft * tx, Fn * nz - Ft * tz
                    F1[0] += f1x
                    F1[1] += f1z
                    F2[0] += f2x
                    F2[1] += f2z
                    Tq1 = d1x * f1z - d1z * f1x
                    Tq2 = d2x * f2z - d2z * f2x

            # ---------------- time step ----------------
            if ov > 0.0:
                dt = dt_c if (t - t_c0) < 6.0 * tau_est else 2.0e-4
            elif two and ov > -4.0e-3:
                dt = min(max(0.04 * (-ov) / max(abs(ddot), 1e-3), 4.0e-7),
                         2.0e-4)
            else:
                dt = 4.0e-4 if two else 8.0e-4

            # ---------------- unilateral wires ----------------
            for (P, p, v, m, l, F, _sp, _Is, _Tq, idx) in (
                    (P1, p1, v1, m1, l1, F1, sp1, Is1, Tq1, 0),
                    (P2, p2, v2, m2, l2, F2, sp2, Is2, Tq2, 1)):
                # linear (pivot and wire) plus quadratic (air) drag.  For
                # a 31.75 mm steel ball 0.5*rho*Cd*A = 2.2e-4 kg/m, so the
                # decay really is slow: Q is of order 10^3 and the swing
                # lasts many minutes, exactly as it does on the bench.
                vmag = math.hypot(v[0], v[1])
                cq = CQ1 if idx == 0 else CQ2
                F[0] -= (air * m + cq * vmag) * v[0]
                F[1] -= (air * m + cq * vmag) * v[1]
                rx, rz = p[0] - P[0], p[1] - P[1]
                rn = math.hypot(rx, rz) or 1e-12
                hx, hz = rx / rn, rz / rn
                if rn >= l - 1e-9:
                    vr = v[0] * hx + v[1] * hz
                    vt2 = max(v[0] ** 2 + v[1] ** 2 - vr * vr, 0.0)
                    Tn = m * vt2 / l + (F[0] * hx + F[1] * hz)
                    if Tn > 0.0:
                        F[0] -= Tn * hx
                        F[1] -= Tn * hz
                # energy before the step, and the work the drag is meant
                # to take out of it
                E0 = 0.5 * m * (v[0] ** 2 + v[1] ** 2) + m * gg * p[1]
                sp0 = math.hypot(v[0], v[1])
                dW = (air * m + cq * sp0) * sp0 * sp0 * dt
                v[0] += F[0] / m * dt
                v[1] += F[1] / m * dt
                p[0] += v[0] * dt
                p[1] += v[1] * dt
                rx, rz = p[0] - P[0], p[1] - P[1]
                rn = math.hypot(rx, rz) or 1e-12
                if rn > l:
                    hx, hz = rx / rn, rz / rn
                    p[0] = P[0] + hx * l
                    p[1] = P[1] + hz * l
                    vr = v[0] * hx + v[1] * hz
                    if vr > 0.0:
                        v[0] -= vr * hx
                        v[1] -= vr * hz
                # Projecting the wire constraint quietly eats energy: with
                # the drag switched off the swing still died away, which is
                # numerical, not physical.  Put back exactly what the step
                # was not supposed to lose.
                if ov <= 0.0:
                    ke = E0 - dW - m * gg * p[1]
                    vsq = v[0] ** 2 + v[1] ** 2
                    if ke > 0.0 and vsq > 1e-16:
                        sc = math.sqrt(2.0 * ke / (m * vsq))
                        if 0.5 < sc < 2.0:
                            v[0] *= sc
                            v[1] *= sc
            sp1 += Tq1 / Is1 * dt
            sp2 += Tq2 / Is2 * dt
            t += dt

            # ---------------- photogate ----------------
            wire = amp_w * math.exp(-t / 0.16) * math.sin(2 * math.pi * f_w * t)
            xb = p1[0] + wire
            if abs(p1[1] - z_gate) < 0.020:
                f_now = R1 - abs(xb - self.x_gate)
            else:
                f_now = -1.0
            inside = f_now > 0.0
            if gate_prev is None:
                gate_prev, f_prev = inside, f_now
            else:
                if inside != gate_prev:
                    den = f_prev - f_now
                    fr = f_prev / den if abs(den) > 1e-15 else 0.5
                    gate_edges.append((t - dt + min(max(fr, 0.0), 1.0) * dt,
                                       inside))
                    gate_prev = inside
                f_prev = f_now

            now = ov > 0.0
            if now != in_contact:
                den = ov_prev - ov
                fr = ov_prev / den if abs(den) > 1e-18 else 0.5
                contact_edges.append((t - dt + min(max(fr, 0.0), 1.0) * dt,
                                      now))
                in_contact = now
            ov_prev = ov

            if t >= next_frame:
                frames_t.append(t)
                frames.append((p1[0], p1[1], p2[0], p2[1], sp1, sp2))
                next_frame += frame_dt

        def to_intervals(edges):
            out, start = [], None
            for tt, rising in edges:
                if rising and start is None:
                    start = tt
                elif (not rising) and start is not None:
                    out.append((start, tt))
                    start = None
            return out

        gate = to_intervals(gate_edges)
        contact = to_intervals(contact_edges)

        segs = []
        f_vib = sphere_mode_frequency(min(R1, R2))
        psi_first = 0.0
        for idx, (a_, b_) in enumerate(contact):
            psi = impacts[idx][1] if idx < len(impacts) else 0.0
            if idx == 0:
                psi_first = psi
            ss, f_vib = contact_segments(a_, b_, min(R1, R2), psi, rng)
            segs.extend(ss)

        self.result = dict(t=np.array(frames_t),
                           p=np.array(frames) if frames else np.zeros((0, 6)),
                           gate=gate, contact=contact, segments=segs,
                           psi=psi_first, f_vib=f_vib, th_eq=th_eq,
                           steps=steps)
        return self.result



def make_pulse_signal(pulses, v_hi=5.0, v_lo=-0.1, t_rise=1.2e-4, noise=0.02,
                      ring_f=None, ring_a=0.0, ring_q=6.0, seed=11):
    """
    Analogue signal delivered to CH1.

    pulses  : list of (t_rise, t_fall) intervals during which the level is
              high (photogate blocked, or the contact circuit closed)
    ring_f  : if given, the breathing mode of the balls modulates the contact
              resistance, so the top of a contact pulse is not flat but rings
              at ring_f with a decay time ring_q / ring_f
    """
    w = max(t_rise / 2.2, 1e-9)
    P = list(pulses)
    rng = np.random.default_rng(seed)

    def sig(t):
        t = np.asarray(t, dtype=float)
        v = np.zeros_like(t)
        # only touch the samples that are actually near a pulse: the record
        # can be 14 Mpts long and the pulses occupy a tiny part of it
        asc = t.size > 1 and t[1] >= t[0]
        for a, b in P:
            lo, hi = a - 8.0 * w, b + 8.0 * w
            if asc:
                i0 = int(np.searchsorted(t, lo))
                i1 = int(np.searchsorted(t, hi))
                if i1 <= i0:
                    continue
                sl = slice(i0, i1)
            else:
                m = (t >= lo) & (t <= hi)
                if not m.any():
                    continue
                sl = m
            tt = t[sl]
            g = 0.5 * (np.tanh((tt - a) / w) - np.tanh((tt - b) / w))
            if ring_f and ring_a:
                dt = np.maximum(tt - a, 0.0)
                g = g * (1.0 + ring_a * np.exp(-dt * ring_f / ring_q)
                         * np.sin(2.0 * np.pi * ring_f * dt))
            v[sl] += g
        v = v_lo + (v_hi - v_lo) * np.clip(v, 0.0, 1.2)
        return v + rng.normal(0.0, noise, t.shape)

    return sig



# ══════════════════════════════════════════════════════════════════
#  ONE RELEASE  =  one Run.  All the tolerances are drawn here, once.
# ══════════════════════════════════════════════════════════════════
class Run:
    """
    One press of "release ball 1".  It carries the frozen oscilloscope
    record and the frames of the animation, so nothing is re-randomised
    while you are measuring - exactly like a real single shot.
    """

    def __init__(self, bench, t_div, v_div, mem, tmax=10.0,
                 init=None, build=True):
        self.res = bench.simulate(tmax=tmax, init=init)
        self.source = bench.source
        if bench.source == "photogate":
            pulses = self.res["gate"]
            sig = make_pulse_signal(pulses, v_hi=5.0, t_rise=1.3e-4,
                                    noise=0.02)
            feature = 1.3e-4
        else:
            pulses = self.res["segments"] or self.res["contact"]
            sig = make_pulse_signal(pulses, v_hi=4.0, t_rise=2.0e-6,
                                    noise=0.012,
                                    ring_f=self.res["f_vib"], ring_a=0.045)
            feature = min([b - a for a, b in pulses]) if pulses else None
        self.pulses = pulses
        self.feature = feature
        self.sig = sig
        self.t0_trig = pulses[0][0] if pulses else 0.0
        self.analog = (lambda t: self.sig(np.asarray(t) + self.t0_trig))
        self.rec = None
        if pulses:
            self.acquire(t_div, v_div, mem, build=build)

    @staticmethod
    def derive(res, source):
        """
        Pulse train and analog signal for a trajectory.  It is a static
        method so the background thread can do this work too and the main
        loop only has to swap the references in, which keeps the frame the
        tail lands on from stalling.
        """
        if source == "photogate":
            pulses = res["gate"]
            return dict(pulses=pulses, v_hi=5.0, feature=1.3e-4,
                        sig=make_pulse_signal(pulses, v_hi=5.0,
                                              t_rise=1.3e-4, noise=0.02))
        pulses = res["segments"] or res["contact"]
        return dict(pulses=pulses, v_hi=4.0,
                    feature=(min([b - a for a, b in pulses])
                             if pulses else None),
                    sig=make_pulse_signal(pulses, v_hi=4.0, t_rise=2.0e-6,
                                          noise=0.012, ring_f=res["f_vib"],
                                          ring_a=0.045))

    def adopt(self, res, built):
        """Take a trajectory whose signal was derived elsewhere."""
        self.res = res
        self.pulses = built["pulses"]
        self.sig = built["sig"]
        self.feature = built["feature"]
        self.v_hi = built["v_hi"]

    def _build(self, res):
        """(Re)derive the pulse train and the analog signal from a run."""
        self.res = res
        if self.source == "photogate":
            pulses = res["gate"]
            sig = make_pulse_signal(pulses, v_hi=5.0, t_rise=1.3e-4,
                                    noise=0.02)
            feature, self.v_hi = 1.3e-4, 5.0
        else:
            pulses = res["segments"] or res["contact"]
            sig = make_pulse_signal(pulses, v_hi=4.0, t_rise=2.0e-6,
                                    noise=0.012, ring_f=res["f_vib"],
                                    ring_a=0.045)
            feature = min([b - a for a, b in pulses]) if pulses else None
            self.v_hi = 4.0
        self.pulses, self.sig, self.feature = pulses, sig, feature

    def spoil(self, fault):
        """
        With no ground the probe is a floating antenna: 50 Hz mains and its
        harmonics ride on the pulses, the baseline wanders, and the whole
        thing is many volts peak to peak.
        """
        if fault != "float":
            return
        base, rg = self.sig, np.random.default_rng(11)
        ph = rg.random() * 2 * math.pi
        drift_f = 0.17 + 0.2 * rg.random()

        def spoiled(t):
            t = np.asarray(t, dtype=float)
            v = base(t)
            hum = (3.1 * np.sin(2 * math.pi * 50.0 * t + ph)
                   + 0.9 * np.sin(2 * math.pi * 150.0 * t + 2 * ph)
                   + 0.4 * np.sin(2 * math.pi * 250.0 * t))
            drift = 1.6 * np.sin(2 * math.pi * drift_f * t + ph)
            grass = 0.25 * (np.sin(t * 9.1e5) + np.sin(t * 1.37e6 + 1.0))
            return 0.55 * v + hum + drift + grass
        self.sig = spoiled
        self.analog = (lambda t: self.sig(np.asarray(t) + self.t0_trig))
        self.feature = None

    def retrigger(self, t_div, v_div, mem):
        """
        Continuous acquisition: arm again on the first pulse that starts
        after the window just captured, exactly as the instrument does
        between sweeps in Run.  Returns False when there is nothing left
        to trigger on.
        """
        end = self.t0_trig + self.rec_t0 + self.rec_n / self.rec_fs
        nxt = [a for a, _ in self.pulses if a > end]
        if not nxt:
            return False
        self.t0_trig = nxt[0]
        self.acquire(t_div, v_div, mem, build=build)
        return True

    # ---- the acquisition chain -----------------------------------
    def acquire(self, t_div, v_div, mem, build=True):
        span = 14 * t_div
        fs = snap_fs(mem / span)
        n = int(min(mem, max(span * fs, 8)))
        t0 = -0.05 * span
        full = 8 * v_div
        lsb = full / 256.0                     # 8 bit over 8 divisions
        self.rec_t0, self.rec_fs = t0, fs
        self.rec_tdiv, self.rec_n = t_div, n
        if not build:
            # Roll draws from the pulse train, so the record - up to 14 M
            # samples - is never built and the release is instant
            self.rec = None
            return
        rec = np.empty(n, dtype=np.float32)
        for k0 in range(0, n, 400_000):
            k1 = min(k0 + 400_000, n)
            t = t0 + np.arange(k0, k1) / fs
            rec[k0:k1] = np.clip(np.round(self.analog(t) / lsb) * lsb,
                                 -full / 2, full / 2)
        self.rec = rec



# ══════════════════════════════════════════════════════════════════
class CoilPanel(tk.Canvas):
    """
    The COIL / LASER corner of the electric junction box, drawn from the
    apparatus photograph: red indicator, silver toggle base with a red bat
    lever, and the ON / OFF legend on the cyan face.

    This is the release control of the real experiment.  G0-7 says it in so
    many words: "release the ball from the holder switching off the control
    box".  With the coil energised the holder grips the ball, so you can
    put the stand where you like; the moment you flick the lever down the
    field collapses and the pendulum starts.

    The same widget appears on the bench page and inside the box on the
    cabling page, and both always show the same lever, because there is
    only one switch.
    """

    W, H = 260, 118
    FACE, NAVY = "#4fa6dc", "#16324f"

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg=self.FACE,
                         highlightthickness=1, highlightbackground="#2e3134",
                         **kw)
        self.app = app
        self.bind("<Button-1>", self._click)
        self.redraw()

    def _click(self, _ev=None):
        self.app.set_coil(not self.app.wiring.coil_on)

    def redraw(self):
        self.delete("all")
        on = self.app.wiring.coil_on
        lit = on and self.app.wiring.linked("adaptor", "box_dc")
        # indicator
        self.create_oval(18, 14, 40, 36,
                         fill="#ff3020" if lit else "#5a1a18",
                         outline="#7a1218", width=1)
        if lit:                                   # a little glow
            self.create_oval(12, 8, 46, 42, outline="#ff8070", width=1)
            self.create_oval(8, 4, 50, 46, outline="#ffb0a0", width=1)
        self.create_text(52, 25, text="\u25c4 COIL / LASER", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 9, "bold"))
        # silver base and the red bat lever
        self.create_oval(46, 58, 94, 88, fill="#c8ccd0", outline="#8b9096",
                         width=2)
        self.create_oval(56, 64, 84, 82, fill="#9aa0a6", outline="#7d838a")
        tipx, tipy = (78, 46) if on else (62, 100)
        self.create_line(70, 73, tipx, tipy, fill="#c42030", width=11,
                         capstyle="round")
        self.create_oval(tipx - 7, tipy - 7, tipx + 7, tipy + 7,
                         fill="#e04050", outline="#8a1620")
        self.create_text(70, 106, text="ON / OFF", fill=self.NAVY,
                         font=("TkDefaultFont", 8, "bold"))
        self.create_text(120, 62, anchor="w",
                         text="coil energised" if lit else
                              ("switch is ON but the 12 V\nadaptor is not "
                               "plugged in" if on else "coil OFF"),
                         fill="#0d2338" if lit else "#7a2020",
                         font=("TkDefaultFont", 8, "bold"))
        self.create_text(120, 92, anchor="w",
                         text="flick the lever DOWN to release the ball"
                         if lit else "flick it UP to grip the ball",
                         fill=self.NAVY, font=("TkDefaultFont", 7))


class WiringPage(tk.Canvas):
    """
    The real hardware of the apparatus photograph, in plan view.

      * the electric junction box (item 6) is a cyan anodised box with
        black end caps: red COIL/LASER indicator, red ON/OFF toggle, a
        blue and silver CURRENT ADJUST pot, a green OSCILLOSCOPE label
        beside three silver banana posts on its right wall, a barrel jack
        for the photogate and for DC 12 V on the left wall, and the red
        BALL WIRES terminal at the bottom.
      * the photogate (item 10), the electromagnetic holder (item 11) and
        the 220 V / 12 V adaptor (item 7) sit on the left.
      * the oscilloscope carries the yellow CH1 and magenta CH2 BNCs and
        the black ground clip.

    Click a terminal, then click the one it goes to.  Click a lead to pull
    it out, right-click to cancel.  One lead per terminal, so plugging a
    second lead into a socket pushes the first one out.
    """

    W, H = 1010, 588
    R = 9
    FACE, BODY, EDGE = "#4fa6dc", "#2e3134", "#1b1d1f"
    GREEN, NAVY, RED = "#7fdb98", "#16324f", "#c81e28"

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#41454a",
                         highlightthickness=1, highlightbackground="#22252a",
                         **kw)
        self.app = app
        self.links = set()
        self.coil_on = True
        self.held = None
        self.mouse = (0, 0)
        self.T = {}

        def t(name, x, y, col, lab, side="e", fg="#e6e8ea"):
            self.T[name] = dict(x=x, y=y, col=col, lab=lab, side=side, fg=fg)

        # ---- units on the left -----------------------------------------
        t("photogate", 250, 330, "#2b2e32", "", "w")
        t("magnet", 250, 178, "#7a3fa8", "", "w")
        t("adaptor", 250, 400, "#2b6fa8", "", "w")
        # ---- junction box, left wall (barrel jacks) ---------------------
        t("box_gate", 372, 330, "#2b2e32", "", "e")
        t("box_mag", 372, 178, "#7a3fa8", "", "e")
        t("box_dc", 372, 400, "#2b6fa8", "", "e")
        # ---- junction box, right wall (silver banana posts) ------------
        t("box_ch", 566, 256, "#d8a000", "", "w")
        t("box_gnd", 566, 290, "#404040", "", "w")
        t("box_ball", 424, 424, "#c04020", "", "e")
        # ---- oscilloscope and the balls --------------------------------
        t("ch1", 748, 306, "#e8c020", "", "e", "#3b3830")
        t("ch2", 806, 306, "#e060b0", "", "e", "#3b3830")
        t("gnd", 864, 306, "#404040", "", "e", "#3b3830")
        t("ball1", 858, 412, "#c04020", "", "e")
        t("ball2", 858, 456, "#c04020", "", "e")

        # a lead can be pushed into any two terminals, exactly as on the
        # bench.  Nothing checks you: the circuit either works or it does
        # not, and state() below is what decides that.
        self.MULTI = {"box_ball"}
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._move)
        self.bind("<Button-3>", lambda e: self._cancel())
        self.redraw()

    # ------------------------------------------------------------------
    def _at(self, x, y):
        for k, d in self.T.items():
            if math.hypot(x - d["x"], y - d["y"]) <= self.R + 7:
                return k
        return None

    @staticmethod
    def _point(a, b, f):
        return (a["x"] + (b["x"] - a["x"]) * f,
                a["y"] + (b["y"] - a["y"]) * f
                + 24 * math.sin(math.pi * f))

    def _cable_at(self, x, y):
        for a, b in list(self.links):
            for f in np.linspace(0, 1, 44):
                px, py = self._point(self.T[a], self.T[b], f)
                if math.hypot(x - px, y - py) < 7:
                    return (a, b)
        return None

    def _cancel(self):
        self.held = None
        self.redraw()

    def _click(self, ev):
        if 388 <= ev.x <= 436 and 146 <= ev.y <= 220:          # ON / OFF
            self.app.set_coil(not self.coil_on)
            return
        k = self._at(ev.x, ev.y)
        if k is not None:
            if self.held is None or self.held == k:
                self.held = None if self.held == k else k
            elif self._can_join(self.held, k):
                self._plug(self.held, k)
                self.held = None
                self._changed()
                return
            else:
                self.held = k
            self.redraw()
            return
        c = self._cable_at(ev.x, ev.y)
        if c is not None:
            self.links.discard(c)
            self.held = None
            self._changed()
            return
        self._cancel()

    def _can_join(self, a, b):
        """Any two different terminals; a lead cannot go back on itself."""
        return a != b and tuple(sorted((a, b))) not in self.links

    def _plug(self, a, b):
        for end in (a, b):
            if end in self.MULTI:
                continue
            for lk in [l for l in self.links if end in l]:
                self.links.discard(lk)
        self.links.add(tuple(sorted((a, b))))

    def _move(self, ev):
        self.mouse = (ev.x, ev.y)
        if self.held is not None:
            self.redraw()

    def linked(self, a, b):
        return tuple(sorted((a, b))) in self.links

    def fault(self):
        """
        What is wrong with the connection, in the order that decides what
        the screen shows.  A real scope does not go blank when you get it
        wrong: it shows something, and the something is horrible.
        """
        st = self.state()
        if st["source"] is None or st["channel"] is None:
            return "open"                    # nothing feeding the input
        if st["channel"] == "ch2":
            return "wrongch"                 # signal on CH2, looking at CH1
        if not st["ground"]:
            return "float"                   # no return path: mains pickup
        return None

    def state(self):
        gate = self.linked("photogate", "box_gate")
        balls = (self.linked("box_ball", "ball1")
                 and self.linked("box_ball", "ball2"))
        power = self.linked("adaptor", "box_dc")
        coil = power and self.coil_on and self.linked("magnet", "box_mag")
        gnd = self.linked("box_gnd", "gnd")
        ch = ("ch1" if self.linked("box_ch", "ch1")
              else ("ch2" if self.linked("box_ch", "ch2") else None))
        src = "photogate" if gate else ("contact" if balls else None)
        return dict(source=src, channel=ch, ground=gnd, coil=coil,
                    powered=power,
                    live=(src is not None and ch == "ch1" and gnd))

    def _changed(self):
        self.redraw()
        self.app.wiring_changed()

    # ------------------------------------------------------------------
    def _post(self, x, y, col):
        """A silver banana post on the black side wall."""
        self.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#b9bec4",
                         outline="#7d838a", width=1)
        self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=col, outline="")

    def redraw(self):
        self.delete("all")

        # ---- the electromagnetic holder (11) is the TOP socket, in
        #      line with the COIL / LASER legend on the box -------------
        # the same assembly as on the bench page: a rail clamp with a
        # knurled screw, a long chrome rod, a cross-boss with three
        # knurled screws, and the short black magnet clamped into it
        self.create_rectangle(116, 220, 156, 234, fill="#c8ccd1",
                              outline="#8b9096")
        self.create_oval(152, 222, 164, 234, fill="#e6e8ea",
                         outline="#8b9096")
        self.create_line(136, 220, 136, 140, fill="#b9bec4", width=4)
        self.create_line(134, 220, 134, 140, fill="#f2f4f6", width=1)
        self.create_rectangle(118, 166, 158, 190, fill="#d3d7dc",
                              outline="#8b9096")
        for dx, dy in ((-14, -2), (0, 3), (14, -2)):
            self.create_oval(132 + dx, 174 + dy, 142 + dx, 184 + dy,
                             fill="#eceef0", outline="#8b9096")
        self.create_line(158, 178, 196, 178, fill="#26292d", width=9)
        self.create_line(196, 178, 200, 178, fill="#5a6068", width=9)
        self.create_line(140, 190, 146, 210, 140, 220, fill="#26292d",
                         width=1, smooth=True)
        self.create_text(136, 248, text="electromagnetic holder  11",
                         fill="#c9ccd1", font=("TkDefaultFont", 8))

        # ---- the photogate (10) is the MIDDLE socket -----------------
        self.create_rectangle(96, 350, 176, 362, fill="#d3d6da",
                              outline="#8b9096")
        for dx in (0, 56):
            self.create_rectangle(104 + dx, 300, 120 + dx, 352,
                                  fill="#f2f2ee", outline="#9aa0a6")
        self.create_rectangle(120, 324, 126, 336, fill="#2b2e32", outline="")
        self.create_line(120, 330, 160, 330, fill="#e03030", dash=(3, 3))
        self.create_line(176, 330, 214, 330, fill="#26292d", width=2)
        self.create_text(136, 376, text="photogate  10", fill="#c9ccd1",
                         font=("TkDefaultFont", 8))

        # ---------------- the 220 V / 12 V adaptor (item 7) ----------
        self.create_rectangle(96, 390, 180, 434, fill="#3b3f44",
                              outline="#1b1d1f", width=2)
        self.create_rectangle(104, 398, 148, 410, fill="#d8dade", outline="")
        self.create_line(180, 400, 214, 400, fill="#26292d", width=2)
        self.create_text(138, 450, text="adaptor 220 V / 12 V   7",
                         fill="#c9ccd1", font=("TkDefaultFont", 8))

        # ---------------- the junction box (item 6) ------------------
        self.create_rectangle(360, 78, 580, 470, fill=self.BODY,
                              outline=self.EDGE, width=2)          # body
        self.create_rectangle(376, 92, 564, 456, fill=self.FACE,
                              outline="#3d8ec0", width=1)          # face
        lit = self.coil_on and self.linked("adaptor", "box_dc")
        self.create_oval(462, 100, 478, 116,
                         fill="#ff3020" if lit else "#5a1a18",
                         outline="#7a1218", width=1)               # LED
        if lit:
            self.create_oval(457, 95, 483, 121, outline="#ff8070")
            self.create_oval(453, 91, 487, 125, outline="#ffb0a0")
        self.create_text(384, 134, text="\u25c4 COIL/LASER", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 8, "bold"))
        self.create_oval(394, 164, 430, 192, fill="#c8ccd0",
                         outline="#8b9096", width=2)               # bat base
        self.create_oval(402, 170, 422, 186, fill="#9aa0a6",
                         outline="#7d838a")
        tx, ty = (426, 152) if self.coil_on else (400, 214)
        self.create_line(412, 178, tx, ty, fill="#c42030", width=9,
                         capstyle="round")
        self.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill="#e04050",
                         outline="#8a1620")
        self.create_text(412, 210, text="ON / OFF", fill=self.NAVY,
                         font=("TkDefaultFont", 7, "bold"))
        self.create_text(512, 150, text="CURRENT", fill=self.NAVY,
                         font=("TkDefaultFont", 8, "bold"))
        self.create_oval(492, 164, 532, 204, fill="#2f63a8",
                         outline="#1d4272", width=2)               # pot body
        self.create_oval(498, 162, 526, 186, fill="#c8ccd0",
                         outline="#9aa0a6")                        # silver top
        self.create_line(512, 174, 512, 164, fill="#5a6068", width=2)
        self.create_text(512, 216, text="ADJUST", fill=self.NAVY,
                         font=("TkDefaultFont", 7, "bold"))
        self.create_text(400, 272, text="6", fill="#ffffff",
                         font=("TkDefaultFont", 22, "bold"))
        self.create_rectangle(448, 240, 560, 302, fill=self.GREEN,
                              outline="#4fae6a")                   # green label
        self.create_text(552, 256, text="CH1/2  \u25ba", anchor="e",
                         fill=self.NAVY, font=("TkDefaultFont", 8, "bold"))
        self.create_text(504, 272, text="OSCILLOSCOPE", fill=self.NAVY,
                         font=("TkDefaultFont", 7, "bold"))
        self.create_text(552, 290, text="GND  \u25ba", anchor="e",
                         fill=self.NAVY, font=("TkDefaultFont", 8, "bold"))
        self.create_text(384, 330, text="\u25c4 PHOTOGATE", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 7, "bold"))
        self.create_text(384, 400, text="\u25c4 DC 12V", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 7, "bold"))
        self.create_text(460, 446, text="BALL WIRES", anchor="c",
                         fill=self.NAVY, font=("TkDefaultFont", 7, "bold"))
        self.create_polygon(452, 432, 464, 432, 458, 412, fill="#ffffff",
                            outline="#8fbede")
        self.create_oval(412, 412, 436, 436, fill="#b9bec4",
                         outline="#7d838a")
        self.create_oval(418, 418, 430, 430, fill="#c42030", outline="")
        self.create_polygon(478, 412, 490, 412, 484, 432, fill="#ffffff",
                            outline="#8fbede")
        self._post(566, 256, "#d8a000")
        self._post(566, 290, "#404040")

        # ---------------- the oscilloscope ---------------------------
        self.create_rectangle(700, 120, 920, 344, fill="#5a626c",
                              outline="#3b4149", width=2)
        self.create_rectangle(708, 128, 912, 336, fill="#efeade",
                              outline="#cdc7ba")
        self.create_text(716, 142, text="SIGLENT", anchor="w",
                         fill="#1f5fa8", font=("TkDefaultFont", 8, "bold"))
        self.create_rectangle(716, 154, 904, 272, fill="#101418",
                              outline="#0e1013")
        for gx in range(1, 7):
            self.create_line(716 + gx * 188 / 7, 154,
                             716 + gx * 188 / 7, 272, fill="#17331a")
        for gy in range(1, 4):
            self.create_line(716, 154 + gy * 118 / 4,
                             904, 154 + gy * 118 / 4, fill="#17331a")
        self.create_text(810, 288, text="SDS 1202X-E", fill="#7d7466",
                         font=("TkDefaultFont", 7))
        for tx, lab in ((748, "CH1"), (806, "CH2"), (864, "GND")):
            self.create_text(tx, 328, text=lab, fill="#3b3830",
                             font=("TkDefaultFont", 7))

        # ---------------- the two balls -----------------------------
        for y, lab in ((412, "ball 1"), (456, "ball 2")):
            self.create_oval(884, y - 13, 910, y + 13, fill="#b9bdc4",
                             outline="#585d63", width=2)
            self.create_text(926, y, text=lab, anchor="w", fill="#c9ccd1",
                             font=("TkDefaultFont", 8))

        for a, b in sorted(self.links):
            pts = []
            for f in np.linspace(0, 1, 26):
                pts += list(self._point(self.T[a], self.T[b], f))
            self.create_line(*pts, fill=self.T[a]["col"], width=3,
                             smooth=True, capstyle="round")
        if self.held is not None:
            d = self.T[self.held]
            self.create_line(d["x"], d["y"], self.mouse[0], self.mouse[1],
                             fill=d["col"], width=3, dash=(6, 4))

        for k, d in self.T.items():
            used = any(k in p for p in self.links)
            rr = self.R + (3 if k == self.held else 0)
            self.create_oval(d["x"] - rr, d["y"] - rr, d["x"] + rr,
                             d["y"] + rr,
                             fill=d["col"] if used else "#f4f4f0",
                             outline="#e03030" if k == self.held else d["col"],
                             width=3 if k == self.held else 2)
            if d["lab"]:
                self.create_text(d["x"] + (16 if d["side"] == "e" else -16),
                                 d["y"], text=d["lab"],
                                 anchor="w" if d["side"] == "e" else "e",
                                 fill=d["fg"], font=("TkDefaultFont", 8))

        self.create_text(20, 22, anchor="w", fill="#aeb4ba",
                         font=("TkDefaultFont", 8),
                         text="click a terminal, then click the one it goes "
                              "to.  Click a lead to pull it out, right-click "
                              "to cancel.  One lead per terminal.")


class App:
    NX, NY = 14, 8

    def __init__(self, root):
        self.root = root
        root.title("APhO 2023 Q1 - Hertzian contact stress - "
                   "pendulum bench and oscilloscope")
        self.rng = random.Random()
        self.bench = Bench(self.rng)
        self.run = None
        self.play = False
        self.play_t = 0.0
        self.delay = 0.0                       # M Pos, s
        self.t_div = 0.5
        self.v_div = 2.0
        self.mem_i = 2
        self.fine = False
        self.armed = True
        self.cont = True
        self._played = None
        self._pending = {}
        self.ball_held = False
        self._drag_mag = False
        self.sel = None
        self.mag_x = 0.0
        self.mag_z = -L_PEND
        self.frozen = None        # the held screen after Stop
        self.zoom = False         # SEC/DIV push, manual p.32
        self.trig_mode = "Auto"   # Auto / Normal / Single
        self.roll = True          # slow sweeps run on, as on the
                                  # instrument's Roll setting
        self.npix = 1200          # trace resolution, adaptive
        self.render_ms = 8.0      # smoothed cost of one frame
        self.fps = 0.0
        self._frame_i = 0
        self.v_off = 0.0
        self.v_div2 = 1.0
        self.trig_lvl = 1.0
        self._last = time.perf_counter()

        self.nb = ttk.Notebook(root)
        self.nb.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.page_bench = ttk.Frame(self.nb)
        self.page_wire = ttk.Frame(self.nb)
        self.nb.add(self.page_bench, text="  Bench and oscilloscope  ")
        self.nb.add(self.page_wire, text="  Cabling  ")
        self.page_bench.columnconfigure(1, weight=1)
        self.page_bench.rowconfigure(0, weight=1)
        self.wiring = WiringPage(self.page_wire, self)
        self.wiring.pack(padx=8, pady=8)
        self._build_widgets()
        self._build_plot()
        self._sync()
        self._tick()

    # ───────────────────────── widgets ─────────────────────────
    def _build_widgets(self):
        left = ttk.Frame(self.page_bench, padding=8)
        left.grid(row=0, column=0, sticky="ns")
        r = 0

        ttk.Label(left, text="Balls on the hangers",
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        self.cb = []
        for i in (0, 1):
            ttk.Label(left, text="pendulum %d" % (i + 1)).grid(
                row=r, column=0, sticky="w")
            r += 1
            c = ttk.Combobox(left, state="readonly", width=34,
                             values=[b[0] for b in BALLS])
            c.current(0)
            c.grid(row=r, column=0, sticky="w", pady=(0, 4))
            c.bind("<<ComboboxSelected>>", lambda e: self._on_geo())
            self.cb.append(c)
            r += 1
        self.var_two = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="pendulum 2 in use   (off = Part A / B)",
                        variable=self.var_two,
                        command=self._on_geo).grid(row=r, column=0, sticky="w")
        r += 1

        ttk.Separator(left, orient="horizontal").grid(
            row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(left, text="Ball positions",
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        self.lbl_geo = ttk.Label(left, text="", font=("Consolas", 9))
        self.lbl_geo.grid(row=r, column=0, sticky="w", pady=(2, 4))
        r += 1
        for text, var, lo, hi, init in (
                ("hanger separation  d_x - 2R  (mm)", "gap", -2.0, 6.0, 0.0),
                ("wire length difference  d_z  (mm)", "dz", -3.0, 3.0, 0.0),
                # the gate belongs at the equilibrium position: that is
                # where dt = d / v_max and where the ball crosses it once
                # every half period
                ("photogate position  (mm from ball 1)", "gate",
                 -120.0, 120.0, 0.0),
                # G0-4 step 7 : "attaching the ball onto electro-magnet".
                # You pull the ball aside to the angle you want and it
                # sticks; the stand is adjusted to suit, not the other way
                # round.  Drag the ball on the angle screen or use this.
                ("pull the ball aside   [or drag it on the angle screen]",
                 "phi",
                 3.0, 85.0, 70.0)):
            ttk.Label(left, text=text).grid(row=r, column=0, sticky="w")
            r += 1
            v = tk.DoubleVar(value=init)
            setattr(self, "var_" + var, v)
            ttk.Scale(left, from_=lo, to=hi, variable=v, orient="horizontal",
                      length=250,
                      command=lambda *_a, _k=var: self._on_geo(_k)
                      ).grid(row=r, column=0, sticky="ew")
            r += 1

        ttk.Separator(left, orient="horizontal").grid(
            row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Button(left, text="open the cabling page",
                   command=lambda: self.nb.select(1)).grid(row=r, column=0,
                                                           sticky="ew")
        r += 1
        self.coil_panel = CoilPanel(left, self)
        self.coil_panel.grid(row=r, column=0, sticky="w", pady=(8, 2))
        r += 1
        ttk.Button(left, text="\u25a0  stop the pendulum",
                   command=self.stop).grid(row=r, column=0, sticky="ew",
                                           pady=(2, 2))
        r += 1
        ttk.Separator(left, orient="horizontal").grid(
            row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Separator(left, orient="horizontal").grid(
            row=r, column=0, sticky="ew", pady=6)
        r += 1
        self.lbl_sel = ttk.Label(left, text="wheel acts on:  -  "
                                       "(click a dial first)",
                                 foreground="#a03000")
        self.lbl_sel.grid(row=r, column=0, sticky="w", pady=(0, 2))
        r += 1
        self.lbl_mpos = ttk.Label(left, text="M Pos = ----",
                                  font=("Consolas", 13, "bold"))
        self.lbl_mpos.grid(row=r, column=0, sticky="w")
        r += 1
        self.lbl_acq = ttk.Label(left, text="", font=("Consolas", 9),
                                 justify="left")
        self.lbl_acq.grid(row=r, column=0, sticky="w", pady=(2, 2))
        r += 1
        self.lbl_warn = ttk.Label(left, text="", wraplength=260,
                                  foreground="#b00000", justify="left")
        self.lbl_warn.grid(row=r, column=0, sticky="w")
        r += 1
        self.lbl_cursor = ttk.Label(left, text="cursor :  -")
        self.lbl_cursor.grid(row=r, column=0, sticky="w", pady=(4, 0))
        r += 1
        ttk.Button(left, text="save screen PNG", command=self.save_png).grid(
            row=r, column=0, sticky="ew", pady=(6, 2))
        r += 1
        ttk.Label(left, wraplength=260, foreground="#555", justify="left",
                  text=("Every oscilloscope setting is on the instrument "
                        "itself: click a dial to select it, then turn "
                        "the mouse wheel.  Push the centre of a knob "
                        "for the fine step.  Acquire cycles the memory "
                        "depth.  Single takes one shot; Run/Stop latches, so "
                        "in Run the scope re-acquires on every "
                        "release until you press it again.  Switching the "
                        "scope on while the pendulum is already "
                        "swinging is fine: it waits for the next "
                        "pulse.\n"
                        "Pull the ball aside to the angle you want - drag "
                        "it on the angle screen or use the phi0 slider - "
                        "and the electromagnet is brought up to it.  With "
                        "the coil live the ball sticks; flick the COIL "
                        "lever down to release it.\n\n"
                        "Graticule 14 x 8, minor grid 0.1 div.  There is no "
                        "zoom: put the half amplitude of the edge on the "
                        "centre line and read M Pos to 7 figures.  Never use "
                        "pulse 1.")).grid(row=r, column=0, sticky="w",
                                          pady=(6, 0))

    # --------------------------- figure ---------------------------
    #  instrument geometry, in its own data units (SDS 1202X-E, drawn
    #  from item 8 of the apparatus photograph)
    #  case 1569 x 803 px in the reference photograph -> aspect 1.954
    IW, IH = 980.0, 501.5
    SX0, SY0, SW, SH = 41.8, 140.5, 531.0, 319.0   # filled in by build
    #  from the 539 x 325 px screen capture in the General Instructions
    BAR_T, BAR_B, SIDE = 15 / 325.0, 43 / 325.0, 60 / 539.0
    C_BAR, C_TRACE, C_STOP = "#2f3030", "#d8d417", "#c40000"

    def _build_plot(self):
        self.fig = Figure(figsize=(9.6, 9.4), dpi=100)
        self.ax_a = self.fig.add_axes([0.04, 0.605, 0.92, 0.385])
        self.ax_a.set_aspect("equal", adjustable="box")
        self.ax_a.axis("off")

        # the screen is drawn INSIDE the instrument axes, so the two can
        # never drift apart and the whole panel keeps its 340 x 165 mm
        # shape whatever the window is resized to
        self.ax_i = self.fig.add_axes([0.035, 0.02, 0.93, 0.55])
        self.ax_i.set_xlim(0, self.IW)
        self.ax_i.set_ylim(0, self.IH)
        self.ax_i.set_aspect("equal", adjustable="box")
        self.ax_i.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.page_bench)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.background = None
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_drag)
        self.canvas.mpl_connect("button_release_event", self._on_up)
        self.canvas.mpl_connect("draw_event", self._on_draw)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        # a direct Tk binding as well: matplotlib's wheel event is not
        # delivered on every platform
        wdg = self.canvas.get_tk_widget()
        wdg.bind("<MouseWheel>", self._tk_wheel)
        wdg.bind("<Button-4>", lambda e: self._tk_wheel(e, +1))
        wdg.bind("<Button-5>", lambda e: self._tk_wheel(e, -1))
        self.build_instrument()
        ax = self.ax_i
        (self.trace,) = ax.plot([], [], "-", color=self.C_TRACE, lw=1.2,
                                zorder=12)
        (self.dots,) = ax.plot([], [], "o", ms=3, color="#ff6060",
                               linestyle="none", zorder=12)
        (self.centre,) = ax.plot([], [], "-", color="#c8c8c8", lw=0.9,
                                 ls=(0, (4, 3)), zorder=11)
        self.txt_hi = ax.text(0, 0, "", color="#40ff40", fontsize=4.6,
                              va="center", family="monospace",
                              zorder=13)
        self.txt_sa = ax.text(0, 0, "", color="#e6e6e6", fontsize=4.4,
                              ha="left", va="top",
                              family="monospace", zorder=13)
        self.txt_lo = ax.text(0, 0, "", color=self.C_TRACE, fontsize=4.6,
                              va="center", family="monospace",
                              zorder=13)
        (self.trig,) = ax.plot([], [], marker="v", ms=6, color="#40c0ff",
                               linestyle="none", zorder=13)
        (self.trig_lv,) = ax.plot([], [], marker="<", ms=6,
                                  color=self.C_TRACE, linestyle="none",
                                  zorder=13)


    def _tk_wheel(self, ev, step=None):
        if step is None:
            step = 1 if getattr(ev, "delta", 0) > 0 else -1
        key = None
        h = int(self.canvas.get_tk_widget().winfo_height())
        x, y = self.ax_i.transData.inverted().transform((ev.x, h - ev.y))
        for k, kx, ky, size, kind in self.hits:
            if kind == "knob" and math.hypot(x - kx, y - ky) <= size:
                key = k
                break
        if key and key != self.sel:
            self._select(key)
        key = key or self.sel
        if key:
            self._turn(key, step)
        return "break"

    def _collect_animated(self):
        """Only these move; everything else lives in the cached background."""
        self.anim = ([self.trace, self.dots, self.txt_hi, self.txt_sa,
                      self.txt_lo, self.trig, self.trig_lv, self.centre,
                      self.sel_ring]
                     + list(self.art_wire) + list(self.art_ball)
                     + [self.art_mline, self.art_mball, self.art_mag,
                        self.art_txt, self.art_cfg,
                        self.art_rod, self.art_rodhi,
                        self.art_foot, self.art_footscrew,
                        self.art_clamp, self.art_cable,
                        self.art_magcap,
                        self.art_grip]
                     + self.art_screws)
        for a in self.anim:
            a.set_animated(True)
        self.background = None

    def _on_draw(self, _ev=None):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
        for a in getattr(self, "anim", []):
            a.axes.draw_artist(a)

    def _blit(self, only=None):
        """only='scope' or 'bench' repaints just that half of the figure."""
        if not hasattr(self, "anim") or self.background is None:
            self.canvas.draw()
            return
        self.canvas.restore_region(self.background)
        for a in self.anim:
            if only == "scope" and a.axes is self.ax_a:
                continue
            if only == "bench" and a.axes is self.ax_i:
                continue
            a.axes.draw_artist(a)
        if only != "bench":
            self.canvas.blit(self.ax_i.bbox)
        if only != "scope":
            self.canvas.blit(self.ax_a.bbox)

    # --------------------------- the instrument ---------------------
    # ------------------------------------------------------------------
    #  Everything below is measured off the straight-on photograph of the
    #  SDS 1202X-E front panel.  The case in that image is 1569 x 803 px,
    #  so every coordinate is stored as a fraction of the case and scaled
    #  to IW x IH here.  Screen sub-rectangles come from the 539 x 325 px
    #  screen capture in the General Instructions.
    # ------------------------------------------------------------------
    def build_instrument(self):
        ax = self.ax_i
        ax.clear()
        ax.set_xlim(0, self.IW)
        ax.set_ylim(0, self.IH)
        ax.set_autoscale_on(False)
        ax.axis("off")
        W, H = self.IW, self.IH

        def X(f):
            return f * W

        def Y(f):
            return f * H

        # ---- case ----------------------------------------------------
        ax.add_patch(FancyBboxPatch((X(0.004), Y(0.030)), X(0.992), Y(0.955),
                                    boxstyle="round,pad=0,rounding_size="
                                             + str(0.012 * W),
                                    facecolor="#dcdcda", edgecolor="#b6b6b3",
                                    lw=1.2, zorder=0))
        for fx in (0.10, 0.78):                      # the two case feet
            ax.add_patch(Rectangle((X(fx), 0), X(0.11), Y(0.055),
                                   facecolor="#c2c2bf", edgecolor="#a8a8a5",
                                   lw=0.8, zorder=0))
        ax.add_patch(Rectangle((X(0.030), Y(0.930)), X(0.560), Y(0.055),
                               facecolor="#ececeb", edgecolor="none",
                               zorder=1))
        ax.text(X(0.075), Y(0.958), "SIGLENT", color="#1f4f9c",
                fontsize=11, fontweight="bold", va="center", zorder=3)
        ax.text(X(0.215), Y(0.966), "SDS 1202X-E", color="#55565a",
                fontsize=7.5, va="center", zorder=3)
        ax.text(X(0.215), Y(0.945), "Digital Storage Oscilloscope",
                color="#8a8b8f", fontsize=5, va="center", zorder=3)
        ax.text(X(0.375), Y(0.966), "SPO", color="#55565a", fontsize=8,
                fontweight="bold", va="center", zorder=3)
        ax.text(X(0.375), Y(0.945), "Super Phosphor Oscilloscope",
                color="#8a8b8f", fontsize=5, va="center", zorder=3)
        ax.text(X(0.500), Y(0.966), "200 MHz", color="#55565a", fontsize=6.5,
                va="center", zorder=3)
        ax.text(X(0.500), Y(0.945), "1 GSa/s", color="#55565a", fontsize=6.5,
                va="center", zorder=3)

        # ---- 1 LCD display -------------------------------------------
        self.SX0, self.SY0 = X(0.0427), Y(0.2802)
        self.SW, self.SH = X(0.5844 - 0.0427), Y(0.9010 - 0.2802)
        ax.add_patch(Rectangle((self.SX0 - X(0.009), self.SY0 - Y(0.016)),
                               self.SW + X(0.018), self.SH + Y(0.032),
                               facecolor="#26262a", edgecolor="#141417",
                               lw=1.0, zorder=2))
        self._draw_glass(ax)

        self.knobs, self.hits = {}, []
        self.sel = None

        def knob(key, fx, fy, fr, label="", ring=None):
            x, y, r = X(fx), Y(fy), fr * W
            if ring:
                ax.add_patch(Circle((x, y), r + 0.010 * W, facecolor="none",
                                    edgecolor=ring, lw=3.2, zorder=3))
            ax.add_patch(Circle((x + 0.0015 * W, y - 0.004 * H), r * 1.03,
                                facecolor="#b9b9b6", edgecolor="none",
                                zorder=3))
            ax.add_patch(Circle((x, y), r, facecolor="#d2d2cf",
                                edgecolor="#a9a9a6", lw=0.9, zorder=4))
            ax.add_patch(Circle((x, y + 0.003 * H), r * 0.72,
                                facecolor="#eeeeec", edgecolor="#c9c9c6",
                                lw=0.7, zorder=5))
            for k in range(18):
                aa = k * math.pi / 9.0
                ax.plot([x + r * 0.80 * math.cos(aa),
                         x + r * 0.96 * math.cos(aa)],
                        [y + r * 0.80 * math.sin(aa),
                         y + r * 0.96 * math.sin(aa)],
                        color="#c4c4c1", lw=0.6, zorder=5)
            m, = ax.plot([x, x], [y + r * 0.20, y + r * 0.62],
                         color="#8d8d8a", lw=2.2, zorder=6,
                         solid_capstyle="round")
            m._cx, m._cy, m._r, m._ang = x, y, r, 0.0
            if label:
                ax.text(x, y - r - 0.020 * H, label, ha="center",
                        va="center", fontsize=5, color="#55565a", zorder=4)
            self.knobs[key] = m
            self.hits.append((key, x, y, r + 0.006 * W, "knob"))

        def button(key, fx, fy, fw, fh, label, col="#e8e8e6",
                   fg="#3a3b3e", rad=0.004):
            x, y = X(fx) - X(fw) / 2, Y(fy) - Y(fh) / 2
            w_, h_ = X(fw), Y(fh)
            ax.add_patch(FancyBboxPatch((x + 0.0012 * W, y - 0.003 * H),
                                        w_, h_,
                                        boxstyle="round,pad=0,rounding_size="
                                                 + str(rad * W),
                                        facecolor="#b9b9b6", edgecolor="none",
                                        zorder=3))
            ax.add_patch(FancyBboxPatch((x, y), w_, h_,
                                        boxstyle="round,pad=0,rounding_size="
                                                 + str(rad * W),
                                        facecolor=col, edgecolor="#a9a9a6",
                                        lw=0.7, zorder=4))
            ax.text(x + w_ / 2, y + h_ / 2, label, ha="center", va="center",
                    fontsize=4.6, fontweight="bold", color=fg, zorder=5)
            self.hits.append((key, x, y, (w_, h_), "btn"))

        def group(fx0, fx1, fy0, fy1, title):
            ax.add_patch(FancyBboxPatch((X(fx0), Y(fy0)), X(fx1 - fx0),
                                        Y(fy1 - fy0),
                                        boxstyle="round,pad=0,rounding_size="
                                                 + str(0.006 * W),
                                        facecolor="none", edgecolor="#7ec8e8",
                                        lw=1.0, zorder=2))
            ax.text(X((fx0 + fx1) / 2), Y(fy1) + Y(0.018), title,
                    ha="center", va="center", fontsize=6.5,
                    fontweight="bold", color="#3a3b3e", zorder=3)

        # ---- 2 Universal knob ----------------------------------------
        button("univbtn", 0.6367, 0.9128, 0.024, 0.030, "", "#d2d2cf")
        knob("univ", 0.6431, 0.8170, 0.01848, "")
        ax.text(X(0.6431), Y(0.8170) + Y(0.052), "Intensity", ha="center",
                fontsize=4.6, color="#55565a", zorder=4)
        ax.text(X(0.6431), Y(0.8170) + Y(0.036), "Adjust", ha="center",
                fontsize=5.2, fontweight="bold", color="#3a3b3e", zorder=4)

        # ---- 3 common function menus ---------------------------------
        for k, (key, lab, col) in enumerate((
                ("cursors", "Cursors", "#e2f0c8"),
                ("acquire", "Acquire", "#e8e8e6"),
                ("save", "Save\nRecall", "#e8e8e6"),
                ("measure", "Measure", "#e8e8e6"),
                ("clear", "Clear\nSweeps", "#e8e8e6"),
                ("utility", "Utility", "#e8e8e6"),
                ("default", "Default", "#e2f0c8"),
                ("display", "Display\nPersist", "#e8e8e6"),
                ("print", "Print", "#cfe4f7"))):
            button(key, 0.7075 + (k % 3) * 0.0536, 0.9128 - (k // 3) * 0.0660,
                   0.046, 0.042, lab, col)
        button("history", 0.8711, 0.8929, 0.046, 0.042, "History")
        button("decode", 0.8711, 0.8032, 0.046, 0.042, "Decode")

        # ---- 4 Run/Stop, 5 Auto Setup --------------------------------
        button("run", 0.9414, 0.9041, 0.0400, 0.0620, "Run\nStop", "#cdeeb0")
        button("auto", 0.9446, 0.7995, 0.0570, 0.0620, "Auto\nSetup",
               "#2f9fe0", "#ffffff")

        # ---- 8 Vertical ----------------------------------------------
        group(0.6329, 0.7859, 0.3089, 0.7098, "Vertical")
        knob("vscale", 0.6437, 0.6339, 0.0255, "", ring="#f2c500")
        knob("vscale2", 0.7463, 0.6364, 0.0249, "", ring="#e86ab4")
        ax.text(X(0.6960), Y(0.5760), "Variable", ha="center", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        button("math", 0.6960, 0.5479, 0.038, 0.040, "Math")
        button("ch1", 0.6418, 0.4969, 0.038, 0.040, "1", "#f6e58a")
        button("ch2", 0.7476, 0.4969, 0.038, 0.040, "2", "#cdeeb0")
        button("ref", 0.6960, 0.4421, 0.038, 0.040, "Ref")
        knob("vpos", 0.6431, 0.3761, 0.0178, "", ring="#f2c500")
        knob("vpos2", 0.7476, 0.3798, 0.0191, "", ring="#e86ab4")
        ax.text(X(0.6960), Y(0.3798), "Position", ha="center", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        for fx in (0.6431, 0.7476):
            ax.text(X(fx), Y(0.3110), "Zero", ha="center", fontsize=4.2,
                    color="#55565a", zorder=4)

        # ---- 7 Horizontal --------------------------------------------
        group(0.7859, 0.8993, 0.3089, 0.7098, "Horizontal")
        knob("hscale", 0.8559, 0.6401, 0.0331, "")
        ax.text(X(0.8508), Y(0.5560), "Zoom", ha="center", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        button("hmenu", 0.8508, 0.4969, 0.038, 0.040, "Roll")
        knob("hpos", 0.8508, 0.3785, 0.0191, "")
        ax.text(X(0.8508), Y(0.4300), "Position", ha="center", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        ax.text(X(0.8508), Y(0.3110), "Zero", ha="center", fontsize=4.2,
                color="#55565a", zorder=4)

        # ---- 6 Trigger -----------------------------------------------
        group(0.8993, 0.9726, 0.3089, 0.7098, "Trigger")
        button("trigmenu", 0.9356, 0.6762, 0.046, 0.042, "Setup", "#2b2c30",
               "#ffffff")
        button("tauto", 0.9356, 0.5990, 0.046, 0.042, "Auto", "#e2f0c8")
        button("tnormal", 0.9356, 0.5268, 0.046, 0.042, "Normal")
        button("single", 0.9356, 0.4620, 0.046, 0.042, "Single")
        knob("trig", 0.9464, 0.3798, 0.0191, "")
        ax.text(X(0.9464), Y(0.4300), "Level", ha="center", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        ax.text(X(0.9464), Y(0.3110), "50%", ha="center", fontsize=4.2,
                color="#55565a", zorder=4)

        # ---- 10 analog inputs ----------------------------------------
        for fx, col, lab, num in ((0.6418, "#f2c500", "X", "1"),
                                  (0.7457, "#e86ab4", "Y", "2"),
                                  (0.8496, "#9a9a97", "", "Ext")):
            x, y, r = X(fx), Y(0.2341), 0.0191 * W
            ax.add_patch(Circle((x, y), r, facecolor="#c2c2bf",
                                edgecolor="#8d8d8a", lw=1.4, zorder=4))
            ax.add_patch(Circle((x, y), r * 0.62, facecolor="#4a4a48",
                                edgecolor="#6e6e6b", lw=0.8, zorder=5))
            ax.add_patch(Circle((x, y), r * 0.22, facecolor="#d8d8d5",
                                edgecolor="none", zorder=6))
            ax.text(x - r - 0.008 * W, y + r + 0.020 * H, lab, ha="center",
                    fontsize=5, color="#3a3b3e", zorder=4)
            ax.text(x + 0.012 * W, y + r + 0.020 * H, num, ha="center",
                    fontsize=6, fontweight="bold", color="#3a3b3e", zorder=4)
        ax.text(X(0.7457), Y(0.1660), "All inputs : 1 M\u03a9 / 16 pF   400 Vpk",
                ha="center", fontsize=4.4, color="#2f6fa8", zorder=4)
        ax.add_patch(FancyBboxPatch((X(0.6300), Y(0.1500)), X(0.2400),
                                    Y(0.1600),
                                    boxstyle="round,pad=0,rounding_size="
                                             + str(0.006 * W),
                                    facecolor="none", edgecolor="#7ec8e8",
                                    lw=1.0, zorder=2))

        # ---- 9 probe compensation ------------------------------------
        ax.add_patch(Rectangle((X(0.9280), Y(0.1900)), X(0.0180), Y(0.0900),
                               facecolor="#b9b9b6", edgecolor="#8d8d8a",
                               lw=0.7, zorder=4))
        ax.add_patch(Rectangle((X(0.9280), Y(0.2900)), X(0.0180), Y(0.0300),
                               facecolor="#b9b9b6", edgecolor="#8d8d8a",
                               lw=0.7, zorder=4))
        ax.text(X(0.9640), Y(0.2700), "\u2510\u2500 1 kHz", fontsize=4.6,
                color="#3a3b3e", zorder=4)
        ax.plot([X(0.9600), X(0.9700)], [Y(0.2100), Y(0.2100)],
                color="#3a3b3e", lw=1.0, zorder=4)
        ax.plot([X(0.9650), X(0.9650)], [Y(0.2100), Y(0.2260)],
                color="#3a3b3e", lw=1.0, zorder=4)

        # ---- 12 menu softkeys, 13 Menu on/off, 11 USB, 14 power ------
        ax.add_patch(FancyBboxPatch((X(0.049), Y(0.1710)), X(0.4390),
                                    Y(0.1070),
                                    boxstyle="round,pad=0,rounding_size="
                                             + str(0.006 * W),
                                    facecolor="none", edgecolor="#7ec8e8",
                                    lw=1.0, zorder=2))
        self.softkeys = []
        for i in range(6):
            fx = 0.1230 + i * 0.0688
            button("sk%d" % i, fx, 0.2192, 0.0465, 0.0386, "")
            self.softkeys.append(self.hits[-1])
        ax.add_patch(Circle((X(0.0567), Y(0.2279)), 0.0140 * W,
                            facecolor="#d2d2cf", edgecolor="#a9a9a6",
                            lw=0.9, zorder=4))
        r_ = 0.0140 * W
        self.hits.append(("menuonoff", X(0.0567) - r_, Y(0.2279) - r_,
                          (2 * r_, 2 * r_), "btn"))
        ax.text(X(0.0567), Y(0.2279) + Y(0.042), "Menu", ha="center",
                fontsize=4.6, color="#3a3b3e", zorder=5)
        ax.text(X(0.0567), Y(0.2279) - Y(0.042), "On/Off", ha="center",
                fontsize=4.6, color="#3a3b3e", zorder=5)
        ax.add_patch(FancyBboxPatch((X(0.5330), Y(0.2010)), X(0.0400),
                                    Y(0.0420),
                                    boxstyle="round,pad=0,rounding_size="
                                             + str(0.004 * W),
                                    facecolor="#3b3f44", edgecolor="#8d8d8a",
                                    lw=0.8, zorder=4))
        
        ax.add_patch(Circle((X(0.1103), Y(0.1270)), 0.0153 * W,
                            facecolor="#cdeeb0", edgecolor="#9ab98a",
                            lw=1.2, zorder=4))
        ax.add_patch(Circle((X(0.1103), Y(0.1270)), 0.0070 * W,
                            facecolor="none", edgecolor="#3a5a2a",
                            lw=1.2, zorder=5))
        ax.plot([X(0.1103), X(0.1103)],
                [Y(0.1270), Y(0.1270) + 0.011 * H],
                color="#3a5a2a", lw=1.4, zorder=6)

        self.sel_ring = Circle((0, 0), 1, facecolor="none",
                               edgecolor="#e03030", lw=2.0, zorder=8,
                               visible=False)
        ax.add_patch(self.sel_ring)
        ax.text(X(0.985), Y(0.055), "click a dial, then use the mouse wheel",
                ha="right", fontsize=5, color="#a9a9a6", zorder=4)

    # ------------------------------------------------------------------
    def _draw_glass(self, ax):
        """
        The screen itself, measured off the 539 x 325 px capture in the
        General Instructions: a 15 px status bar, a 43 px bottom bar, a
        60 px right sidebar and a 14 x 8 graticule of square 33.5 px cells
        on pure black, bars in #2f3030.
        """
        ax.add_patch(Rectangle((self.SX0, self.SY0), self.SW, self.SH,
                               facecolor="#000000", edgecolor="#3a3a3e",
                               lw=0.8, zorder=3))
        gx, gy, gw, gh = self._grat()
        ax.add_patch(Rectangle((self.SX0, self.SY0 + self.SH
                                * (1 - self.BAR_T)), self.SW,
                               self.SH * self.BAR_T, facecolor=self.C_BAR,
                               edgecolor="none", zorder=4))
        ax.add_patch(Rectangle((self.SX0 + gw, self.SY0), self.SW - gw,
                               self.SH * (1 - self.BAR_T),
                               facecolor=self.C_BAR, edgecolor="none",
                               zorder=4))
        major, minor = [], []
        for i in range(self.NX * 5 + 1):
            x = gx + i * gw / (self.NX * 5.0)
            (major if i % 5 == 0 else minor).append([(x, gy), (x, gy + gh)])
        for j in range(self.NY * 5 + 1):
            y = gy + j * gh / (self.NY * 5.0)
            (major if j % 5 == 0 else minor).append([(gx, y), (gx + gw, y)])
        ax.add_collection(LineCollection(minor, colors="#1e2320",
                                         linewidths=0.35,
                                         linestyle=(0, (1, 4)), zorder=4))
        ax.add_collection(LineCollection(major, colors="#39463a",
                                         linewidths=0.5,
                                         linestyle=(0, (1, 3)), zorder=4))
        bh = self.SH * self.BAR_T
        by = self.SY0 + self.SH - bh / 2
        ax.add_patch(Rectangle((self.SX0 + 2, self.SY0 + self.SH - bh + 1),
                               0.052 * self.IW, bh - 2, facecolor="#ffffff",
                               edgecolor="none", zorder=5))
        ax.text(self.SX0 + 2 + 0.026 * self.IW, by, "SIGLENT",
                color="#000000", fontsize=4.6, fontweight="bold",
                ha="center", va="center", zorder=6)
    def _hit(self, ev):
        for key, x, y, size, kind in self.hits:
            if kind == "knob":
                if math.hypot(ev.xdata - x, ev.ydata - y) <= size:
                    return key, x, y, kind
            else:
                w, h = size
                if x <= ev.xdata <= x + w and y <= ev.ydata <= y + h:
                    return key, x, y, kind
        return None

    def _select(self, key):
        """A click selects the control; the mouse wheel then turns it."""
        self.sel = key
        m = self.knobs[key]
        self.sel_ring.set_center((m._cx, m._cy))
        self.sel_ring.set_radius(m._r + 9)
        self.sel_ring.set_visible(True)
        self.lbl_sel.config(text="wheel acts on:  %s%s"
                            % (SEL_NAMES.get(key, key),
                               "   [fine]" if self.fine else ""))
        self._blit("scope")

    def _on_click(self, ev):
        if ev.xdata is None:
            return
        if ev.inaxes is self.ax_a:
            self._grab_magnet(ev)
            return
        if ev.inaxes is not self.ax_i:
            return
        h = self._hit(ev)
        if h is None:
            return
        key, x, y, kind = h
        if kind == "btn":
            self._press(key)
            return
        if math.hypot(ev.xdata - x, ev.ydata - y) < self.knobs[key]._r * 0.40:
            self._push(key)
            return
        self._select(key)

    def _push(self, key):
        """
        Knob push actions, straight from the SDS1000X-E user manual:
          HORIZONTAL POSITION  ->  reset the trigger delay to zero
          SEC/DIV              ->  turn Zoom on and off
          VERTICAL POSITION    ->  set the channel offset to zero
          VOLTS/DIV            ->  toggle coarse and fine adjustment
          TRIGGER LEVEL        ->  set the level to 50 % of the waveform
          UNIVERSAL            ->  confirm the highlighted item
        """
        if key == "hpos":
            self.delay = 0.0
        elif key == "hscale":
            self.zoom = not self.zoom
        elif key == "vpos":
            self.v_off = 0.0
        elif key in ("vscale", "vscale2"):
            self.fine = not self.fine
        elif key == "trig":
            hi = getattr(self.run, "v_hi", 5.0) if self.run else 5.0
            self.trig_lvl = 0.5 * (hi + V_LOW)
        if self.sel:
            self._select(self.sel)
        self.draw_scope()
        self._blit("scope")

    def _on_scroll(self, ev):
        """Wheel over a dial, or anywhere once a dial has been selected."""
        key = None
        if ev.inaxes is self.ax_i and ev.xdata is not None:
            h = self._hit(ev)
            if h is not None and h[3] == "knob":
                key = h[0]
                if key != self.sel:
                    self._select(key)
        if key is None:
            key = self.sel
        if key is None:
            return
        up = (ev.button == "up") if ev.button in ("up", "down") \
            else (getattr(ev, "step", 1) > 0)
        self._turn(key, 1 if up else -1)

    # ---- the electromagnetic holder is dragged round the angle screen --
    def _grab_magnet(self, ev):
        """Grab the ball (or the magnet head) to pull it aside."""
        b = self.bench
        a = math.radians(b.phi0)
        ball = (b.xh[0] - b.l[0] * math.sin(a), -b.l[0] * math.cos(a))
        self._drag_mag = (math.hypot(ev.xdata - ball[0],
                                     ev.ydata - ball[1]) < 3.0 * b.R(0)
                          or math.hypot(ev.xdata - self.mag_x,
                                        ev.ydata - self.mag_z) < 3.0 * b.R(0))

    def _on_drag(self, ev):
        if not self._drag_mag or ev.inaxes is not self.ax_a \
                or ev.xdata is None:
            return
        b = self.bench
        ang = math.degrees(math.atan2(-(ev.xdata - b.xh[0]),
                                      max(-ev.ydata, 1e-9)))
        self.var_phi.set(min(max(round(ang * 2) / 2.0, 3.0), 85.0))
        self._sync()
        self.update_scene()
        self._blit("bench")

    def _on_up(self, _ev=None):
        self._drag_mag = False

    def _turn(self, key, s):
        self.background = None            # the pointer is part of the
        line = self.knobs.get(key)        # cached panel, so rebuild it
        if line is not None:
            line._ang += s * 0.28
            a, r, x, y = line._ang, line._r, line._cx, line._cy
            line.set_data([x + 0.30 * r * math.sin(a),
                           x + 0.80 * r * math.sin(a)],
                          [y + 0.30 * r * math.cos(a),
                           y + 0.80 * r * math.cos(a)])
        if key == "hpos":
            self.delay += s * self.t_div * (0.004 if self.fine else 0.1)
        elif key == "univ":
            self.delay += s * self.t_div * (0.0005 if self.fine else 0.01)
        elif key == "hscale":
            i = TIME_DIVS.index(self.t_div)
            self.t_div = TIME_DIVS[min(max(i + s, 0), len(TIME_DIVS) - 1)]
        elif key == "vscale":                    # CH1, the live channel
            i = VOLT_DIVS.index(self.v_div)
            self.v_div = VOLT_DIVS[min(max(i + s, 0), len(VOLT_DIVS) - 1)]
        elif key == "vscale2":                   # CH2 is not connected
            i = VOLT_DIVS.index(self.v_div2)
            self.v_div2 = VOLT_DIVS[min(max(i + s, 0), len(VOLT_DIVS) - 1)]
        elif key == "vpos":
            self.v_off += s * self.v_div * 0.25
        elif key == "vpos2":
            pass                             # CH2 is not connected
        elif key == "trig":
            self.trig_lvl += s * self.v_div * 0.1
        self.draw_scope()
        self._blit("scope")

    def _rolling_now(self):
        return self.roll and self.t_div >= ROLL_MIN_TDIV

    def _press(self, key):
        if key == "single":
            self.trig_mode = "Single"
            self.single()
        elif key == "run":
            self.run_stop()
        elif key in ("auto", "default"):
            self.t_div, self.v_div, self.v_off = 0.5, 2.0, 0.0
            self.trig_lvl = 1.0
            self.single()
        elif key == "acquire":                   # cycles the memory depth
            self.mem_i = (self.mem_i + 1) % len(MEM_DEPTHS)
            self.single()
        elif key == "tauto":
            self.trig_mode = "Auto"
            self.cont = self.armed = True
            self._refresh()
        elif key == "tnormal":
            self.trig_mode = "Normal"
            self.cont = self.armed = True
            self._refresh()
        elif key == "roll":
            self.roll = not self.roll
            if not self.roll and self.run is not None:
                self.run.acquire(self.t_div, self.v_div,
                                 MEM_DEPTHS[self.mem_i])
                self.delay = self.run.rec_t0 + 0.5 * self.NX * self.t_div
            self._refresh()
        else:
            self.draw_scope()
            self._blit()

    # ───────────────────────── bench state ─────────────────────────
    def _sync(self):
        b = self.bench
        b.ball = [self.cb[0].current(), self.cb[1].current()]
        b.active2 = self.var_two.get()
        st = self.wiring.state()
        b.source = st["source"] or "photogate"
        self.wire_state = st
        R1, R2 = b.R(0), b.R(1)
        gap = self.var_gap.get() * 1e-3
        b.xh = [-R1 - gap / 2.0, R2 + gap / 2.0]
        dz = self.var_dz.get() * 1e-3
        b.l = [L_PEND, L_PEND - dz]
        # the holder is a physical object on its rod stand: the release
        # angle is whatever its position makes, and if it is not on the
        # arc of radius l it simply cannot hold the ball
        # the ball is pulled aside to phi0 and the electromagnet is
        # brought up to it: the holder position simply follows the ball
        b.phi0 = round(self.var_phi.get() * 2) / 2.0
        a = math.radians(b.phi0)
        reach = b.l[0] + b.R(0)
        self.mag_x = b.xh[0] - reach * math.sin(a)
        self.mag_z = -reach * math.cos(a)
        b.x_gate = b.xh[0] + self.var_gate.get() * 1e-3
        self.lbl_geo.config(
            text=("d_x - 2R = %+5.2f mm    d_z = %+5.2f mm    "
                  "gate = %+6.1f mm\n"
                  "ball %s"
                  % (self.var_gap.get(), self.var_dz.get(),
                     self.var_gate.get(),
                     "ATTACHED to the holder" if self.ball_held
                     else "hanging free (coil dead)")))

    def _live_state(self):
        """Where both balls are, and how fast, at this instant."""
        r = self._played.res
        t = float(np.clip(self.play_t, 0.0, r["t"][-1] if len(r["t"]) else 0))
        i = int(np.searchsorted(r["t"], t))
        i = min(max(i, 1), len(r["p"]) - 1)
        a, b = r["p"][i - 1], r["p"][i]
        dt = max(r["t"][i] - r["t"][i - 1], 1e-9)
        return (((b[0], b[1]), ((b[0] - a[0]) / dt, (b[1] - a[1]) / dt),
                 (b[2], b[3]), ((b[2] - a[2]) / dt, (b[3] - a[3]) / dt),
                 b[4], b[5]))

    def _restart_from(self, state):
        """
        Carry on from the state the bench is already in.  Hanging the
        second pendulum, or moving the gate, while the first ball is still
        swinging is perfectly possible on the bench, and the collisions
        that follow must be recorded like any others.
        """
        two = self.bench.active2
        tail = 60.0 if two else 300.0
        spare = copy.deepcopy(self.bench)
        run = Run(self.bench, self.t_div, self.v_div,
                  MEM_DEPTHS[self.mem_i], tmax=min(20.0, tail), init=state,
                  build=not self._rolling_now())
        self._pending = {}
        if tail > 20.0:
            box = self._pending

            def _worker(b=spare, box=box, tm=tail, st=state,
                        src=run.source):
                try:
                    r = b.simulate(tmax=tm, init=st)
                    box["built"] = Run.derive(r, src)
                    box["res"] = r
                except Exception:
                    box["res"] = None
            threading.Thread(target=_worker, daemon=True).start()
        st = self.wire_state
        ok = 0.0 < self.trig_lvl < getattr(run, "v_hi", 5.0)
        fault = self.wiring.fault()
        run.fault = fault
        if fault == "float":
            run.spoil(fault)
            run.acquire(self.t_div, self.v_div, MEM_DEPTHS[self.mem_i])
        usable = st["source"] is not None and st["channel"] == "ch1"
        self.run = run if (self.armed and usable and ok) else None
        if self.run is not None:
            self.delay = run.rec_t0 + 0.5 * self.NX * self.t_div
            self.armed = self.cont
        self._played = run
        self.play_t = 0.0
        self.play = True
        self.build_scene()
        self.background = None
        self.canvas.draw_idle()

    def _on_geo(self, which=None):
        was_running = self.play and self._played is not None
        state = self._live_state() if was_running else None
        self._sync()
        if was_running:
            self._restart_from(state)
            return
        self.build_scene()
        self.background = None
        self.canvas.draw_idle()


    # ───────────────────────── actions ─────────────────────────
    def set_coil(self, on):
        """
        The one and only release control.  Energising the coil grips the
        ball at the holder; cutting it lets the pendulum go, exactly as the
        General Instructions describe.
        """
        w = self.wiring
        was_held = self.ball_held
        w.coil_on = bool(on)
        self._sync()
        if on:
            self.play = False
            self._played = None
            self.ball_held = bool(self.wire_state["coil"])
            if not self.wire_state["powered"]:
                self.lbl_warn.config(
                    text="no 12 V on the box: plug the adaptor into DC 12V "
                         "and the holder coil into MAGNET on the cabling "
                         "page.")
            else:
                self.lbl_warn.config(text="")
        else:
            if was_held:
                self.lbl_warn.config(text="")
                self.release()
            self.ball_held = False
        self.coil_panel.redraw()
        w.redraw()
        self.update_scene()
        self.draw_scope()
        self._blit()                 # nothing static changed, so no
                                     # full redraw is needed here

    def wiring_changed(self):
        st = self.wiring.state()
        self.ball_held = bool(st["coil"])
        self.coil_panel.redraw()
        self._sync()
        self.build_scene()
        self.background = None
        self.canvas.draw_idle()

    def release(self):
        self._sync()
        st = self.wire_state

        # the first seconds are computed at once so the release is
        # instant; the long, slowly decaying tail is finished off in a
        # background thread on a private copy of the bench, with the same
        # random state, so the two agree exactly where they overlap
        two = self.bench.active2
        tail = 60.0 if two else 300.0
        head = 8.0
        spare = copy.deepcopy(self.bench)
        run = Run(self.bench, self.t_div, self.v_div,
                  MEM_DEPTHS[self.mem_i], tmax=min(head, tail),
                  build=not self._rolling_now())
        self._pending = {}
        if tail > head:
            box = self._pending

            def _tail_worker(b=spare, box=box, tm=tail, src=run.source):
                try:
                    r = b.simulate(tmax=tm)
                    box["built"] = Run.derive(r, src)
                    box["res"] = r
                except Exception:
                    box["res"] = None
            threading.Thread(target=_tail_worker, daemon=True).start()
        # the record only exists if the scope is armed AND the signal
        # really reaches CH1 through the cables you laid
        # the edge has to cross the trigger level, or nothing fires
        ok = 0.0 < self.trig_lvl < getattr(run, "v_hi", 5.0)
        fault = self.wiring.fault()
        run.fault = fault
        if fault == "float":
            run.spoil(fault)                 # it still triggers, on hum
            run.acquire(self.t_div, self.v_div, MEM_DEPTHS[self.mem_i])
        usable = st["source"] is not None and st["channel"] == "ch1"
        self.run = run if (self.armed and usable and ok) else None
        if self.armed and st["live"] and not ok:
            self.lbl_warn.config(
                text="the trigger level is outside the signal, so the scope "
                     "never fires.  Turn the LEVEL knob back inside the "
                     "pulse height.")
        msg = {"open": "nothing is feeding CH1: check the source lead and "
                       "the CH1/2 lead on the cabling page.",
               "wrongch": "the box is on CH2 but you are looking at CH1.",
               "float": "the ground lead is missing, so the input is "
                        "floating: what you see is mains pickup and drift, "
                        "not your signal."}.get(fault)
        if msg:
            self.lbl_warn.config(text=msg)
        if self.run is not None and not self.run.pulses:
            self.lbl_warn.config(text="no trigger: the ball never breaks the "
                                      "beam / never closes the circuit")
            self.run = None
            return
        if self.run is not None:
            self.delay = self.run.rec_t0 + 0.5 * self.NX * self.t_div
            self.armed = self.cont       # Run keeps acquiring
        self._played = run
        self.play = True
        self.play_t = 0.0
        self._last = time.perf_counter()

    def _absorb_tail(self):
        """Take the long tail from the background thread if it is ready."""
        if not self._pending:
            return False
        res = self._pending.pop("res", None)
        built = self._pending.pop("built", None)
        if res is None or not len(res["t"]) or self._played is None:
            return False
        if built is not None:
            self._played.adopt(res, built)     # nothing to recompute here
        else:
            self._played._build(res)
        return True

    def arm_now(self):
        """
        Arm while the pendulum is already going: the scope simply waits
        for the next pulse, which is what it does on the bench.  Without
        this, switching the scope on mid-swing caught nothing at all.
        """
        self._absorb_tail()
        p = self._played
        if p is None or not p.pulses or not self.wire_state["live"]:
            return False
        if not 0.0 < self.trig_lvl < getattr(p, "v_hi", 5.0):
            return False
        nxt = [a for a, _ in p.pulses if a > self.play_t + 0.02]
        if not nxt:
            return False
        p.t0_trig = nxt[0]
        p.acquire(self.t_div, self.v_div, MEM_DEPTHS[self.mem_i],
                  build=not self._rolling_now())
        self.run = p
        self.delay = p.rec_t0 + 0.5 * self.NX * self.t_div
        self.armed = self.cont
        return True

    def single(self):
        """
        Arm the scope.  It does NOT touch the pendulum: the instrument sits
        there waiting for a trigger and the trace only appears when the
        experiment actually produces one, which is what "release" does.
        """
        # Roll has no trigger at all, so asking for a single triggered
        # acquisition leaves it: that is what the instrument does
        self.frozen = None
        self.roll = False
        self.cont = False
        self.armed = True
        self.run = None
        if self.play:
            self.arm_now()
        self._refresh()

    def run_stop(self):
        """
        Green Run/Stop, as the manual describes it.

        STOP freezes the screen: the last acquisition stays on the display
        and nothing is added to it.  The pendulum is not part of the
        oscilloscope, so it carries on swinging exactly as before - only
        the instrument stops looking.

        RUN starts acquiring again from this instant.  Nothing is
        re-released, nothing is reset.
        """
        if self.cont:                              # -> Stop
            x = np.array(self.trace.get_xdata(), dtype=float)
            y = np.array(self.trace.get_ydata(), dtype=float)
            self.frozen = (x, y)
            self.cont = False
            self.armed = False
        else:                                      # -> Run
            self.frozen = None
            self.cont = True
            self.armed = True
            if self.play and self.run is None:
                self.arm_now()
        self._refresh()

    def _refresh(self):
        """
        Repaint the instrument.  Only animated artists change here, so the
        cached background stays valid and this costs a blit, not a full
        canvas redraw.
        """
        self.draw_scope()
        self._blit("scope")

    def stop(self):
        self.play = False

    def save_png(self):
        p = filedialog.asksaveasfilename(defaultextension=".png",
                                         filetypes=[("PNG image", "*.png")])
        if p:
            self.fig.savefig(p, dpi=180)

    def _on_motion(self, ev):
        if (ev.inaxes is self.ax_i and ev.xdata is not None
                and self.SX0 <= ev.xdata <= self.SX0 + self.SW
                and self.SY0 <= ev.ydata <= self.SY0 + self.SH):
            div = (ev.xdata - self.SX0) / self.SW * self.NX
            t = self.delay + (div - self.NX / 2) * self.t_div
            v = ((ev.ydata - self.SY0 - self.SH / 2)
                 / self.SH * self.NY * self.v_div)
            self.lbl_cursor.config(text="cursor :  t = %s   V = %+.3f V"
                                        % (eng(t, "s"), v))
        else:
            self.lbl_cursor.config(text="cursor :  -")

    # --------------------------- drawing ---------------------------
    def build_scene(self):
        """Static parts of the bench.  Rebuilt only when the geometry
        changes, never inside the animation loop."""
        ax = self.ax_a
        ax.clear()
        ax.axis("off")
        ax.set_aspect("equal", adjustable="box")
        b = self.bench
        L = b.l[0]
        ax.set_xlim(-0.405, 0.405)
        ax.set_ylim(-L - 0.082, 0.062)
        cx = 0.5 * (b.xh[0] + b.xh[1])

        for s_ in (-1, 1):
            ax.add_patch(Wedge((cx, 0.0), L, 180 if s_ < 0 else 270,
                               270 if s_ < 0 else 360,
                               facecolor="#f7f7f4", edgecolor="#d8dade",
                               lw=0.8, zorder=0))
        segs = []
        for a2 in range(-178, 179):
            ra = math.radians(a2 / 2.0)
            segs.append([(cx + 0.30 * L * math.sin(ra),
                          -0.30 * L * math.cos(ra)),
                         (cx + 0.985 * L * math.sin(ra),
                          -0.985 * L * math.cos(ra))])
        ax.add_collection(LineCollection(segs, colors="#b8bec5",
                                         linewidths=0.35, zorder=1))
        ar = 0.845 * L
        ticks = []
        for a in range(-88, 89):
            ra = math.radians(a)
            g = 0.014 if a % 10 == 0 else (0.010 if a % 5 == 0 else 0.006)
            ticks.append([(cx + ar * math.sin(ra), -ar * math.cos(ra)),
                          (cx + (ar + g) * math.sin(ra),
                           -(ar + g) * math.cos(ra))])
        ax.add_collection(LineCollection(ticks, colors="#5a6068",
                                         linewidths=0.5, zorder=2))
        for a in range(-80, 81, 20):
            ra = math.radians(a)
            ax.text(cx + (ar + 0.024) * math.sin(ra),
                    -(ar + 0.024) * math.cos(ra), str(abs(a)),
                    ha="center", va="center", fontsize=6, color="#4a5057",
                    zorder=2)

        yr = -L - 0.030
        self.y_rail = yr
        ax.add_patch(Rectangle((-0.395, yr - 0.016), 0.79, 0.008,
                               facecolor="#e6e8ea", edgecolor="#b9bfc6",
                               lw=0.6, zorder=3))
        ax.add_patch(Rectangle((-0.395, yr - 0.008), 0.79, 0.008,
                               facecolor="#2f5fa8", edgecolor="#24487e",
                               lw=0.6, zorder=3))
        ax.add_patch(Rectangle((-0.395, yr), 0.79, 0.007,
                               facecolor="#d3d6da", edgecolor="#b9bfc6",
                               lw=0.6, zorder=3))
        tape = [[(x, yr - 0.008), (x, yr - 0.004)]
                for x in np.arange(-0.390, 0.395, 0.010)]
        ax.add_collection(LineCollection(tape, colors="#dce6f4",
                                         linewidths=0.4, zorder=4))
        ax.add_patch(Rectangle((cx - 0.010, yr + 0.007), 0.020,
                               -(yr + 0.007), facecolor="#c8ccd1",
                               edgecolor="#9aa0a6", lw=0.6, zorder=2))
        ax.add_patch(Rectangle((cx - 0.115, -0.014), 0.230, 0.016,
                               facecolor="#e9ebee", edgecolor="#9aa0a6",
                               lw=0.8, zorder=5))

        gx = b.x_gate
        for dx in (-0.011, 0.011):
            ax.add_patch(Rectangle((gx + dx - 0.004, yr + 0.007), 0.008,
                                   0.055, facecolor="#f2f2ee",
                                   edgecolor="#9aa0a6", lw=0.8, zorder=6))
        ax.add_patch(Rectangle((gx - 0.007, yr + 0.030), 0.005, 0.012,
                               facecolor="#2b2e32", edgecolor="none",
                               zorder=7))
        ax.plot([gx - 0.007, gx + 0.007], [yr + 0.036, yr + 0.036],
                color="#e03030", lw=0.8, ls=(0, (2, 2)), zorder=7)

        # (the rod stand is drawn with the holder: they move together)

        # hanger units and the dynamic artists
        self.art_wire, self.art_ball = [], []
        for i in (0, 1):
            ax.add_patch(Rectangle((b.xh[i] - 0.013, -0.020), 0.026, 0.016,
                                   facecolor="#dfe2e6", edgecolor="#8b9096",
                                   lw=0.8, zorder=11))
            ax.add_patch(Circle((b.xh[i] - 0.005, -0.025), 0.005,
                                facecolor="#fbfaf6", edgecolor="#8b9096",
                                lw=0.6, zorder=11))
            ax.add_patch(Circle((b.xh[i] + 0.006, -0.025), 0.004,
                                facecolor="#3b4149", edgecolor="#20242a",
                                lw=0.6, zorder=11))
            (w,) = ax.plot([], [], color="#c86a2a", lw=1.0, zorder=8)
            c = Circle((0, 0), b.R(i), facecolor="#b9bdc4",
                       edgecolor="#585d63", lw=1.0, zorder=9)
            ax.add_patch(c)
            self.art_wire.append(w)
            self.art_ball.append(c)
        (self.art_mline,) = ax.plot([], [], color="#c86a2a", lw=0.7,
                                    ls=(0, (4, 3)), zorder=8)
        self.art_mball = Circle((0, 0), b.R(0), facecolor="none",
                                edgecolor="#c86a2a", lw=0.9, ls="--",
                                zorder=9)
        ax.add_patch(self.art_mball)
        (self.art_mag,) = ax.plot([], [], color="#26292d", lw=7,
                                  solid_capstyle="butt", zorder=9)
        (self.art_magcap,) = ax.plot([], [], color="#5a6068", lw=7,
                                     solid_capstyle="butt", zorder=10)
        # item 11, as photographed: a rail clamp with a knurled screw,
        # a long thin chrome rod, a cross-clamp boss with three knurled
        # screws near the top, and a short black cylindrical magnet
        (self.art_rod,) = ax.plot([], [], color="#b9bec4", lw=3.4, zorder=5)
        (self.art_rodhi,) = ax.plot([], [], color="#f2f4f6", lw=1.1, zorder=5)
        # NB plain Rectangles here: FancyBboxPatch measures its rounding
        # in DATA units, and the bench is in metres
        self.art_foot = Rectangle((0, 0), 0.030, 0.016,
                                  facecolor="#c8ccd1", edgecolor="#8b9096",
                                  lw=0.8, zorder=6)
        ax.add_patch(self.art_foot)
        self.art_footscrew = Circle((0, 0), 0.0055, facecolor="#e6e8ea",
                                    edgecolor="#8b9096", lw=0.7, zorder=7)
        ax.add_patch(self.art_footscrew)
        self.art_clamp = Rectangle((0, 0), 0.034, 0.020,
                                   facecolor="#d3d7dc", edgecolor="#8b9096",
                                   lw=0.9, zorder=7)
        ax.add_patch(self.art_clamp)
        self.art_screws = [Circle((0, 0), 0.0050, facecolor="#eceef0",
                                  edgecolor="#8b9096", lw=0.7, zorder=8)
                           for _ in range(3)]
        for c in self.art_screws:
            ax.add_patch(c)
        (self.art_cable,) = ax.plot([], [], color="#26292d", lw=0.8, zorder=6)
        self.art_txt = ax.text(0, 0, "", ha="center", fontsize=8, zorder=12)
        self.art_grip = ax.text(0, 0, "", ha="center", fontsize=8,
                                fontweight="bold", zorder=13)
        self.art_cfg = ax.text(-0.400, 0.054, "", fontsize=8,
                               color="#2b4a6a", family="monospace", va="top")
        ax.set_xlim(-0.405, 0.405)
        ax.set_ylim(-b.l[0] - 0.086, 0.062)
        self._collect_animated()
        self.update_scene()

    def update_scene(self):
        b = self.bench
        if self.play and self._played is not None:
            p = self._frame()
            pos = [(p[0], p[1]), (p[2], p[3])]
        else:
            th = b.equilibrium()
            pos = [b.centre(0, th[0]), b.centre(1, th[1])]
            if self.ball_held:
                # the coil grips ball 1: it hangs from the pivot on a taut
                # wire, pulled aside to wherever the holder is
                rr0 = math.hypot(self.mag_x - b.xh[0], self.mag_z) or 1e-9
                pos[0] = (b.xh[0] + b.l[0] * (self.mag_x - b.xh[0]) / rr0,
                          b.l[0] * self.mag_z / rr0)
            else:
                pos[0] = b.centre(0, th[0])       # it just hangs
        n = 2 if b.active2 else 1
        for i in (0, 1):
            on = i < n
            self.art_wire[i].set_visible(on)
            self.art_ball[i].set_visible(on)
            if on:
                self.art_wire[i].set_data([b.xh[i], pos[i][0]],
                                          [0.0, pos[i][1]])
                self.art_ball[i].set_center(pos[i])
                self.art_ball[i].set_radius(b.R(i))
        show = True
        mx, my = self.mag_x, self.mag_z
        rr = math.hypot(mx - b.xh[0], my) or 1e-9
        ux, uy = (mx - b.xh[0]) / rr, my / rr
        # the pole face sits on the outer surface of the held ball and the
        # body of the magnet runs outward from it along the same radius.
        # The magnet is clamped straight into the cross-boss, so the boss
        # sits on the back face of the magnet and the rod runs down from
        # there - there is nothing at all in between.
        R0 = b.R(0)
        face = (mx, my)
        body = 0.024                      # the short black cylinder
        zmin = self.y_rail + 0.008
        if uy < -1e-6:
            body = min(body, max((face[1] - zmin) / (-uy), 0.006))
        back = (face[0] + ux * body, face[1] + uy * body)
        ball = (b.xh[0] + b.l[0] * ux, b.l[0] * uy)
        rod_x = back[0]
        clamp_y = back[1]
        # the dashed circle shows where the ball WOULD be caught
        self.art_mball.set_visible(not self.ball_held)
        self.art_mline.set_visible(self.ball_held)
        self.art_txt.set_visible(True)
        for art in ([self.art_mag, self.art_magcap,
                     self.art_rod, self.art_rodhi, self.art_foot,
                     self.art_footscrew, self.art_clamp, self.art_cable]
                    + self.art_screws):
            art.set_visible(show)
        if True:
            self.art_mline.set_data([b.xh[0], ball[0]], [0.0, ball[1]])
            self.art_mball.set_center(ball)
            self.art_mball.set_radius(R0)
            self.art_mball.set_edgecolor("#c86a2a")
            self.art_mag.set_color("#26292d")
            self.art_magcap.set_color("#c42030" if self.ball_held
                                      else "#5a6068")
            self.art_mag.set_data([face[0], back[0]], [face[1], back[1]])
            # a rigid assembly, exactly as photographed: a rail clamp, a
            # long chrome rod, a cross-clamp boss and the black magnet
            rail_top = self.y_rail
            self.art_foot.set_xy((rod_x - 0.015, rail_top - 0.004))
            self.art_footscrew.set_center((rod_x + 0.019, rail_top + 0.004))
            top = max(clamp_y + 0.026, rail_top + 0.055)
            self.art_rod.set_data([rod_x, rod_x], [rail_top + 0.004, top])
            self.art_rodhi.set_data([rod_x - 0.0011, rod_x - 0.0011],
                                    [rail_top + 0.004, top])
            self.art_clamp.set_xy((rod_x - 0.017, clamp_y - 0.011))
            for k, c in enumerate(self.art_screws):
                c.set_center((rod_x - 0.022 + k * 0.022,
                              clamp_y + (0.000 if k == 1 else 0.005)))
            self.art_cable.set_data(
                [rod_x + 0.006, rod_x + 0.012, rod_x + 0.006],
                [clamp_y - 0.012, (clamp_y + rail_top) / 2, rail_top + 0.010])
            self.art_magcap.set_data([face[0], face[0] + ux * 0.006],
                                     [face[1], face[1] + uy * 0.006])
            self.art_txt.set_position((ball[0], ball[1] + R0 + 0.016))
            self.art_txt.set_text("")
        # the circle the pole face has to reach, drawn while the coil is
        # live but has not caught anything yet
        self.art_grip.set_position((0.0, 0.014))
        if self.play:
            self.art_grip.set_text("")
        elif self.ball_held:
            self.art_grip.set_text("ball attached  -  read the angle off the "
                                   "screen, then flick the COIL lever down")
            self.art_grip.set_color("#207020")
        else:
            self.art_grip.set_text("coil dead - the ball just hangs.  "
                                   "Check the cabling page.")
            self.art_grip.set_color("#b00000")
        self.art_cfg.set_text(b.config_name())

    def _frame(self):
        r = self._played.res
        t = np.clip(self.play_t, 0.0, r["t"][-1] if len(r["t"]) else 0.0)
        i = int(np.searchsorted(r["t"], t))
        i = min(max(i, 0), len(r["p"]) - 1)
        return r["p"][i]

    def _grat(self):
        """(x, y, w, h) of the graticule inside the glass."""
        return (self.SX0,
                self.SY0 + self.SH * self.BAR_B,
                self.SW * (1.0 - self.SIDE),
                self.SH * (1.0 - self.BAR_T - self.BAR_B))

    def _sx(self, div):
        """screen division 0..14  ->  instrument x"""
        x0, _, w, _ = self._grat()
        return x0 + np.asarray(div, dtype=float) * w / self.NX

    def _sy(self, volts):
        """volts  ->  instrument y, clipped to the graticule"""
        _, y0, _, h = self._grat()
        d = np.clip(np.asarray(volts, dtype=float) / self.v_div
                    + self.v_off / self.v_div, -self.NY / 2, self.NY / 2)
        return y0 + h / 2 + d * h / self.NY

    def _roll_trace(self, run, t0, t1):
        """
        Roll mode.  The record is no longer a frozen block, so the trace is
        built straight from the pulse train: for every screen column, the
        lowest and highest the signal reaches inside that column.  It is
        the same envelope the peak detect would give, and it costs nothing.
        """
        npix = self.npix
        edges = np.linspace(t0, t1, npix + 1) + run.t0_trig
        lo = np.full(npix, V_LOW, dtype=np.float32)
        hi = np.full(npix, V_LOW, dtype=np.float32)
        vhi = getattr(run, "v_hi", 5.0)
        for a, b in run.pulses:
            if b < edges[0] or a > edges[-1]:
                continue
            i = max(int(np.searchsorted(edges, a) - 1), 0)
            j = min(int(np.searchsorted(edges, b)), npix)
            if j > i:
                hi[i:j] = vhi
        rg = np.random.default_rng(3)
        n = 0.010 * (rg.random(npix) - 0.5)
        xc = (np.arange(npix) + 0.5) / npix * self.NX
        ys = np.empty(2 * npix, dtype=np.float32)
        ys[0::2] = lo + n
        ys[1::2] = hi + n
        self.trace.set_data(self._sx(np.repeat(xc, 2)), self._sy(ys))
        self.dots.set_data([], [])

    def draw_scope(self):
        run = self.run
        if self.frozen is not None:
            # Stop: the screen holds whatever was on it
            self.trace.set_data(*self.frozen)
            self.dots.set_data([], [])
            self.txt_hi.set_position((self.SX0 + 0.056 * self.IW,
                                      self.SY0 + self.SH
                                      - self.SH * self.BAR_T / 2))
            self.txt_hi.set_text("Stop")
            self.txt_hi.set_color("#ff4040")
            self.lbl_mpos.config(text="M Pos = %.6f s" % self.delay)
            return
        rolling = (self.roll and self.cont and run is not None
                   and self._played is not None
                   and self.t_div >= ROLL_MIN_TDIV)
        if rolling:
            # the window ends at this instant and slides with it, so the
            # trace never restarts: it just runs off the left edge
            t1 = self.play_t - run.t0_trig
            t0 = t1 - self.NX * self.t_div
            self.delay = 0.5 * (t0 + t1)
        else:
            t0 = self.delay - self.NX / 2 * self.t_div
            t1 = self.delay + self.NX / 2 * self.t_div
        self.trace.set_data([], [])
        self.dots.set_data([], [])
        # the acquisition runs on its own: the trace stops growing when
        # the record window is full, whatever the pendulum is doing
        live = (self.play_t - run.t0_trig) if run is not None else None
        if live is not None:
            t1 = min(t1, live)
        if rolling:
            self._roll_trace(run, t0, t1)
        elif run is not None and run.rec is not None and t1 > t0:
            npix = self.npix
            spp = run.rec_fs * (t1 - t0) / npix
            if spp > 2.0:
                k0 = max(int((t0 - run.rec_t0) * run.rec_fs), 0)
                k1 = min(int((t1 - run.rec_t0) * run.rec_fs) + 2,
                         len(run.rec))
                seg = run.rec[k0:k1]
                m = len(seg) // npix
                if m >= 1:
                    core = seg[:m * npix].reshape(npix, m)
                    lo, hi = core.min(axis=1), core.max(axis=1)
                    tail = seg[m * npix:]
                    if tail.size:
                        lo[-1] = min(lo[-1], tail.min())
                        hi[-1] = max(hi[-1], tail.max())
                    xc = (np.arange(npix) + 0.5) / npix * (t1 - t0) \
                        / self.t_div
                    ys = np.empty(2 * npix, dtype=np.float32)
                    ys[0::2], ys[1::2] = lo, hi
                    self.trace.set_data(self._sx(np.repeat(xc, 2)),
                                        self._sy(ys))
            else:
                tt = np.linspace(t0, t1, npix)
                v = sinx_x(run.rec, run.rec_t0, run.rec_fs, tt)
                self.trace.set_data(self._sx((tt - t0) / self.t_div),
                                    self._sy(v))
                if spp < 0.25:
                    k0 = max(int((t0 - run.rec_t0) * run.rec_fs), 0)
                    k1 = min(int((t1 - run.rec_t0) * run.rec_fs) + 1,
                             len(run.rec))
                    ts = run.rec_t0 + np.arange(k0, k1) / run.rec_fs
                    self.dots.set_data(self._sx((ts - t0) / self.t_div),
                                       self._sy(run.rec[k0:k1]))
        gx0, _, gw0, _ = self._grat()
        self.trig_lv.set_data([gx0 + gw0 - 3],
                              [float(self._sy(self.trig_lvl))])
        cx = float(self._sx(self.NX / 2.0))
        self.centre.set_data([cx, cx], [self.SY0, self.SY0 + self.SH])
        if t0 <= 0.0 <= t1:
            self.trig.set_data([float(self._sx((0.0 - t0) / self.t_div))],
                               [self.SY0 + self.SH * 0.94])
        else:
            self.trig.set_data([], [])

        if rolling:
            state, col = "Roll", "#ffd23a"
        elif run is None:
            # manual: in Auto the scope free-runs and shows "Auto" when no
            # trigger is found; in Normal it waits and shows "Ready"
            if not self.armed:
                state, col = "Stop", "#ff4040"
            elif self.trig_mode == "Auto":
                state, col = "Auto", "#40ff40"
            else:
                state, col = "Ready", "#40ff40"
        elif live is None or live <= run.rec_t0:
            state, col = "Ready", "#40ff40"
        elif live < run.rec_t0 + run.rec_n / run.rec_fs:
            state, col = "Trig'd", "#ffd23a"
        else:
            state, col = "Stop", "#ff4040"
        self.txt_hi.set_position((self.SX0 + 0.056 * self.IW,
                                  self.SY0 + self.SH
                                  - self.SH * self.BAR_T / 2))
        self.txt_hi.set_text(state)
        self.txt_hi.set_color(col)
        self.txt_lo.set_position((self.SX0 + 6, self.SY0
                                  + self.SH * self.BAR_B / 2))
        self.txt_lo.set_text("M %s   CH1 = %g V   M Pos = %.6f s"
                             % (tdiv_label(self.t_div), self.v_div,
                                self.delay))
        _, gy, gw, gh = self._grat()
        self.txt_sa.set_position((self.SX0 + gw + 4, gy + gh - 6))
        if run is not None and run.rec is not None:
            self.txt_sa.set_text("Sa %s\nCurr %s"
                                 % (fs_label(run.rec_fs),
                                    mem_label(run.rec_n)))
            dts = 1.0 / run.rec_fs
            self.lbl_acq.config(
                text=("acquired at %s/div\n%s , %s , dt = %s"
                      % (tdiv_label(run.rec_tdiv), fs_label(run.rec_fs),
                         mem_label(run.rec_n), eng(dts, "s")))
                + ("\n%.0f fps  (%d trace points)" % (self.fps, self.npix)
                   if self.play else ""))
            if run.feature and run.feature < 10 * dts:
                self.lbl_warn.config(
                    text=("the feature you must measure is only %.2f samples "
                          "wide - what you see is the sin(x)/x rebuild of a "
                          "few points.  Use a faster time base or a deeper "
                          "acquisition memory, then press Single."
                          % (run.feature / dts)))
        else:
            self.txt_sa.set_text("")
            self.lbl_acq.config(text="")
        self.lbl_mpos.config(text="M Pos = %.6f s" % self.delay)

    def _tick(self):
        """
        One frame.  The bench and the oscilloscope are two separate
        machines here and the loop treats them that way:

          * the BENCH clock advances whenever the pendulum is swinging.
            Nothing on the instrument can start, stop or rewind it - only
            the coil switch and the "stop the pendulum" button can.
          * the SCOPE is redrawn whenever it is acquiring.  Run and Stop
            change what the screen does and nothing else.

        The frame budget is measured and fed back: only the moving artists
        are redrawn over a cached background, the after() interval follows
        the measured render time so a slow machine drops frames instead of
        queueing, and the clock is wall-clock so dropped frames never slow
        the pendulum down.
        """
        t_start = time.perf_counter()
        dt = t_start - self._last
        self._last = t_start

        # ---- the bench -----------------------------------------------
        moving = False
        if self.play and self._played is not None:
            self.play_t += dt                      # real time, 1x
            self._absorb_tail()
            self.update_scene()
            moving = True

        # ---- the instrument, quite independently ---------------------
        if self.cont and self.run is not None and not self.roll:
            r = self.run
            if (r.rec is not None and self.play_t - r.t0_trig
                    > r.rec_t0 + r.rec_n / r.rec_fs):
                if r.retrigger(self.t_div, self.v_div,
                               MEM_DEPTHS[self.mem_i]):
                    self.delay = r.rec_t0 + 0.5 * self.NX * self.t_div
                    self.background = None

        if moving or self.cont:
            self._frame_i += 1
            if self._frame_i % 3 == 0 or not moving:
                self.draw_scope()
                self._blit()
            else:
                self._blit("bench")
            ms = (time.perf_counter() - t_start) * 1000.0
            self.render_ms += 0.25 * (ms - self.render_ms)
            self.fps += 0.25 * (1000.0 / max(ms, 1.0) - self.fps)
            if self.render_ms > 26.0 and self.npix > 300:
                self.npix //= 2
            elif self.render_ms < 10.0 and self.npix < 1200:
                self.npix *= 2
            delay = int(min(max(1.02 * self.render_ms, 5.0), 60.0))
        else:
            delay = 40
        self.root.after(delay, self._tick)



def main():
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.15)
    except Exception:
        pass
    app = App(root)
    app.build_scene()
    app.draw_scope()
    app.canvas.draw_idle()
    root.mainloop()


if __name__ == "__main__":
    main()
