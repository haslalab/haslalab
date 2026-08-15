#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APhO 2023 (Mongolia, Ulaanbaatar) - Experimental Problem 2
INTERFERENCE FROM A THERMALLY DEFORMED SURFACE - virtual apparatus

  Q1  Hertzian Contact Stress          (10 points)
        Part A  Large angle pendulum
        Part B  Period of the oscillation
        Part C  Behaviors of the collisions
        Part D  Time of collisions
        Part E  Parameters of Hertz deformation
  Q2  Interference from thermally deformed surface (10 points)
        Part A  Yield strength power
        Part B  D_out and N vs laser power
        Part C  Visible angle / angular width of fringes
        Part D  Height of the thermal deformation

Design philosophy (same as the IPhO 2017 / 2025 / 2026 simulators):
  * a real forward physical model, NOT a replay of the official tables
  * true parameters randomised each session inside realistic tolerances
  * every number must be *measured* by the user through an emulated
    Siglent digital storage oscilloscope / multimeters / ruler, with
    realistic quantisation, jitter and instrument limitations
  * built-in analysis compares the session against the OFFICIAL
    solution sheets (APhO_2023_S4.pdf, APhO_2023_S5.pdf)

Calibration targets taken from the official solutions
---------------------------------------------------------------
  grad(1/dt)            = 110.77 s^-1          (A.1)
  k_v = 2 sqrt(g l)     = 3.517 m/s            (A.2)
  T_0                   = 1.1267 s             (B.1)
  alpha = 1/4, beta = 9/64                     (B.1)
  g_UB                  = 9.804 m/s^2          (B.2)
  tau = A (R1+R2)/c (c/v)^(1/5), A = 2.40      (D.4)
  c   = sqrt(E'/rho)    = 5180 m/s
  E   = 200 GPa, nu = 0.3
  N(P) = 0.4632 P - 132.94  (fringes vs power) (B.3)
  m    = 2h/lambda                             (D.1)
  R_base = 167.82 lambda,  m = m' + 2          (Q2 appendix)
  P_yield ~ 363.6 mW                           (A.1)

Requires: numpy only          (tkinter ships with CPython)
Run:      python apho2023_Q2_thermo_deformation.py
"""

import math
import time
import zlib
import struct
import base64
import random

import numpy as np

import tkinter as tk
from tkinter import ttk

APP_TITLE = "APhO 2023  Q2  Thermo-deformation  -  virtual apparatus"

# ==========================================================================
#  PHYSICAL CONSTANTS  (Ulaanbaatar)
# ==========================================================================

LAMBDA = 650.0e-9                 # m, red laser diode
R_BASE_LAMBDA = 167.82            # base radius of the thermal bump, in lambda
P_THRESHOLD = 287.0               # mW, onset of the thermal deformation
N_SLOPE = 0.4632                  # fringes per mW
P_YIELD_NOM = 363.6               # mW, yield strength of PMMA
HIDDEN_ORDERS = 2.1722            # official C.3 intercept

# The drive is limited by the control box, not by the knob.  Neither the
# question sheet nor the solution states a maximum current, so the
# ceiling is taken from what the marking scheme has to be able to reach:
#
#   D.1 requires the candidate's data to span 200 mW to 400 mW;
#   A.1 awards credit for a yield power anywhere up to 450 mW.
#
# 450 mW needs 116.3 mA on this diode's I-V curve, so a 115 mA ceiling -
# 444 mW - left the top marking band out of reach.  120 mA gives 467 mW,
# which clears every band with a little to spare.  For reference the
# official run itself never went above 98.3 mA (368 mW).
I_MAX = 120.0                     # mA, the control box will not go higher

# A laser diode does not emit below its own threshold current: with the
# dial wound right down the circuit is live and the meters read, but
# there is no beam.  The cabling page used to light its indicator and
# draw a beam out of the head from the mere fact that the circuit was
# complete, so at minimum intensity it claimed an output the bench and
# the control box both - correctly - showed as dark.
I_LASING = 2.0                    # mA, below this the diode does not lase

# ---- the three carriers also rise and fall on their posts -------------
# Every stand on the bench has a vertical slide with its own thumbscrew,
# and they do not come set to the same height: the question sheet has the
# candidate "position the beam at the same height along the axis of the
# optical bench" so that it "passes freely through the hole in the
# screen".  Until that is done the beam simply lands on the back of the
# screen and there is nothing to measure.
Z_MIN, Z_MAX = 0.0, 40.0          # mm of travel on a post
Z_NOM = 20.0                      # mm, the middle of that travel
HOLE_R = 2.5                      # mm, radius of the hole in the screen
PLATE_HALF = 25.0                 # mm, half height of the PMMA plate


LEG_X, LEG_W = np.polynomial.legendre.leggauss(96)


# ==========================================================================
#  numerical helpers
# ==========================================================================


# ==========================================================================
#  Q1 - COLLISION MODEL  (Parts C, D, E)
# ==========================================================================

# ==========================================================================
#  Q2 - THERMAL DEFORMATION / INTERFERENCE MODEL
# ==========================================================================
class ThermoModel:
    """
    Laser diode -> PMMA surface -> reflected diffraction pattern.

    Height of the thermal bump:      h = m * lambda / 2
    Number of fringes:               m = 0.4632 (P - 287)   [official fit]
    Dark fringe condition:           R_base sin(alpha_m) = m lambda
                                     R_base = 167.82 lambda
    The two innermost orders are hidden inside the bright central spot,
    so the observed order is m' = m - 2 (the official appendix).

    Two things deform the surface, and they behave quite differently.

    THERMAL (reversible).  The beam heats the acrylic, it expands, and a
    shallow bump rises over the irradiated spot.  It follows the power
    and it is fully reversible: turn the laser down and the bump sinks
    again.  This is the pattern Parts B and D are about, and it is what
    "the pattern shows reversibility and shrinkage up to a certain
    power" in Part A refers to.

    PLASTIC (frozen).  Above the yield power the material passes its
    glass transition and flows.  What flows does not come back: a small
    crater is left in the plate for good.  It is confined to the hottest
    core of the spot, so it is NARROWER than the thermal bump, and a
    narrower aperture throws its rings out to WIDER angles.  That is the
    faint second set of rings, with a bright one far out, that appears
    once you have been past the yield point - and because it does not
    depend on the power any more, it is still sitting there when you
    turn the laser back down and the thermal pattern has shrunk away.
    Finding the power at which that happens is Part A.1.

    Neither deformation is instantaneous.  Both are governed by heat
    diffusing through the acrylic, and with PMMA's diffusivity
    alpha = k/(rho c) = 0.19/(1180 x 1470) = 1.10e-7 m^2/s a heat
    affected depth of half a millimetre gives tau = d^2/alpha = 2.3 s.
    So the pattern grows over a few seconds after you move the knob,
    decays over a few seconds after you turn the laser off, and the
    plastic flow, being a viscous process near Tg, takes longer still.
    """

    # ---- PMMA, from the data on the question sheet and standard tables --
    ALPHA_TH = 1.095e-7      # m^2/s, thermal diffusivity k/(rho c)
    D_HOT = 0.50e-3          # m, heat affected depth while heating
    D_COOL = 0.60e-3         # m, the warm zone has spread by then
    TAU_HEAT = D_HOT * D_HOT / ALPHA_TH        # 2.3 s
    TAU_COOL = D_COOL * D_COOL / ALPHA_TH      # 3.3 s
    TAU_PLASTIC = 8.0        # s, viscous flow near the glass transition
    RETAIN = 0.55            # fraction of the excess that stays behind
    SEC_RADIUS = 0.62        # melted core radius / thermal bump radius
    SEC_BRIGHT = 0.32        # the second pattern is the fainter one

    def __init__(self, rng):
        self.rng = rng
        self.R_base_lam = R_BASE_LAMBDA * (1.0 + rng.gauss(0.0, 0.015))
        self.P_th = P_THRESHOLD * (1.0 + rng.gauss(0.0, 0.004))
        self.slope = N_SLOPE * (1.0 + rng.gauss(0.0, 0.03))
        self.P_yield = P_YIELD_NOM * (1.0 + rng.gauss(0.0, 0.02))
        # The official solution's own regression is
        #     m' = 167.82 sin(alpha_m) - 2.1722
        # so the number of orders swallowed by the central spot is
        # 2.1722, not the 2 that the write-up rounds it to.
        self.hidden = HIDDEN_ORDERS + rng.gauss(0.0, 0.10)
        self.iv_a = 0.35928
        self.iv_b = 0.73823 * (1.0 + rng.gauss(0.0, 0.004))
        self.sec_ratio = self.SEC_RADIUS * (1.0 + rng.gauss(0.0, 0.03))
        self.spot_key = (0, 0)
        self.spots = {}
        self.m_th = 0.0          # thermal, reversible, follows the power
        self.m_pl = 0.0          # plastic, frozen into the plate for good
        self.dirty = abs(rng.gauss(0.0, 0.35))       # surface contamination
        self.ellipticity = 1.0 + abs(rng.gauss(0.0, 0.012))
        self.tilt = rng.uniform(0, math.pi)

    # ---------------- laser electrical model ----------------
    def diode_voltage(self, current_mA):
        if current_mA <= 1.0:
            return 0.0
        return self.iv_a + self.iv_b * math.log(current_mA)

    def read_meters(self, current_mA):
        """Two multimeters: DC current (mA) and DC voltage (V) with noise."""
        i = current_mA + self.rng.gauss(0.0, 0.12)
        v = self.diode_voltage(current_mA) + self.rng.gauss(0.0, 0.004)
        return round(i, 1), round(v, 2)

    def power_true(self, current_mA):
        return current_mA * self.diode_voltage(current_mA)

    # ---------------- deformation ----------------
    SOFT_W = 0.9             # width of the knee at the fringe threshold

    def m_steady(self, current_mA, lit=True):
        """
        The thermal bump the present power would settle at.

        Warm acrylic is always a little domed, so there is no power at
        which the surface is exactly flat and the diffraction exactly
        vanishes - it just falls below the two orders that are buried in
        the bright central spot, and stops being countable.  Clipping the
        official straight line at zero put a kink in the surface that is
        not there on the bench, so the line is rolled off smoothly
        instead:

            m = w ln(1 + exp(slope (P - P_th) / w))

        Above the threshold this IS the official fit - at ten orders the
        two differ by 5e-5 - and below it the bump shrinks away smoothly
        rather than being switched off.
        """
        if not lit:
            return 0.0
        P = self.power_true(current_mA)
        x = self.slope * (P - self.P_th) / self.SOFT_W
        # log1p(exp(x)) written so that large x cannot overflow
        soft = x + math.log1p(math.exp(-x)) if x > 0 else math.log1p(math.exp(x))
        return self.SOFT_W * soft

    def m_yield(self):
        """The thermal amplitude at which the surface starts to flow."""
        return max(self.slope * (self.P_yield - self.P_th), 0.0)

    def step(self, dt, current_mA, lit):
        """
        Advance the surface by dt seconds.

        The bump relaxes towards whatever the present power supports; the
        crater creeps towards whatever the present bump would leave
        behind, and never creeps back.
        """
        if dt <= 0.0:
            return
        dt = min(dt, 1.0)                # a long pause is not a long burn
        target = self.m_steady(current_mA, lit)
        tau = self.TAU_HEAT if target > self.m_th else self.TAU_COOL
        self.m_th += (target - self.m_th) * (1.0 - math.exp(-dt / tau))
        over = self.m_th - self.m_yield()
        if over > 0.0:
            want = self.RETAIN * over
            if want > self.m_pl:
                self.m_pl += ((want - self.m_pl)
                              * (1.0 - math.exp(-dt / self.TAU_PLASTIC)))

    def settle(self, current_mA, lit=True, seconds=90.0):
        """
        Run the surface forward as if you had waited.  step() caps a
        single call at one second on purpose, so that a window left
        minimised for an hour does not come back to a burnt plate; this
        walks it forward properly instead.
        """
        n = int(max(seconds / 0.25, 1))
        for _ in range(n):
            self.step(0.25, current_mA, lit)

    @property
    def melted(self):
        return self.m_pl > 0.05

    def height_lambda(self):
        """Total surface relief now, in wavelengths."""
        return (self.m_th + self.m_pl) / 2.0

    def intensity(self, nu, mmax):
        """Radial intensity as a function of nu = R_base sin(alpha)/lambda."""
        core = 1.35 * np.exp(-(nu / 1.55) ** 2)
        env = 0.80 * np.exp(-0.85 * (nu / max(mmax, 1.0)) ** 2)
        cutoff = 0.5 * (1.0 - np.tanh((nu - mmax) / 0.55))
        ring = env * cutoff * np.sin(np.pi * nu) ** 2
        # the first orders drown in the bright core
        ring *= 0.5 * (1.0 + np.tanh((nu - self.hidden) / 0.55))
        return core + ring

    def crater(self, nu, mmax):
        """
        The frozen crater, which has a rim rather than a smooth shoulder.

        A sharp edge diffracts into a strong outermost ring instead of
        fading away, which is the bright ring you see well outside the
        thermal pattern once the plate has been melted.
        """
        env = 0.80 * np.exp(-0.55 * (nu / max(mmax, 1.0)) ** 2)
        cutoff = 0.5 * (1.0 - np.tanh((nu - mmax) / 0.30))
        ring = env * cutoff * np.sin(np.pi * nu) ** 2
        ring *= 0.5 * (1.0 + np.tanh((nu - self.hidden) / 0.55))
        rim = 0.95 * np.exp(-((nu - mmax) / 0.55) ** 2)
        return ring + rim

    def pattern(self, L_cm, X, Y, current_mA, lit):
        """
        Intensity on the screen for the given cm grid.

        Two apertures are superposed: the thermal bump, and - once the
        plate has been past its yield point - the narrower frozen crater,
        whose rings therefore sit at wider angles and reach further out.
        Both are lit by the same beam, so both scale with the drive.
        """
        ca, sa = math.cos(self.tilt), math.sin(self.tilt)
        Xr = X * ca + Y * sa
        Yr = -X * sa + Y * ca
        Rr = np.sqrt((Xr / self.ellipticity) ** 2
                     + (Yr * self.ellipticity) ** 2)
        sin_a = Rr / np.sqrt(Rr * Rr + L_cm * L_cm)
        nu = self.R_base_lam * sin_a
        # No branch on the amplitude: intensity() already collapses to the
        # bare central spot when the bump is small, because the hidden
        # order factor suppresses everything below order two.  Switching
        # between two formulae at m = 0.4 made the pattern jump as the
        # knob crossed the threshold.
        img = self.intensity(nu, self.m_th)
        if self.m_pl > 0.4:
            nu_p = self.R_base_lam * self.sec_ratio * sin_a
            img = img + self.SEC_BRIGHT * self.crater(nu_p, self.m_pl)
        # brightness follows the drive: below the fringe threshold the
        # knob still does something visible, as it does on the bench
        P = self.power_true(current_mA) if lit else 0.0
        img = img * min(max(P / 300.0, 0.0), 1.6)
        if self.dirty > 0.25:
            img = img * (1.0 + 0.05 * self.dirty
                         * np.cos(4.0 * np.arctan2(Yr, Xr)))
        return np.clip(img, 0.0, 1.6)

    def goto_spot(self, key):
        """
        The adjustable stand slides the plate across the beam.  Every spot
        on that plate keeps its own history: the crater melted into one
        shot is still there when you wind the stand back to it, while a
        fresh shot starts with a flat surface.  The thermal bump does not
        travel with the stand - it belongs to wherever the beam is now.
        """
        if not hasattr(self, "spots"):
            self.spots = {}
        self.spots[self.spot_key] = (self.m_pl, self.R_base_lam,
                                     self.sec_ratio)
        self.spot_key = key
        self.m_th = 0.0
        if key in self.spots:
            (self.m_pl, self.R_base_lam, self.sec_ratio) = self.spots[key]
        else:
            self.m_pl = 0.0
            self.R_base_lam = R_BASE_LAMBDA * (1.0
                                               + self.rng.gauss(0.0, 0.015))
            self.sec_ratio = self.SEC_RADIUS * (1.0
                                                + self.rng.gauss(0.0, 0.03))

    def fresh_spot(self):
        self.goto_spot((self.spot_key[0] + 1, self.spot_key[1]))



def png_photo(rgb):
    """
    numpy uint8 (h, w, 3) or (h, w, 4)  ->  tk.PhotoImage, with no image
    library at all.  Tk 8.6 reads PNG natively, including the alpha of a
    colour-type-6 image, so a minimal encoder is enough: IHDR, one IDAT
    with filter byte 0 in front of every scan line, IEND.

    Compression level 1 rather than 6: this is a throw-away buffer handed
    straight to Tk, never a file, and on a 490 x 490 pattern level 6 cost
    more time than computing the pattern did.
    """
    h, w = rgb.shape[:2]
    nc = rgb.shape[2] if rgb.ndim == 3 else 1
    ctype = {1: 0, 3: 2, 4: 6}[nc]

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff))

    raw = np.concatenate(
        [np.zeros((h, 1), dtype=np.uint8), rgb.reshape(h, w * nc)],
        axis=1).tobytes()
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 1))
           + chunk(b"IEND", b""))
    return tk.PhotoImage(data=base64.b64encode(png))


LASER_STOPS = ((0.00, (0, 0, 0)), (0.18, (42, 0, 0)), (0.40, (139, 0, 8)),
               (0.62, (224, 16, 32)), (0.82, (255, 90, 85)),
               (1.00, (255, 233, 230)))


def _build_lut(n=2048):
    """The colour ramp, sampled once into a table."""
    x = np.linspace(0.0, 1.0, n)
    out = np.zeros((n, 3), dtype=np.float32)
    for (a, ca), (b, cb) in zip(LASER_STOPS[:-1], LASER_STOPS[1:]):
        m = (x >= a) & (x <= b)
        f = (x[m] - a) / (b - a)
        for c in range(3):
            out[m, c] = ca[c] + f * (cb[c] - ca[c])
    return out.astype(np.uint8)


LASER_LUT = _build_lut()


def laser_rgb(img, vmax=1.35):
    """
    Map the intensity array to the deep red of a 650 nm diode pattern.

    One table lookup per pixel instead of five masked passes over the
    whole array; the table is sampled finely enough that the result is
    the same 8 bit colour.
    """
    n = LASER_LUT.shape[0]
    idx = np.clip(img * ((n - 1) / vmax), 0, n - 1).astype(np.int32)
    return LASER_LUT[idx]


# ==========================================================================
#  THE OPTICAL BENCH  (Figure 1a of the question sheet)
# ==========================================================================
class BenchCanvas(tk.Canvas):
    """
    Side view of the rail.  Laser on the right, semi transparent screen with
    the hole in the middle, PMMA target on the left.  Drag the screen or the
    target along the rail; the distance L that you must quote in task A.2 is
    the target to screen distance and it is yours to read off the rail scale.
    """

    W, H = 560, 434

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#e9e7e2",
                         highlightthickness=1, highlightbackground="#999",
                         **kw)
        self.app = app
        self.drag = None
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.redraw()

    RAIL = 100.0                    # cm of rail
    GAP_LS = 8.0                    # laser head to screen, minimum
    GAP_TS = 5.0                    # target to screen, minimum

    # The rail carries three carriers, and all three slide: on the bench
    # the laser sits in a carrier of exactly the same pattern as the
    # screen and the target, clamped into the T slot with a knurled
    # screw, and the instructions have the candidate place all three of
    # them.  It used to be bolted to one spot here, which it is not.
    def _px(self, cm):
        return 40 + cm * (self.W - 90) / self.RAIL

    def _cm(self, px):
        return (px - 40) * self.RAIL / (self.W - 90)

    def _press(self, ev):
        for name, cm in (("laser", self.app.x_laser),
                         ("screen", self.app.x_screen),
                         ("target", self.app.x_target)):
            # down to the rail, so the stand and its carrier can be
            # grabbed as well as the head
            if abs(ev.x - self._px(cm)) < 16 and 60 < ev.y < 300:
                self.drag = name
                return

    def _motion(self, ev):
        if not self.drag:
            return
        # up and down on the post as well as along the rail: the thumb
        # screw on every carrier lets the stand rise and fall
        z = max(Z_MIN, min(Z_MAX, Z_NOM - (ev.y - 190) / 1.15))
        setattr(self.app, "z_" + self.drag, z)
        cm = max(0.0, min(self.RAIL, self._cm(ev.x)))
        if self.drag == "laser":
            # it has to stay behind the screen, or its own beam would
            # never reach the hole
            self.app.x_laser = max(cm, self.app.x_screen + self.GAP_LS)
        elif self.drag == "screen":
            # the screen sits between the target and the laser
            self.app.x_screen = min(max(cm, self.app.x_target + self.GAP_TS),
                                    self.app.x_laser - self.GAP_LS)
        else:
            self.app.x_target = min(cm, self.app.x_screen - self.GAP_TS)
        self.app.on_geometry(self.drag)
        self.redraw()

    def _plate_views(self, x0, y0):
        """
        The PMMA plate itself, not a graph: the face you shoot at, and the
        same plate seen edge on so the swelling of the surface can be
        judged.  The bump is a few wavelengths high on a 3 mm plate, so
        the edge view is drawn with the surface relief exaggerated and the
        magnification is stated on the drawing.
        """
        m = self.app.model
        h = m.height_lambda()            # thermal bump plus frozen crater
        hot = h > 0.05

        # The bump is a few tens of wavelengths high on a 3 mm plate, so
        # on a life-size drawing of the whole plate it is a third of a
        # pixel and genuinely invisible.  The edge view therefore shows a
        # 0.25 mm square of the surface itself, at a stated scale, where a
        # strongly heated spot does show a very slight swelling.
        SLICE_M = 250e-6                          # what the edge view spans
        h_m = h * LAMBDA
        rise = min(h_m / SLICE_M * 60.0, 34.0)    # px, 60 px = 0.25 mm
        base = self.app.model.R_base_lam * LAMBDA / SLICE_M * 60.0

        # ---- the plate, seen face on ---------------------------------
        self.create_rectangle(x0 - 30, y0 - 30, x0 + 30, y0 + 30,
                              fill="#dff0f5", outline="#7fa3ad", width=2)
        # at life size the irradiated spot is a speck of scattered light
        self.create_oval(x0 - 2, y0 - 2, x0 + 2, y0 + 2,
                         fill="#ff9a3c" if hot else "#d9c4b0", outline="")
        self.create_text(x0, y0 + 42, text="PMMA, 정면",
                         fill="#5c6169", font=("TkDefaultFont", 7))

        # ---- the same plate, seen edge on ----------------------------
        ex, ey = x0 + 128, y0
        # the laser comes from the right, so the right face is the one
        # that swells
        half = max(base, 6.0)
        pts = [ex - 22, ey - 30, ex - 22, ey + 30]
        for k in range(61):
            u = 1.0 - k / 30.0
            pts += [ex + 22 + rise * math.exp(-((u * 30.0 / half) ** 2)),
                    ey + 30 * u]
        self.create_polygon(*pts, fill="#dff0f5", outline="#7fa3ad",
                            width=2)
        self.create_line(ex + 22, ey - 30, ex + 22, ey + 30,
                         fill="#b7ced6", dash=(3, 3))
        self.create_text(ex, ey + 42, text="PMMA 표면, 0.25 mm",
                         fill="#5c6169", font=("TkDefaultFont", 7))
        self.create_text(x0 - 44, ey, text="실물\n크기",
                         fill="#8b8f96", font=("TkDefaultFont", 7))


    def _py(self, z_mm):
        """Height on a post, in mm of travel, to a canvas row."""
        return 190 - (z_mm - Z_NOM) * 1.15

    def _stand(self, x, y_top, yb):
        """Post and carrier under any of the three stands."""
        self.create_rectangle(x - 15, yb - 10, x + 15, yb + 6,
                              fill="#4a4f55", outline="#2f343a")
        self.create_oval(x + 10, yb - 7, x + 21, yb + 4,
                         fill="#b6bcc4", outline="#7d848c")
        self.create_rectangle(x - 5, y_top, x + 5, yb - 8,
                              fill="#8b9096", outline="#5c6169")
        self.create_rectangle(x - 11, y_top - 5, x + 11, y_top + 6,
                              fill="#5c6169", outline="#2f343a")

    def redraw(self):
        self.delete("all")
        yb = 290
        self.create_rectangle(24, yb, self.W - 24, yb + 16, fill="#b9bcc2",
                              outline="#8b8f96")
        for cm in range(0, int(self.RAIL) + 1, 5):
            x = self._px(cm)
            self.create_line(x, yb, x, yb - 6, fill="#6b7076")
            self.create_text(x, yb - 13, text="%d" % cm, fill="#6b7076",
                             font=("TkDefaultFont", 7))
        self.create_text(self.W - 28, yb + 26, text="광학대, cm",
                         anchor="e", fill="#6b7076",
                         font=("TkDefaultFont", 7))

        xs = self._px(self.app.x_screen)
        xt = self._px(self.app.x_target)
        xl = self._px(self.app.x_laser)
        beam_y = 190
        # each post carries its own height, so the three no longer share
        # one line: this is what the candidate has to set
        yl = self._py(self.app.z_laser)
        ys_ = self._py(self.app.z_screen)
        yt = self._py(self.app.z_target)
        path = self.app.beam_path()

        # The laser head on its stand.  The post used to stop 47 px short
        # of the head, which left the laser hanging in mid air; it now
        # runs from the head down to a carrier of the same pattern as the
        # ones under the screen and the target, with its clamping screw.
        self._stand(xl, yl + 13, yb)
        self.create_rectangle(xl - 26, yl - 13, xl + 30, yl + 13,
                              fill="#4a5059", outline="#2f343a")
        self.create_rectangle(xl - 34, yl - 6, xl - 26, yl + 6,
                              fill="#2f343a", outline="")
        self.create_text(xl + 2, yl - 22, text="레이저", fill="#4a5059",
                         font=("TkDefaultFont", 8))

        # semi transparent screen with the hole
        self._stand(xs, ys_ + 88, yb)
        self.create_rectangle(xs - 3, ys_ - 96, xs + 3, ys_ + 88,
                              fill="#dcdcd4", outline="#9a9a92")
        self.create_rectangle(xs - 4, ys_ - 5, xs + 4, ys_ + 5,
                              fill="#e9e7e2", outline="")
        self.create_text(xs, ys_ - 104, text="스크린 (구멍)",
                         fill="#5c6169", font=("TkDefaultFont", 8))

        # PMMA target on its magnetic holder
        # the plate had a 6 px gap under it and no carrier at all, so it
        # floated the way the laser did
        self._stand(xt, yt + 60, yb)
        self.create_rectangle(xt - 5, yt - 60, xt + 5, yt + 60,
                              fill="#cfe0e6", outline="#7fa3ad", width=2)
        self.create_text(xt, yt - 72, text="PMMA 시료", fill="#4d707a",
                         font=("TkDefaultFont", 8))

        if self.app.emitting():
            bw = 1 + int(3.0 * min(self.app.model.power_true(self.app.cur)
                                   / 380.0, 1.0))
            if path == "blocked":
                # it stops on the back of the screen, and the spot shows
                # through: that red dot is how you find the hole
                self.create_line(xl - 26, yl, xs + 3, yl, fill="#e02020",
                                 width=bw)
                self.create_oval(xs - 2, yl - 4, xs + 8, yl + 4,
                                 fill="#ff5040", outline="")
            else:
                self.create_line(xl - 26, yl, xt + 5, yl, fill="#e02020",
                                 width=bw)
                if path == "ok":
                    for dy in (-1, 1):
                        self.create_line(xt + 5, yl, xs - 3,
                                         ys_ + dy * 78, fill="#e02020",
                                         width=1)
        # the distance the student has to quote
        self.create_line(xt, beam_y + 72, xs, beam_y + 72, fill="#30507a",
                         arrow="both")
        # above the arrow: below it the label sat on top of the rail
        # graduations and neither could be read
        self.create_text((xt + xs) / 2, beam_y + 62, text="L",
                         fill="#30507a", font=("TkDefaultFont", 9, "bold"))
        self.create_text(12, 14, text="레이저·스크린·시료를 레일 위에서 끌어 옮기고, 위아래로 끌어 높이를 맞추세요", anchor="w", fill="#8b8f96",
                         font=("TkDefaultFont", 8))
        self._plate_views(100, 360)


# ==========================================================================
#  THE CONTROL BOX AND THE TWO MULTIMETERS
# ==========================================================================
class ControlCanvas(tk.Canvas):
    W, H = 560, 210

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#e9e7e2",
                         highlightthickness=0, **kw)
        self.app = app
        self.knob_a = 0.0
        self.bind("<Button-1>", self._click)
        self.bind("<MouseWheel>", lambda e: self._turn(1 if e.delta > 0
                                                       else -1))
        self.bind("<Button-4>", lambda e: self._turn(+1))
        self.bind("<Button-5>", lambda e: self._turn(-1))
        self.redraw()

    KX, KY, KR = 150, 108, 34
    SX, SY, SW, SH = 40, 78, 62, 30

    def _click(self, ev):
        if (self.SX <= ev.x <= self.SX + self.SW
                and self.SY <= ev.y <= self.SY + self.SH):
            self.app.toggle_power()
            return
        if math.hypot(ev.x - self.KX, ev.y - self.KY) <= self.KR + 5:
            if math.hypot(ev.x - self.KX, ev.y - self.KY) < 11:
                self.app.fine = not self.app.fine
                self.redraw()
                return
            self._turn(1 if ev.x > self.KX else -1)

    def _turn(self, s):
        """
        Turn the current dial one detent.

        The pointer only moves if the current actually moved with it.
        This is a potentiometer with end stops: once it is wound down to
        zero or up against the limit of the control box it will not go
        any further in that direction, and the knob does not carry on
        rotating while nothing changes.
        """
        before = self.app.cur
        self.app.set_current(before + s * (0.1 if self.app.fine else 1.0))
        if self.app.cur != before:
            self.knob_a += s * 0.35
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.create_rectangle(20, 30, 300, 190, fill="#2f6fa8",
                              outline="#1d4a72", width=2)
        self.create_text(30, 44, text="컨트롤 박스", anchor="w",
                         fill="#dbe8f4", font=("TkDefaultFont", 9, "bold"))
        on = self.app.on              # the switch, not the lamp
        self.create_rectangle(self.SX, self.SY, self.SX + self.SW,
                              self.SY + self.SH,
                              fill="#3fbf5f" if on else "#8b3030",
                              outline="#123", width=2)
        self.create_text(self.SX + self.SW / 2, self.SY + self.SH / 2,
                         text="ON" if on else "OFF", fill="#ffffff",
                         font=("TkDefaultFont", 9, "bold"))
        self.create_text(self.SX + self.SW / 2, self.SY - 10, text="전원",
                         fill="#dbe8f4", font=("TkDefaultFont", 7))

        x, y, r = self.KX, self.KY, self.KR
        self.create_oval(x - r, y - r, x + r, y + r, fill="#d9dde2",
                         outline="#8b8f96", width=2)
        self.create_oval(x - 10, y - 10, x + 10, y + 10, fill="#b6bcc4",
                         outline="#8b8f96")
        a = self.knob_a
        self.create_line(x + (r - 6) * math.sin(a), y - (r - 6) * math.cos(a),
                         x + 10 * math.sin(a), y - 10 * math.cos(a),
                         fill="#c02020", width=3)
        self.create_text(x, y + r + 12, text="CURRENT  Adjust",
                         fill="#dbe8f4", font=("TkDefaultFont", 8))
        self.create_text(x, y + r + 24,
                         text="fine step" if self.app.fine else "coarse step",
                         fill="#a9c4dc", font=("TkDefaultFont", 7))
        self.create_text(232, 76, text="LASER", fill="#dbe8f4",
                         font=("TkDefaultFont", 8))
        self.create_oval(222, 86, 242, 106,
                         fill="#ff4030" if self.app.emitting()
                         else "#603030", outline="#123")
        self.create_text(232, 120, text="DC 12 V", fill="#dbe8f4",
                         font=("TkDefaultFont", 7))

        i, v = self.app.reading
        for k, (lab, val, unit) in enumerate((("DC mA", i, "mA"),
                                              ("DC V", v, "V"))):
            X = 330 + k * 118
            self.create_rectangle(X, 30, X + 104, 190, fill="#b5443f",
                                  outline="#7d2b28", width=2)
            self.create_rectangle(X + 10, 46, X + 94, 86, fill="#101810",
                                  outline="#0a0d0a")
            if val is None:
                txt = "  . "                 # nothing connected
            else:
                txt = ("%.1f" % val) if unit == "mA" else ("%.2f" % val)
            self.create_text(X + 88, 66, text=txt, anchor="e",
                             fill="#7dff9d", font=("Consolas", 15, "bold"))
            self.create_text(X + 52, 98, text=lab, fill="#f3dedd",
                             font=("TkDefaultFont", 8, "bold"))
            self.create_oval(X + 40, 120, X + 64, 144, fill="#8d3733",
                             outline="#5c1f1c")
            self.create_text(X + 52, 176, text="멀티미터", fill="#f3dedd",
                             font=("TkDefaultFont", 7))


# ==========================================================================
#  THE SCREEN
# ==========================================================================
class Ruler:
    """
    The 30 cm clear plastic ruler from the apparatus list.

    It is an object lying on the screen, not a read-out: drag it where
    you want it, roll the wheel over it to swing it round, and read the
    fringe positions off its own millimetre scale with your own eyes.
    Nothing anywhere prints a radius for you.
    """
    LEN = 30.0          # cm, the printed scale runs 0 .. 30
    WID = 3.0           # cm across
    TRANS = 0.86        # two air/acrylic surfaces, about 8% lost at each

    def __init__(self):
        self.x = 0.0            # cm, centre of the ruler on the screen
        self.y = 13.0
        self.ang = 0.0          # radians, 0 = lying along x

    def local(self, X, Y):
        """Screen cm -> ruler cm (u along the scale, v across it)."""
        ca, sa = math.cos(-self.ang), math.sin(-self.ang)
        dx, dy = X - self.x, Y - self.y
        return dx * ca - dy * sa, dx * sa + dy * ca

    def contains(self, X, Y):
        u, v = self.local(X, Y)
        return abs(u) <= self.LEN / 2 and abs(v) <= self.WID / 2

    def bbox(self):
        """Screen-cm bounding box of the rotated ruler."""
        hu, hv = self.LEN / 2, self.WID / 2
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        xs, ys = [], []
        for su in (-1, 1):
            for sv in (-1, 1):
                xs.append(self.x + su * hu * ca - sv * hv * sa)
                ys.append(self.y + su * hu * sa + sv * hv * ca)
        return min(xs), min(ys), max(xs), max(ys)

    def render(self, u, v, I):
        """
        What the ruler looks like lying on the screen, as colour.

        Clear acrylic transmits most of the light and reflects the rest,
        so the fringes stay visible through it but dimmed - that part is
        still the laser's own deep red.  What the ruler itself shows is
        not: the two bevelled edges pipe light along their length and the
        engraved graduations scatter it, and both come back neutral, the
        way they do on the bench.  So the plastic is composited as colour
        rather than as intensity, and a fringe under the scale can still
        be lined up against a millimetre mark.
        """
        rgb = laser_rgb(np.clip(I * self.TRANS, 0.0, 1.6)).astype(np.float32)

        # a faint grey veil over the whole body
        rgb += np.array([11.0, 13.0, 17.0], dtype=np.float32)

        # the lit edges
        edge = np.exp(-((np.abs(v) - self.WID / 2) / 0.085) ** 2)
        rgb += edge[..., None] * np.array([54.0, 62.0, 72.0],
                                          dtype=np.float32)

        return np.clip(rgb, 0, 255).astype(np.uint8)

    def ticks(self):
        """
        The engraved millimetre scale, as line segments in screen cm.

        These are drawn rather than sampled into the image: a millimetre
        is only about 1.2 screen pixels wide, so putting the marks into
        the pixel grid turned them into an aliased hash instead of a
        scale you could read against.
        """
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        half = self.WID / 2
        out = []
        for k in range(0, 301):
            u = k * 0.1 - self.LEN / 2
            tl = 0.66 if k % 10 == 0 else (0.42 if k % 5 == 0 else 0.22)
            v0, v1 = half, half - tl
            out.append((self.x + u * ca - v0 * sa,
                        self.y + u * sa + v0 * ca,
                        self.x + u * ca - v1 * sa,
                        self.y + u * sa + v1 * ca,
                        k % 10 == 0, k % 5 == 0))
        return out


class ScreenCanvas(tk.Canvas):
    W, H = 560, 560
    HALF = 20.0                     # cm shown from the centre

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#20211f",
                         highlightthickness=0, **kw)
        self.app = app
        self.img = None
        self.rul = Ruler()
        self._drag = None
        self._geo_key = None
        self._pat_key = None
        self._I = None
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.bind("<MouseWheel>", lambda e: self._spin(1 if e.delta > 0
                                                       else -1))
        self.bind("<Button-4>", lambda e: self._spin(+1))
        self.bind("<Button-5>", lambda e: self._spin(-1))
        self.redraw()

    # The image spans exactly the pixels the geometry does.  The desktop
    # program used to blow a 420 point grid up with PhotoImage.zoom(2),
    # which put the pattern on the glass at 21 px/cm while every length
    # in the model was 12.25 px/cm, so anything measured off it came out
    # 1.714 times too small.  NPIX is that span, and there is no zoom.
    NPIX = 490

    def _px(self, cm):
        return self.W / 2 + cm * (self.W - 70) / (2 * self.HALF)

    def _cm(self, px):
        return (px - self.W / 2) * 2 * self.HALF / (self.W - 70)

    # ---------------- mouse ----------------
    def _press(self, ev):
        X, Y = self._cm(ev.x), self._cm(ev.y)
        if self.rul.contains(X, Y):
            self._drag = (X - self.rul.x, Y - self.rul.y)

    def _motion(self, ev):
        if self._drag is None:
            return
        X, Y = self._cm(ev.x), self._cm(ev.y)
        self.rul.x = X - self._drag[0]
        self.rul.y = Y - self._drag[1]
        self.redraw()

    def _spin(self, s):
        """Swing the ruler round, so it can be laid across a diameter."""
        self.rul.ang += s * math.radians(2.0)
        self.redraw()

    # ---------------- the pattern ----------------
    def _geometry(self):
        """
        Everything that depends only on the grid and on the plate's own
        tilt and ellipticity, worked out once and kept.
        """
        m = self.app.model
        key = (m.tilt, m.ellipticity, m.dirty, self.NPIX)
        if self._geo_key == key:
            return
        n = self.NPIX
        ax = np.linspace(-self.HALF, self.HALF, n, dtype=np.float32)
        X, Y = np.meshgrid(ax, ax)
        ca, sa = math.cos(m.tilt), math.sin(m.tilt)
        Xr = X * ca + Y * sa
        Yr = -X * sa + Y * ca
        self._X, self._Y = X, Y
        self._Rr = np.sqrt((Xr / m.ellipticity) ** 2
                           + (Yr * m.ellipticity) ** 2).astype(np.float32)
        # the four-fold ripple from surface contamination
        self._theta = (1.0 + 0.05 * m.dirty
                       * np.cos(4.0 * np.arctan2(Yr, Xr))).astype(np.float32) \
            if m.dirty > 0.25 else None
        # the speckle is drawn from a fixed seed, so it is the same array
        # every time: there is no reason to draw it again on every frame
        rg = np.random.default_rng(7)
        self._sp1 = rg.random((n, n), dtype=np.float32) - 0.5
        self._sp2 = rg.random((n, n), dtype=np.float32)
        self._geo_key = key

    def _intensity(self):
        """The pattern on the screen, cached against everything it uses."""
        m, app = self.app.model, self.app
        live = app.emitting()
        key = (round(app.cur, 3), round(app.L(), 4), m.spot_key, live,
               round(m.m_th, 4), round(m.m_pl, 4),
               round(m.R_base_lam, 6), round(m.sec_ratio, 5),
               round(app.z_laser, 3), round(app.z_screen, 3),
               round(app.z_target, 3))
        if self._pat_key == key and self._I is not None:
            return self._I
        self._geometry()
        n = self.NPIX
        path = self.app.beam_path()
        if live and path != "ok":
            # the beam never reaches the plate.  If it is stopped by the
            # screen its spot still shows through the translucent sheet,
            # displaced from the hole by exactly the height error - which
            # is what you steer by when you line the stands up.
            img = np.zeros((n, n), dtype=np.float32)
            if path == "blocked":
                self._geometry()
                dy = -(app.z_laser - app.z_screen) / 10.0
                P = m.power_true(app.cur)
                img = (1.45 * min(max(P / 300.0, 0.0), 1.6)
                       * np.exp(-((self._X ** 2 + (self._Y - dy) ** 2)
                                  / (2.0 * 0.075 ** 2))))
            self._I = np.clip(img, 0.0, 1.6).astype(np.float32)
            self._rgb0 = laser_rgb(self._I)
            self._pat_key = key
            return self._I
        if not live:
            self._I = np.zeros((n, n), dtype=np.float32)
            self._rgb0 = laser_rgb(self._I)
            self._pat_key = key
            return self._I
        P = m.power_true(app.cur)
        L = app.L()
        # sin(arctan2(r, L)) is r / hypot(r, L): the same number without
        # a transcendental pair over a quarter of a million points
        R = self._Rr
        sin_a = (R / np.sqrt(R * R + L * L)).astype(np.float32)
        nu = m.R_base_lam * sin_a
        if m.m_th > 0.4:
            img = m.intensity(nu, m.m_th)
        else:
            img = 1.35 * np.exp(-(nu / 1.55) ** 2)
        # the frozen crater is narrower than the thermal bump, so its
        # rings sit at wider angles: the faint second pattern, with a
        # bright ring well outside the first, that stays behind once the
        # plate has been taken past its yield point
        if m.m_pl > 0.4:
            img = img + m.SEC_BRIGHT * m.crater(
                m.R_base_lam * m.sec_ratio * sin_a, m.m_pl)
        img = img * min(max(P / 300.0, 0.0), 1.6)
        if self._theta is not None:
            img = img * self._theta
        img = img + 0.030 * np.sqrt(np.clip(img, 0.0, None)) * self._sp1 \
            + 0.0015 * self._sp2
        self._I = np.clip(img, 0.0, 1.6).astype(np.float32)
        self._rgb0 = laser_rgb(self._I)
        self._pat_key = key
        return self._I

    # ---------------- painting ----------------
    def redraw(self):
        self.delete("all")
        I = self._intensity()
        n = self.NPIX
        # the clean pattern is coloured once and kept; dragging the ruler
        # only repaints the pixels the ruler actually covers
        rgb = self._rgb0.copy()

        # ---- the ruler, composited into the pixels it covers ----------
        r = self.rul
        x0c, y0c, x1c, y1c = r.bbox()
        i0 = max(int((x0c + self.HALF) / (2 * self.HALF) * (n - 1)) - 1, 0)
        i1 = min(int((x1c + self.HALF) / (2 * self.HALF) * (n - 1)) + 2, n)
        j0 = max(int((y0c + self.HALF) / (2 * self.HALF) * (n - 1)) - 1, 0)
        j1 = min(int((y1c + self.HALF) / (2 * self.HALF) * (n - 1)) + 2, n)
        if i1 > i0 and j1 > j0:
            Xs = self._X[j0:j1, i0:i1]
            Ys = self._Y[j0:j1, i0:i1]
            u, v = r.local(Xs, Ys)
            inside = (np.abs(u) <= r.LEN / 2) & (np.abs(v) <= r.WID / 2)
            if inside.any():
                patch = r.render(u, v, I[j0:j1, i0:i1])
                tgt = rgb[j0:j1, i0:i1]
                rgb[j0:j1, i0:i1] = np.where(inside[..., None], patch, tgt)

        self.img = png_photo(rgb)
        self.create_image(self.W / 2, self.H / 2, image=self.img)

        # the hole the incoming beam goes through
        self.create_oval(self.W / 2 - 5, self.H / 2 - 5, self.W / 2 + 5,
                         self.H / 2 + 5, outline="#8090a0", dash=(2, 2))

        # the printed scale, drawn crisp on top of the plastic
        for (x0, y0, x1, y1, iscm, is5) in r.ticks():
            if max(abs(x0), abs(y0)) > self.HALF:
                continue
            self.create_line(self._px(x0), self._px(y0),
                             self._px(x1), self._px(y1),
                             fill="#eef3f8" if iscm else
                                  ("#d6dee6" if is5 else "#9fadb8"),
                             width=1)

        # the numbers printed on the ruler
        ca, sa = math.cos(r.ang), math.sin(r.ang)
        for cmv in range(0, 31, 5):
            uu = cmv - r.LEN / 2
            vv = r.WID / 2 - 1.02
            X = r.x + uu * ca - vv * sa
            Y = r.y + uu * sa + vv * ca
            if abs(X) > self.HALF or abs(Y) > self.HALF:
                continue
            self.create_text(self._px(X), self._px(Y), text=str(cmv),
                             fill="#dfe6ec", font=("TkDefaultFont", 7),
                             angle=-math.degrees(r.ang))
        # and the maker's mark at the far end, so which way is up is clear
        uu, vv = r.LEN / 2 - 2.6, -r.WID / 2 + 0.75
        X = r.x + uu * ca - vv * sa
        Y = r.y + uu * sa + vv * ca
        if abs(X) <= self.HALF and abs(Y) <= self.HALF:
            self.create_text(self._px(X), self._px(Y), text="cm",
                             fill="#b9c4cd", font=("TkDefaultFont", 7),
                             angle=-math.degrees(r.ang))


# ==========================================================================
#  MAIN APPLICATION
# ==========================================================================
class WiringPage(tk.Canvas):
    """
    Item 4 and 5 of the apparatus list: "connecting wires for laser source
    and power control unit" and "connecting wires for multimeters".

    Nothing lights until the circuit is complete, and the meters only read
    what they are actually connected to:

        adaptor            ->  control box  DC 12V
        control box  L+    ->  ammeter  mA          )
        ammeter  COM       ->  laser  +             )  in series
        laser  -           ->  control box  L-      )
        voltmeter  V       ->  laser  +             )  in parallel
        voltmeter  COM     ->  laser  -             )

    Put the ammeter across the laser instead of in series and the loop is
    broken, exactly as it would be on the bench.
    """

    W, H = 1010, 560
    R = 9
    FACE, BODY, NAVY = "#4fa6dc", "#2e3134", "#16324f"

    def __init__(self, master, app, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#41454a",
                         highlightthickness=1, highlightbackground="#22252a",
                         **kw)
        self.app = app
        self.links = set()
        self.held = None
        self.mouse = (0, 0)
        self.T = {}

        def t(name, x, y, col, lab, side="e", fg="#e6e8ea"):
            self.T[name] = dict(x=x, y=y, col=col, lab=lab, side=side, fg=fg)

        t("adaptor", 150, 470, "#2b6fa8", "", "e")
        t("box_dc", 356, 470, "#2b6fa8", "", "e")
        t("box_lp", 356, 150, "#c02020", "", "e")
        t("box_ln", 356, 250, "#2b2e32", "", "e")
        t("amp_in", 560, 96, "#c02020", "", "e")
        t("amp_com", 560, 176, "#2b2e32", "", "e")
        t("volt_in", 800, 96, "#c02020", "", "e")
        t("volt_com", 800, 176, "#2b2e32", "", "e")
        t("laser_p", 620, 330, "#c02020", "+", "e")
        t("laser_n", 620, 410, "#2b2e32", "\u2212", "e")

        self.ALLOWED = {
            frozenset(("adaptor", "box_dc")),
            frozenset(("box_lp", "amp_in")),
            frozenset(("amp_com", "laser_p")),
            frozenset(("laser_n", "box_ln")),
            frozenset(("volt_in", "laser_p")),
            frozenset(("volt_com", "laser_n")),
            # the classic mistakes, allowed so that they can be made
            frozenset(("box_lp", "laser_p")),
            frozenset(("amp_in", "laser_p")),
            frozenset(("amp_com", "laser_n")),
            frozenset(("volt_in", "box_lp")),
            frozenset(("volt_com", "box_ln")),
        }
        self.MULTI = {"laser_p", "laser_n", "box_lp", "box_ln"}
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
        if 300 <= ev.x <= 360 and 300 <= ev.y <= 350:        # ON / OFF
            self.app.toggle_power()
            return
        k = self._at(ev.x, ev.y)
        if k is not None:
            if self.held is None or self.held == k:
                self.held = None if self.held == k else k
            elif frozenset((self.held, k)) in self.ALLOWED:
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

    # ---- what the wiring means ---------------------------------------
    def state(self):
        powered = self.linked("adaptor", "box_dc")
        series = (self.linked("box_lp", "amp_in")
                  and self.linked("amp_com", "laser_p")
                  and self.linked("laser_n", "box_ln"))
        direct = (self.linked("box_lp", "laser_p")
                  and self.linked("laser_n", "box_ln"))
        shorted = self.linked("amp_in", "laser_p") \
            and self.linked("amp_com", "laser_n")
        # the POWER switch is part of the circuit too: with it off the
        # box passes nothing, so no beam anywhere
        on = getattr(self.app, "on", False)
        lit = on and powered and (series or direct) and not shorted
        return dict(powered=powered, lit=lit,
                    amp=series and lit,
                    volt=(self.linked("volt_in", "laser_p")
                          and self.linked("volt_com", "laser_n") and lit),
                    shorted=shorted)

    def _changed(self):
        self.redraw()
        self.app.wiring_changed()

    # ------------------------------------------------------------------
    def _meter(self, x0, y0, title, value, unit, live):
        self.create_rectangle(x0, y0, x0 + 210, y0 + 190, fill="#b5443f",
                              outline="#7d2b28", width=2)
        self.create_rectangle(x0 + 16, y0 + 22, x0 + 194, y0 + 74,
                              fill="#101810", outline="#0a0d0a")
        self.create_text(x0 + 186, y0 + 48, anchor="e",
                         text=(value if live else "  . "),
                         fill="#7dff9d", font=("Consolas", 17, "bold"))
        self.create_text(x0 + 105, y0 + 92, text=title, fill="#f3dedd",
                         font=("TkDefaultFont", 9, "bold"))
        self.create_oval(x0 + 80, y0 + 108, x0 + 130, y0 + 158,
                         fill="#8d3733", outline="#5c1f1c", width=2)
        self.create_text(x0 + 105, y0 + 133, text=unit, fill="#f3dedd",
                         font=("TkDefaultFont", 8, "bold"))

    def redraw(self):
        self.delete("all")
        st = self.state()
        i, v = self.app.reading

        self.create_rectangle(300, 60, 420, 520, fill=self.BODY,
                              outline="#1b1d1f", width=2)
        self.create_rectangle(312, 74, 408, 506, fill=self.FACE,
                              outline="#3d8ec0")
        self.create_text(320, 100, text="\u25c4 LASER +", anchor="w",
                         fill="#c02020", font=("TkDefaultFont", 8, "bold"))
        self.create_text(320, 214, text="\u25c4 LASER \u2212", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 8, "bold"))
        self.create_oval(346, 118, 374, 146,
                         fill="#ff4030" if self.app.emitting()
                         else "#603030",
                         outline="#7a1218")
        self.create_rectangle(300, 300, 360, 350,
                              fill="#3fbf5f" if self.app.on else "#8b3030",
                              outline="#123", width=2)
        self.create_text(330, 325, text="ON" if self.app.on else "OFF",
                         fill="#ffffff", font=("TkDefaultFont", 9, "bold"))
        self.create_text(330, 364, text="전원", fill=self.NAVY,
                         font=("TkDefaultFont", 7, "bold"))
        self.create_text(320, 440, text="\u25c4 DC 12V", anchor="w",
                         fill=self.NAVY, font=("TkDefaultFont", 8, "bold"))
        self.create_text(360, 490, text="컨트롤 박스", fill=self.NAVY,
                         font=("TkDefaultFont", 8, "bold"))

        self.create_rectangle(96, 446, 180, 494, fill="#3b3f44",
                              outline="#1b1d1f", width=2)
        self.create_rectangle(104, 454, 148, 466, fill="#d8dade", outline="")
        self.create_text(138, 512, text="어댑터  7", fill="#c9ccd1",
                         font=("TkDefaultFont", 8))

        self._meter(452, 60, "직류 전류",
                    "%.1f" % i if i is not None else "", "mA", st["amp"])
        self._meter(692, 60, "직류 전압",
                    "%.2f" % v if v is not None else "", "V", st["volt"])

        self.create_rectangle(560, 330, 700, 412, fill="#7d848c",
                              outline="#4a4f55", width=2)
        self.create_rectangle(700, 356, 730, 386, fill="#2b2e32",
                              outline="#1b1d1f")
        self.create_text(630, 434, text="레이저 다이오드 헤드  1", fill="#c9ccd1",
                         font=("TkDefaultFont", 8))
        if self.app.emitting():
            bw = 1 + int(4.0 * min(self.app.model.power_true(self.app.cur)
                                   / 380.0, 1.0))
            self.create_line(730, 371, 800, 371, fill="#ff5040", width=bw)

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
                self.create_text(d["x"] + 16, d["y"], text=d["lab"],
                                 anchor="w", fill=d["fg"],
                                 font=("TkDefaultFont", 9, "bold"))
        if st["shorted"]:
            self.create_text(505, 536, text="전류계가 레이저에 병렬로 물려 단락되었습니다",
                             fill="#ff9090", font=("TkDefaultFont", 9, "bold"))
        self.create_text(20, 24, anchor="w", fill="#aeb4ba",
                         font=("TkDefaultFont", 8),
                         text="단자를 클릭한 뒤 연결할 단자를 클릭하세요. 리드를 클릭하면 빠지고, 우클릭하면 취소됩니다.")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x880")
        self.seed = random.randrange(1, 10 ** 9)
        self.rng = random.Random(self.seed)
        self.model = ThermoModel(self.rng)

        self.on = False
        self.lit = False
        self.cur = 40.0
        self.fine = False
        self.reading = (0.0, 0.0)
        self.x_target = 0.0
        self.x_screen = 49.2
        self.x_laser = 72.0
        # each stand comes at whatever height it was left at
        self.z_target = self.rng.uniform(Z_MIN + 5.0, Z_MAX - 5.0)
        self.z_screen = self.rng.uniform(Z_MIN + 5.0, Z_MAX - 5.0)
        self.z_laser = self.rng.uniform(Z_MIN + 5.0, Z_MAX - 5.0)
        self._screen_job = None
        self._t_surface = time.perf_counter()

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="  APhO 2023  –  실험 문제 2  –  열변형 표면에 의한 간섭", font=("TkDefaultFont", 11, "bold")
                  ).pack(side="left", pady=5)
        self.lbl_seed = ttk.Label(top, text="PMMA 판 %d" % self.seed)
        self.lbl_seed.pack(side="right", padx=8)


        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=4, pady=4)
        page_bench = ttk.Frame(self.nb)
        page_wire = ttk.Frame(self.nb)
        self.nb.add(page_bench, text="  광학대와 스크린  ")
        self.nb.add(page_wire, text="  결선  ")
        self.wiring = WiringPage(page_wire, self)
        self.wiring.pack(padx=8, pady=8)
        pw = ttk.PanedWindow(page_bench, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pw)
        pw.add(left, weight=0)
        right = ttk.Frame(pw)
        pw.add(right, weight=1)

        self.bench = BenchCanvas(left, self)
        self.bench.pack(padx=6, pady=6)
        self.ctrl = ControlCanvas(left, self)
        self.ctrl.pack(padx=6, pady=(0, 6))
        st = ttk.LabelFrame(left, text="조절 스탠드")
        row = ttk.Frame(st)
        row.pack(padx=6, pady=4, anchor="w")
        ttk.Label(row, text="판 이동:").pack(side="left",
                                                     padx=(0, 6))
        for dx, dy, lab in ((-1, 0, "\u25c4"), (0, 1, "\u25b2"),
                            (0, -1, "\u25bc"), (1, 0, "\u25ba")):
            ttk.Button(row, text=lab, width=3,
                       command=lambda a=dx, b=dy: self.move_stand(a, b)
                       ).pack(side="left", padx=2)
        self.lbl_spot = ttk.Label(row, text="", font=("Consolas", 9))
        self.lbl_spot.pack(side="left", padx=(10, 0))
        st.pack(fill="x", padx=6, pady=(0, 6))
        note = ttk.LabelFrame(left, text="안내")
        note.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(note, justify="left", wraplength=500, text=(
            "전류 노브는 마우스 휠로 돌리거나 좌우 절반을 클릭하세요.  노브 중앙을 누르면 거친 스텝과 미세 스텝이 바뀝니다.")
                  ).pack(anchor="w", padx=6, pady=4)

        self.screen = ScreenCanvas(right, self)
        self.screen.pack(padx=6, pady=6)
        self.lbl_cur = ttk.Label(
            right, anchor="w", justify="left", wraplength=540,
            text="30 cm 플라스틱 자를 끌어서 무늬 위에 놓고, 자의 눈금으로 "
                 "직접 재세요.  자 위에서 마우스 휠을 굴리면 자가 회전하므로 "
                 "지름을 가로질러 놓을 수 있습니다.  자를 통해서도 무늬는 "
                 "보이지만 조금 어두워집니다.")
        self.lbl_cur.pack(anchor="w", padx=10, pady=(4, 2))

        self.read_meters()

    # ------------------------------------------------------------------
    def emitting(self):
        """Is the diode actually giving light, not merely powered?"""
        return bool(self.lit) and self.cur > I_LASING

    def beam_path(self):
        """
        Where the beam gets to, given how the three stands are set.

        'blocked'  it misses the hole and stops on the screen
        'missed'   it clears the hole but flies past the plate
        'ok'       it reaches the plate and comes back
        """
        if abs(self.z_laser - self.z_screen) > HOLE_R:
            return "blocked"
        if abs(self.z_laser - self.z_target) > PLATE_HALF:
            return "missed"
        return "ok"

    def L(self):
        return self.x_screen - self.x_target

    def start_surface_clock(self):
        self._t_surface = time.perf_counter()
        self.after(70, self._evolve)

    def toggle_power(self):
        # the switch itself always throws - it is a mechanical switch on
        # the box.  Whether anything lights up is decided by the circuit.
        self.on = not self.on
        self.read_meters()
        self.refresh()

    def set_current(self, mA):
        self.cur = max(0.0, min(I_MAX, round(mA, 1)))
        self.read_meters()
        self.refresh()

    def read_meters(self):
        st = self.wiring.state() if hasattr(self, "wiring") else \
            dict(lit=True, amp=True, volt=True)
        if st["lit"]:
            i, v = self.model.read_meters(self.cur)
        else:
            i, v = 0.0, 0.0
        # an unconnected meter shows nothing at all, not a zero
        self.reading = (i if st["amp"] else None,
                        v if st["volt"] else None)
        self.lit = bool(st["lit"])

    def wiring_changed(self):
        self.read_meters()
        self.refresh()

    def _page_visible(self, which):
        """Is the cabling page the one on top?"""
        try:
            return (self.nb.index(self.nb.select()) == 1) == (which == "wire")
        except Exception:
            return True

    def on_geometry(self, moved=None):
        """
        A carrier has been dragged.  Sliding the laser changes nothing
        the screen shows - the pattern depends on the distance from the
        target to the screen, not on where the head sits behind it - so
        that case only repaints the bench and leaves the diffraction
        pattern alone.
        """
        if moved == "laser":
            self.bench.redraw()
            return
        self.refresh()

    def move_stand(self, dx, dy):
        """Wind the stand one step; the beam lands on a new part of the
        plate, which may or may not have been melted before."""
        k = self.model.spot_key
        self.model.goto_spot((k[0] + dx, k[1] + dy))
        self.refresh()

    def fresh_spot(self):
        self.model.fresh_spot()
        self.refresh()

    def _spot_label(self):
        k = self.model.spot_key
        self.lbl_spot.config(text="지점 %+d, %+d" % (k[0], k[1]))
        self.lbl_seed.config(text="PMMA 판 %d" % self.seed)

    def refresh(self):
        """
        The cheap panels go now; the screen is the expensive one, so it
        is scheduled.  A wheel spin on the current knob delivers a burst
        of events and rendering the whole pattern for every one of them
        was what made the knob feel like treacle.
        """
        # the cabling page is behind the bench page most of the time, and
        # redrawing a hidden canvas is pure cost
        if hasattr(self, "wiring") and self._page_visible("wire"):
            self.wiring.redraw()
        self.ctrl.redraw()
        self._spot_label()
        self.bench.redraw()
        # Coalesce, but never starve.  This used to cancel the pending
        # repaint and book a new one, so while the wheel was actually
        # turning - events every few milliseconds - the cancel always
        # won and the screen did not repaint once until the hand came
        # off the knob.  Booking only when nothing is pending still
        # collapses a burst into one paint, but guarantees one every
        # frame while the burst lasts.
        if self._screen_job is None:
            self._screen_job = self.after(16, self._paint_screen)

    def _paint_screen(self):
        self._screen_job = None
        self.screen.redraw()

    # ------------------------------------------------------------------
    #  The surface has a clock of its own.
    #
    #  The acrylic does not deform the instant you move the knob: the
    #  beam has to heat it, and the heat has to diffuse.  With PMMA's
    #  diffusivity that takes a couple of seconds to rise and rather
    #  longer to fall, so the pattern grows and shrinks visibly after
    #  every change and does not vanish the moment the laser goes out.
    #  Give it time to settle before you read anything off it.
    # ------------------------------------------------------------------
    def _evolve(self):
        now = time.perf_counter()
        dt = now - self._t_surface
        self._t_surface = now
        m = self.model
        before = (m.m_th, m.m_pl)
        m.step(dt, self.cur, self.emitting())
        if (abs(m.m_th - before[0]) > 2e-3
                or abs(m.m_pl - before[1]) > 2e-3):
            self.bench.redraw()        # the edge view swells with it
            if self._screen_job is None:
                self._screen_job = self.after(1, self._paint_screen)
        self.after(70, self._evolve)

    # There is deliberately no radius read-out.  The apparatus gives you
    # a ruler and a screen; where the fringe falls on the millimetre
    # scale is for you to see and write down.



def main():
    app = App()
    app.start_surface_clock()
    app.mainloop()


if __name__ == "__main__":
    main()
