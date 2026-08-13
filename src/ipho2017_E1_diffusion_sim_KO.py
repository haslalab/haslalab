#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2017 (Yogyakarta) Experimental Problem E1
"Determination of Refractive Index Gradient and Diffusion Coefficient
 of Salt Solution from Laser Deflection Measurement"

Virtual optical bench.

The components are PLACED BY DRAGGING them on the 2D bench picture, exactly
as on the real rail; their positions have to be read off the rail scale.  The
apparatus delivers nothing but what the real one delivers: a laser trace on a
sheet of millimetre paper.  No quantity is computed for the user, and no graph
is drawn - Y_i, (dn/dY)_i, the linearised plot and D are the user's work.

────────────────────────────────────────────────────────────────────────
HOW THE REAL EXPERIMENT RUNS  (problem sheet, "Experimental Procedures")

  1. assemble laser module - diffusion cell - screen on the rail
  2. with the cell empty, focus the laser (rotate its back) and rotate the
     whole laser so that a sharp straight diagonal line appears; trace this
     reference line on the millimetre paper
  3. pour the salt solution into the cell up to the white line
  4. add about 40 drops of distilled water slowly down the side channel,
     then start the stopwatch
  5. adjust Z, Z0 and the laser height so that the deflectogram is centred,
     sharp, and the dip as deep as possible
  6. after 30 minutes trace the deflected line on the millimetre paper
  7. repeat for C0 = 23, 28 and 33 g/150 mL

WHAT THE USER THEN DOES ON PAPER (nothing of this is done by the program)

  A.2  read Z, d, Z0 off the rail and xi_i, delta_i off the millimetre paper
  A.3  Y_i = xi_i Z0/(Z0+d+Z)   and   (dn/dY)_i = delta_i/(Z d)
  A.4  h = Y_i at the maximum of dn/dY
  B.1  ln(dn/dY) = m (h-Y)^2 + C,   m = -1/(4 D t)
  B.3  D from the slope
  C.1  dD/dC from D versus C0

────────────────────────────────────────────────────────────────────────
PHYSICAL MODEL  (equations 1-4 of the sheet)

  xi     = Y (Z0 + d + Z)/Z0
  delta  = Z d (dn/dY)
  dn/dY  = (dn/dC) * C0/(2 sqrt(pi D t)) * exp(-(h-Y)^2/(4 D t))

  The laser is rotated by an angle theta, so the undeflected line on the
  screen makes that angle with the horizontal; the refraction displaces each
  ray vertically only, which is what produces the dip.

CALIBRATION against the official Marking Scheme & Solution

  D is linear in the local concentration C0/2 (part C.1).  A least-squares
  line through the mid-range values of B3, D(23,28,33 g/150 mL) = 1.48, 1.36,
  1.13 (x 1e-5 cm^2/s), gives
        D(C0)     = 2.29e-5 - 5.25e-5 * C0     [cm^2/s], C0 in g/mL
  (slope with respect to C0/2 is -1.05e-4, inside the accepted band
   -4.2e-5 ... -15.8e-5 cm^2 mL g^-1 s^-1 of C1).  Inverting the (dn/dY)_max
  values of A3 with this D gives dn/dC = 0.1392/0.1217/0.1112 mL/g, fitted as
        dn/dC(C0) = 0.2036 - 0.420 * C0        [mL/g]
  With the official geometry (Z0 = 10.4, d = 0.8, Z = 53.4 cm) the dip depth
  after 30 min is then 1.57 / 1.83 / 2.06 cm, i.e. inside the grading windows
  of A1 (1.5-1.6 / 1.7-1.9 / 1.9-2.3 cm).

ERROR MODEL (re-drawn at every pour)
  salt mass +-0.25 g, volume +-1.0 mL, D +-5 %, interface height +-0.6 mm,
  initial mixing layer 20-50 s, stopwatch +-3 s, trace roughness ~0.1 mm.
  Copying the line onto the paper by hand adds a slow wander of about
  0.3 mm rms (a smooth drift, not a jitter), so every traced curve
  differs slightly from the projected one - as a pencil copy does.
────────────────────────────────────────────────────────────────────────
"""

import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ═══════════════════════════ language ═══════════════════════════
LANG = "ko"          # "en" or "ko"

_KO = {
    "Light source module": "광원 모듈",
    "diode laser on": "다이오드 레이저 켜기",
    "focus (rotate the back of the laser)": "초점 (레이저 뒷부분을 돌린다)",
    "rotation of the laser  (angle of the line)": "레이저 회전  (선의 각도)",
    "Solutions": "소금물",
    "/ 150 mL": "/ 150 mL",
    "1.  pour the salt solution up to the white line":
        "1.  소금물을 흰 선까지 붓는다",
    "2.  add ~40 drops of distilled water\n     down the side channel":
        "2.  증류수 약 40방울을\n     옆 통로로 떨어뜨린다",
    "     add a single drop": "     한 방울만 더",
    "%d drops added": "%d방울 넣음",
    "3.  start the stopwatch": "3.  스톱워치를 누른다",
    "empty and rinse the cell": "셀을 비우고 헹군다",
    "Stopwatch": "스톱워치",
    "speed ": "배속 ",
    "(1x while the water goes in)": "(물이 들어가는 동안 1배속)",
    "Millimetre block paper": "밀리미터 방안지",
    "trace the line with a pencil": "연필로 선을 옮겨 그린다",
    "take a fresh sheet": "새 종이를 꺼낸다",
    "save the sheet as PNG": "종이를 PNG로 저장",
    "cursor:  -": "커서:  -",
    "cursor:": "커서:",
    "optical rail  -  drag the components into position":
        "광학 레일  -  부품을 끌어서 배치한다",
    "laser +\ncyl. lens": "레이저 +\n원통 렌즈",
    "cell": "셀",
    "screen": "스크린",
    "millimetre block paper on the screen  (30 x 30 cm, fine 1 mm / bold 1 cm)":
        "스크린 위의 밀리미터 방안지  (30 x 30 cm, 가는 눈금 1 mm / 굵은 눈금 1 cm)",
    "cm": "cm",
    "PNG image": "PNG 이미지",
}

if LANG == "ko":
    # matplotlib walks this list and takes the first family it can find, so
    # the same file works on Windows, macOS and Linux without editing.
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = [
        "Malgun Gothic",        # Windows
        "AppleGothic",          # macOS
        "NanumGothic", "NanumBarunGothic",
        "Noto Sans KR", "Noto Sans CJK KR", "Noto Sans CJK JP",
        "DejaVu Sans",
    ] + matplotlib.rcParams["font.sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def T(s):
    """User-visible text.  Untranslated keys fall through unchanged."""
    return _KO.get(s, s) if LANG == "ko" else s


# ───────────────────────── apparatus ─────────────────────────
RAIL_LEN    = 85.0     # cm, optical rail
SCREEN_SIZE = 30.0     # cm, screen / millimetre paper, 30 x 30 cm
CELL_D      = 0.8      # cm, diffusion cell thickness   (given on the sheet)
CELL_W      = 6.5      # cm, diffusion cell width
CELL_H      = 9.5      # cm, diffusion cell height
CELL_FOOT   = 1.0      # cm, height of the cell holder above the rail
FILL_LINE   = 5.0      # cm, white filling mark above the cell bottom
BENCH_TOP   = 33.0     # cm, top of the bench drawing

LASER_X     = 0.0      # cm, the laser module stays at the zero of the scale
LASER_Y0    = 4.5      # cm, default height of the cylindrical lens
CELL_X0     = 10.4     # cm, default cell position   (official set-up)
SCREEN_X0   = 64.6     # cm, default screen position (official set-up)
SCREEN_Y0   = 15.0     # cm, default height of the screen centre

LASER_Y_RANGE  = (2.5, 8.0)
SCREEN_Y_RANGE = (9.0, 24.0)
CELL_X_RANGE   = (3.0, 40.0)

# ───────────────────────── physics ─────────────────────────
D_A, D_B       = 2.29e-5, -5.25e-5   # D(C0)     [cm^2/s]
DNDC_A, DNDC_B = 0.2036, -0.420      # dn/dC(C0) [mL/g]

SIG_MASS, SIG_VOLUME = 0.25, 1.0     # g, mL
SIG_D_REL   = 0.025                  # D is a property of the solution;
                                     # only the room temperature really moves it
SIG_H       = 0.06                   # cm

# ---- the distilled water is added drop by drop (step 2) ----
#   The problem sheet asks for "about 40 drops of distilled water slowly
#   down the side channel".  That is now done in real time: the student
#   watches the drops land and decides when to stop and start the
#   stopwatch.  The head start of the diffusion is therefore no longer a
#   hidden random number - it is however long the student took.
WDROP_RISE  = 0.075   # cm, rise of the water column per drop
WDROPS_DEFAULT = 40   # "about 40 drops", as the problem sheet asks
WDROP_RATE  = 6.0     # drops per second the pipette can actually deliver
DROP_FALL_G = 600.0   # cm/s^2, visual free fall of a drop
PIPETTE_DY  = 3.0     # cm, height of the pipette tip above the cell rim
SIG_STOP    = 2.0                    # s, when the stopwatch was really zeroed
SIG_ROUGH   = 0.006                  # cm

HAND_OFFSET = 0.010                  # cm, where the pencil is put down
HAND_WANDER = 0.011                  # cm, amplitude of each wander component

N_POINTS    = 2200
PRESET_CONC = [23.0, 28.0, 33.0]     # g / 150 mL


class Pour:
    """One filling of the cell.  All random errors are drawn once."""

    def __init__(self, grams, volume=150.0, seed=None):
        rng = np.random.default_rng(seed)
        self.grams = grams
        mass = grams + rng.normal(0, SIG_MASS)
        vol = volume + rng.normal(0, SIG_VOLUME)
        self.C0 = max(mass, 0.1) / max(vol, 1.0)             # g/mL
        self.D = max((D_A + D_B * self.C0) *
                     (1 + rng.normal(0, SIG_D_REL)), 1e-6)   # cm^2/s
        self.dndC = DNDC_A + DNDC_B * self.C0                # mL/g
        self.dh = rng.normal(0, SIG_H)                       # cm, interface jitter
        self.t_off = rng.normal(0, SIG_STOP)
        self._k = rng.uniform(0.3, 1.8, 6)
        self._p = rng.uniform(0, 2 * np.pi, 6)
        self._a = rng.normal(0, SIG_ROUGH, 6)

    def t_eff(self, t_diff):
        return max(t_diff, 1.0)

    def rough(self, xi):
        out = np.zeros_like(xi)
        for k, p, a in zip(self._k, self._p, self._a):
            out += a * np.sin(k * xi + p)
        return out


# ═══════════════════════════ application ═══════════════════════════
class App:
    def __init__(self, root):
        self.root = root
        root.title("IPhO 2017 E1 - laser deflection diffusion experiment "
                   "(virtual optical bench)")

        # bench state
        self.laser_y = LASER_Y0
        self.cell_x = CELL_X0
        self.screen_x = SCREEN_X0
        self.screen_y = SCREEN_Y0
        self.laser_on = True

        self.pour = None
        self.filled = False          # salt solution poured up to the white line
        self.wlevel = 0.0            # cm, top of the water column above the mark
        self._drops = []             # drops in flight: [y, vy]
        self._drop_acc = 0.0         # drops charged into the pipette
        self._rel_credit = 0.0       # how many it may let go right now
        self.n_drops = 0             # water drops that have landed
        self._t_first = None         # set when the first water drop lands
        self.t_diff = 0.0            # s, true diffusion time since that drop
        self.t_stop0 = None          # t_diff at which the stopwatch was zeroed
        self.started = False         # stopwatch running
        self.t_sim = 0.0
        self.speed = 1.0
        self._speed_locked = False
        self._last = time.perf_counter()

        self.pencil = []             # traced curves on the millimetre paper
        self.drag = None

        self._build_controls()
        self._build_figure()
        self._draw_bench()
        self._draw_paper()
        self._tick()

    # ───────────────────────── controls ─────────────────────────
    def _build_controls(self):
        c = ttk.Frame(self.root, padding=9)
        c.grid(row=0, column=0, sticky="ns")
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        r = 0
        ttk.Label(c, text=T("Light source module"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        self.var_on = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text=T("diode laser on"), variable=self.var_on,
                        command=self._laser_toggle).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("focus (rotate the back of the laser)")).grid(
            row=r, column=0, sticky="w", pady=(6, 0))
        r += 1
        self.var_focus = tk.DoubleVar(value=0.35)
        ttk.Scale(c, from_=0.0, to=1.0, variable=self.var_focus, length=245,
                  orient="horizontal",
                  command=lambda *_: self._redraw_paper()).grid(row=r, column=0,
                                                                sticky="ew")
        r += 1
        ttk.Label(c, text=T("rotation of the laser  (angle of the line)")).grid(
            row=r, column=0, sticky="w", pady=(6, 0))
        r += 1
        self.var_theta = tk.DoubleVar(value=45.0)
        ttk.Scale(c, from_=25.0, to=75.0, variable=self.var_theta, length=245,
                  orient="horizontal",
                  command=lambda *_: self._redraw_paper()).grid(row=r, column=0,
                                                                sticky="ew")
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=8)
        r += 1
        ttk.Label(c, text=T("Solutions"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_conc = tk.StringVar(value="23")
        box = ttk.Frame(c)
        box.grid(row=r, column=0, sticky="w", pady=(2, 4))
        self.conc_btns = []
        for g in PRESET_CONC:
            rb = ttk.Radiobutton(box, text=f"{g:.0f} g", value=f"{g:.0f}",
                                 variable=self.var_conc)
            rb.pack(side="left", padx=(0, 6))
            self.conc_btns.append(rb)
        ttk.Label(box, text=T("/ 150 mL")).pack(side="left")
        r += 1
        self.btn_fill = ttk.Button(c, text=T("1.  pour the salt solution "
                                           "up to the white line"),
                                   command=self.fill)
        self.btn_fill.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        r += 1
        self.btn_water = ttk.Button(
            c, text=T("2.  add ~40 drops of distilled water\n"
                    "     down the side channel"),
            command=self.add_water, state="disabled")
        self.btn_water.grid(row=r, column=0, sticky="ew", pady=(3, 1))
        r += 1
        self.btn_drop = ttk.Button(c, text=T("     add a single drop"),
                                   command=self.one_drop, state="disabled")
        self.btn_drop.grid(row=r, column=0, sticky="ew", pady=(0, 1))
        r += 1
        self.lbl_drops = ttk.Label(c, text=T("     0 drops added"))
        self.lbl_drops.grid(row=r, column=0, sticky="w", pady=(0, 3))
        r += 1
        self.btn_start = ttk.Button(c, text=T("3.  start the stopwatch"),
                                    command=self.start, state="disabled")
        self.btn_start.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        r += 1
        ttk.Button(c, text=T("empty and rinse the cell"),
                   command=self.empty).grid(row=r, column=0, sticky="ew", pady=(2, 2))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=8)
        r += 1
        ttk.Label(c, text=T("Stopwatch"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        disp = tk.Frame(c, bg="#101418", bd=2, relief="sunken")
        disp.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        self.lbl_t = tk.Label(disp, text=T("--:--"), font=("Consolas", 22, "bold"),
                              fg="#8fd6ff", bg="#101418", anchor="e", width=11)
        self.lbl_t.pack(fill="x", padx=8, pady=6)
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 2))
        ttk.Label(row, text=T("speed ")).pack(side="left")
        self.var_speed = tk.StringVar(value="1")
        self.cb_speed = ttk.Combobox(row, textvariable=self.var_speed, width=7,
                                     state="readonly",
                                     values=["1", "10", "30", "60", "120", "300",
                                             "600", "1800"])
        self.cb_speed.pack(side="left")
        self.cb_speed.bind(
            "<<ComboboxSelected>>",
            lambda *_: setattr(self, "speed", float(self.var_speed.get())))
        ttk.Label(row, text=T(" x")).pack(side="left")
        self.lbl_speed_note = ttk.Label(row, text="")
        self.lbl_speed_note.pack(side="left", padx=(6, 0))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=8)
        r += 1
        ttk.Label(c, text=T("Millimetre block paper"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Button(c, text=T("trace the line with a pencil"),
                   command=self.trace).grid(row=r, column=0, sticky="ew", pady=(3, 2))
        r += 1
        ttk.Button(c, text=T("take a fresh sheet"),
                   command=self.fresh_sheet).grid(row=r, column=0, sticky="ew")
        r += 1
        ttk.Button(c, text=T("save the sheet as PNG"),
                   command=self.save_png).grid(row=r, column=0, sticky="ew", pady=(2, 0))
        r += 1
        self.lbl_cur = ttk.Label(c, text=T("cursor:  -"))
        self.lbl_cur.grid(row=r, column=0, sticky="w", pady=(8, 0))
        r += 1
        ttk.Label(c, wraplength=250, foreground="#555",
                  text=(T("Drag the cell and the screen along the rail, and drag "
                        "the laser or the screen up and down.  Read Z0, d and Z "
                        "off the rail scale, and xi_i and delta_i off the "
                        "millimetre grid (fine 1 mm, bold 1 cm).\n"
                        "Diffusion cell:  6.5 x 0.8 x 9.5 cm."))
                  ).grid(row=r, column=0, sticky="w", pady=(6, 0))

    # ───────────────────────── figure ─────────────────────────
    def _build_figure(self):
        self.fig = Figure(figsize=(8.8, 9.6), dpi=96)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.32, 2.2], hspace=0.20)
        self.axb = self.fig.add_subplot(gs[0])
        self.axp = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self.background = None
        self.canvas.mpl_connect("draw_event", self._on_draw)

    # ───────────────────────── geometry ─────────────────────────
    @property
    def Z0(self):
        return self.cell_x - LASER_X

    @property
    def Z(self):
        return self.screen_x - self.cell_x - CELL_D

    @property
    def mag(self):
        return (self.Z0 + CELL_D + self.Z) / max(self.Z0, 1e-3)

    @property
    def h(self):
        """Height of the interface above the optical axis."""
        base = CELL_FOOT + FILL_LINE - self.laser_y
        return base + (self.pour.dh if self.pour else 0.0)

    @property
    def xi_mid(self):
        """xi of the ray that reaches the centre of the screen."""
        return self.screen_y - self.laser_y

    def trace_xy(self):
        """The line as it appears on the paper.  Returns x, y in cm."""
        half = SCREEN_SIZE / 2
        cot = 1.0 / np.tan(np.deg2rad(float(self.var_theta.get())))
        xi = np.linspace(self.xi_mid - half, self.xi_mid + half, N_POINTS)
        x = half + (xi - self.xi_mid) * cot
        y = half + (xi - self.xi_mid)

        if self._t_first is not None and self.pour is not None:
            Y = xi / self.mag
            t = self.pour.t_eff(self.t_diff)
            s = 2.0 * np.sqrt(self.pour.D * t)
            dCdY = self.pour.C0 / (s * np.sqrt(np.pi)) * \
                np.exp(-((self.h - Y) / s) ** 2)
            y = y - self.Z * CELL_D * self.pour.dndC * dCdY + self.pour.rough(xi)
        keep = (x >= -1) & (x <= SCREEN_SIZE + 1)
        return x[keep], y[keep]

    # ───────────────────────── bench drawing ─────────────────────────
    def _draw_bench(self):
        a = self.axb
        a.clear()
        a.set_title(T("optical rail  -  drag the components into position"),
                    fontsize=10)

        # rail with its scale
        a.add_patch(Rectangle((-2, -2.6), RAIL_LEN + 4, 2.6,
                              facecolor="#4a4a4a", edgecolor="#222", zorder=1))
        for t in np.arange(0, RAIL_LEN + 0.01, 1.0):
            big = abs(t % 5) < 1e-6
            a.plot([t, t], [-0.15, -0.15 - (0.85 if big else 0.45)],
                   color="#e8e8e8", lw=0.8 if big else 0.5, zorder=2)
            if big:
                a.text(t, -2.30, f"{t:.0f}", color="#f0f0f0", fontsize=7.5,
                       ha="center", va="bottom", zorder=2)

        # ---- beam ----
        if self.laser_on:
            xs = self.screen_x
            top = self.laser_y + (self.screen_y - self.laser_y) + SCREEN_SIZE / 2
            bot = self.laser_y + (self.screen_y - self.laser_y) - SCREEN_SIZE / 2
            a.add_patch(Polygon([[LASER_X + 1.2, self.laser_y],
                                 [xs, top], [xs, bot]],
                                closed=True, facecolor="#ff3b3b", alpha=0.13,
                                edgecolor="none", zorder=3))
            for f in np.linspace(-1, 1, 7):
                ye = self.screen_y + f * SCREEN_SIZE / 2
                a.plot([LASER_X + 1.2, xs], [self.laser_y, ye],
                       color="#e02020", lw=0.7, alpha=0.55, zorder=3)

        # ---- laser module ----
        a.add_patch(Rectangle((LASER_X - 2.0, self.laser_y - 1.1), 3.2, 2.2,
                              facecolor="#2e3d52", edgecolor="#101820", zorder=5))
        a.add_patch(Rectangle((LASER_X - 2.4, 0.0), 1.4, self.laser_y - 1.1,
                              facecolor="#8a8a8a", edgecolor="#444", zorder=4))
        a.plot([LASER_X, LASER_X], [0.0, self.laser_y + 1.6], ":",
               color="#c8102e", lw=1.0, zorder=6)
        a.plot([LASER_X + 1.2], [self.laser_y], "o", color="#ffd24d",
               ms=5, zorder=6)
        a.text(LASER_X - 2.2, self.laser_y + 2.0, T("laser +\ncyl. lens"),
               fontsize=7, color="#223", ha="left", va="bottom", zorder=6)

        # ---- diffusion cell ----
        cx, cb = self.cell_x, CELL_FOOT
        a.add_patch(Rectangle((cx - 0.9, 0.0), 1.8, cb,
                              facecolor="#8a8a8a", edgecolor="#444", zorder=4))
        a.add_patch(Rectangle((cx, cb), CELL_D, CELL_H,
                              facecolor="#eaf4fb", edgecolor="#31506b",
                              lw=1.3, zorder=5))
        if self.filled:
            a.add_patch(Rectangle((cx, cb), CELL_D, FILL_LINE,
                                  facecolor="#7fb6d8", edgecolor="none",
                                  zorder=5))
        # the water column is a live artist: it is blitted while dripping
        self.art_liq = Rectangle((cx, cb + FILL_LINE), CELL_D,
                                 max(self.wlevel, 0.0),
                                 facecolor="#dff0fa", edgecolor="none", zorder=5)
        self.art_liq.set_visible(self.filled and self.wlevel > 1e-9)
        a.add_patch(self.art_liq)
        if self.filled and self.wlevel > 1e-9:
            a.plot([cx, cx + CELL_D], [cb + FILL_LINE] * 2, "-",
                   color="#2c6f9b", lw=1.0, zorder=6)

        # ---- water pipette and the drops in flight ----
        ptip = cb + CELL_H + PIPETTE_DY
        px = cx + CELL_D / 2
        vis = bool(self._drops) or self.filled and not self.started
        body = Polygon([[px - 0.42, ptip + 3.4], [px + 0.42, ptip + 3.4],
                        [px + 0.42, ptip + 0.7], [px + 0.06, ptip],
                        [px - 0.06, ptip], [px - 0.42, ptip + 0.7]],
                       closed=True, facecolor="#dfe8ee",
                       edgecolor="#5c6b76", lw=1.0, zorder=8)
        fluid = Rectangle((px - 0.36, ptip + 0.8), 0.72, 2.2,
                          facecolor="#cfe9f6", edgecolor="none", zorder=9)
        for art in (body, fluid):
            art.set_visible(vis)
            a.add_patch(art)
        (self.art_drops,) = a.plot([], [], "o", color="#8fcbe8",
                                   ms=3.4, zorder=9)
        a.plot([cx - 0.35, cx + CELL_D + 0.35], [cb + FILL_LINE] * 2, "-",
               color="#ffffff", lw=1.6, zorder=6)
        a.text(cx + CELL_D + 0.6, cb + CELL_H, T("cell"), fontsize=7,
               va="top", zorder=6)

        # ---- screen ----
        sx, sy = self.screen_x, self.screen_y
        a.add_patch(Rectangle((sx - 0.9, 0.0), 1.8, sy - SCREEN_SIZE / 2,
                              facecolor="#8a8a8a", edgecolor="#444", zorder=4))
        a.add_patch(Rectangle((sx, sy - SCREEN_SIZE / 2), 0.7, SCREEN_SIZE,
                              facecolor="#fbfbf4", edgecolor="#555",
                              lw=1.2, zorder=6))
        a.text(sx + 1.2, sy + SCREEN_SIZE / 2, T("screen"), fontsize=7,
               va="top", zorder=6)

        a.set_xlim(-5, RAIL_LEN + 6)
        a.set_ylim(-3.2, BENCH_TOP)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)
        self.background = None
        self.canvas.draw_idle()

    # ───────────────────────── paper drawing ─────────────────────────
    def _draw_paper(self):
        a = self.axp
        a.clear()
        a.set_title(T("millimetre block paper on the screen  "
                    "(30 x 30 cm, fine 1 mm / bold 1 cm)"), fontsize=10)
        a.set_xlim(0, SCREEN_SIZE)
        a.set_ylim(0, SCREEN_SIZE)
        a.set_aspect("equal", adjustable="box")
        a.set_xticks(np.arange(0, SCREEN_SIZE + 0.5, 2.0))
        a.set_yticks(np.arange(0, SCREEN_SIZE + 0.5, 2.0))
        a.tick_params(labelsize=7)
        for k in np.arange(0, SCREEN_SIZE + 0.001, 0.1):
            a.axvline(k, color="#cfe0ef", lw=0.3, zorder=0)
            a.axhline(k, color="#cfe0ef", lw=0.3, zorder=0)
        for k in np.arange(0, SCREEN_SIZE + 0.001, 1.0):
            a.axvline(k, color="#7fa8c9", lw=0.7, zorder=0)
            a.axhline(k, color="#7fa8c9", lw=0.7, zorder=0)
        a.set_xlabel(T("cm"), fontsize=8)
        a.set_ylabel(T("cm"), fontsize=8)

        for px, py, lw, col in self.pencil:
            a.plot(px, py, "-", color=col, lw=lw, zorder=4,
                   solid_joinstyle="round")

        (self.live,) = a.plot([], [], "-", color="#d81010", lw=2.0,
                              alpha=0.9, zorder=5, animated=True)
        self.background = None
        self.canvas.draw_idle()

    def _redraw_paper(self):
        self._draw_bench()
        self._draw_paper()

    # ───────────────────────── dragging ─────────────────────────
    def _hit(self, x, y):
        if abs(x - self.screen_x) < 2.5 and \
                self.screen_y - 17 < y < self.screen_y + 17:
            return "screen"
        if self.cell_x - 1.4 < x < self.cell_x + CELL_D + 1.4 and \
                -0.5 < y < CELL_FOOT + CELL_H + 1:
            return "cell"
        if LASER_X - 3.0 < x < LASER_X + 2.0 and \
                self.laser_y - 2.5 < y < self.laser_y + 2.5:
            return "laser"
        return None

    def _press(self, ev):
        if ev.inaxes is self.axb and ev.xdata is not None:
            self.drag = self._hit(ev.xdata, ev.ydata)

    def _motion(self, ev):
        if ev.inaxes is self.axp and ev.xdata is not None:
            self.lbl_cur.config(
                text=(T("cursor:") + f"  x = {round(ev.xdata*20)/20:6.2f} cm"
                      f"   y = {round(ev.ydata*20)/20:6.2f} cm"))
        elif ev.inaxes is not self.axp:
            self.lbl_cur.config(text=T("cursor:  -"))

        if self.drag is None or ev.inaxes is not self.axb or ev.xdata is None:
            return
        if self.drag == "laser":
            self.laser_y = float(np.clip(ev.ydata, *LASER_Y_RANGE))
        elif self.drag == "cell":
            lo, hi = CELL_X_RANGE
            self.cell_x = float(np.clip(ev.xdata, lo,
                                        min(hi, self.screen_x - CELL_D - 5)))
        elif self.drag == "screen":
            self.screen_x = float(np.clip(ev.xdata, self.cell_x + CELL_D + 5,
                                          RAIL_LEN))
            self.screen_y = float(np.clip(ev.ydata, *SCREEN_Y_RANGE))
        self._draw_bench()

    def _release(self, ev):
        self.drag = None

    # ───────────────────────── actions ─────────────────────────
    def _laser_toggle(self):
        self.laser_on = self.var_on.get()
        self._redraw_paper()

    # ---- speed lock -------------------------------------------------
    def _lock_speed(self, on):
        """While the pipette is running the bench must run in real time."""
        if on:
            self._speed_locked = True
            self.speed = 1.0
            self.var_speed.set("1")
            self.cb_speed.config(state="disabled")
            self.lbl_speed_note.config(text=T("(1x while the water goes in)"))
        else:
            # the run always begins in real time; wind it forward from here
            self._speed_locked = False
            self.speed = 1.0
            self.var_speed.set("1")
            self.cb_speed.config(state="readonly")
            self.lbl_speed_note.config(text="")

    # ---- step 1: fill the cell with the salt solution ---------------
    def fill(self):
        """Poured from a beaker up to the white line - one go, as on the
        problem sheet.  Only the water is added drop by drop."""
        if self.started:
            return
        self.pour = Pour(float(self.var_conc.get()))
        self.filled = True
        self.wlevel = 0.0
        self.n_drops = 0
        self._t_first = None
        self.t_diff = 0.0
        self.t_stop0 = None
        self.t_sim = 0.0
        for rb in self.conc_btns:
            rb.config(state="disabled")
        self.btn_fill.config(state="disabled")
        self.btn_water.config(state="normal")
        self.btn_drop.config(state="normal")
        self._update_drop_label()
        self._draw_bench()
        self._redraw_paper()

    # ---- step 2: layer the distilled water drop by drop -------------
    def _update_drop_label(self):
        self.lbl_drops.config(
            text="     " + T("%d drops added") % self.n_drops)

    def _charge(self, n):
        """Put n drops into the pipette; it lets them go at its own rate."""
        if self.started or not self.filled:
            return
        self._lock_speed(True)
        room = (CELL_H - FILL_LINE - self.wlevel) / WDROP_RISE - 3
        self._drop_acc = min(self._drop_acc + n, max(room, 0.0))
        self._draw_bench()

    def add_water(self):
        self._charge(WDROPS_DEFAULT)

    def one_drop(self):
        """Release exactly one more drop of distilled water."""
        self._charge(1)

    def _release_drop(self):
        self._drops.append([CELL_FOOT + CELL_H + PIPETTE_DY, 0.0])

    def _advance_drops(self, dt):
        """Move the drops, let them land, raise the water column.

        Everything here runs on the wall clock, which is why the speed
        selector is held at 1x: the head start of the diffusion is the
        real time the student spends on this step.
        """
        self._rel_credit = min(self._rel_credit + dt * WDROP_RATE, 3.0)
        if self._drop_acc >= 1.0:
            n = int(min(self._drop_acc, self._rel_credit))
            self._rel_credit -= n
            for _ in range(n):
                if FILL_LINE + self.wlevel + WDROP_RISE * 3 > CELL_H:
                    self._drop_acc = 0.0
                    break
                self._drop_acc -= 1.0
                self._release_drop()

        surface = CELL_FOOT + FILL_LINE + self.wlevel
        still, landed = [], 0
        for d in self._drops:
            d[1] -= DROP_FALL_G * dt
            d[0] += d[1] * dt
            if d[0] <= surface:
                landed += 1
            else:
                still.append(d)
        self._drops = still

        if landed:
            if self._t_first is None:
                # the first drop touches the salt solution: from this
                # moment the interface is sharp and diffusion is running,
                # whether or not the student has started the stopwatch
                self._t_first = time.perf_counter()
                self.t_diff = 0.0
                self.btn_start.config(state="normal")
            self.wlevel = min(self.wlevel + landed * WDROP_RISE,
                              CELL_H - FILL_LINE)
            self.n_drops += landed
            self._update_drop_label()
        return landed > 0 or bool(self._drops)

    def _maybe_unlock_speed(self):
        """The speed selector comes back once the stopwatch is running.

        While the water is going in, and until the stopwatch is started,
        the bench is held at 1x: those seconds are real diffusion time.
        """
        if self._drops or self._drop_acc >= 1.0 or not self._speed_locked:
            return
        if self.started or self._t_first is None:
            self._lock_speed(False)

    # ---- step 3: start the stopwatch --------------------------------
    def start(self):
        if not self.filled or self._t_first is None:
            return
        # put the pipette down first, whatever is still in the air lands
        self._drop_acc = 0.0
        # the stopwatch is zeroed now, so it never sees the time already
        # spent layering the water - and it is zeroed a little late
        self.t_stop0 = self.t_diff + self.pour.t_off
        self.started = True
        self._last = time.perf_counter()
        self.btn_water.config(state="disabled")
        self.btn_drop.config(state="disabled")
        self.btn_start.config(state="disabled")
        self._lock_speed(False)
        self._draw_bench()
        self._redraw_paper()

    def empty(self):
        self._drops = []
        self._drop_acc = 0.0
        self.filled = False
        self.wlevel = 0.0
        self.n_drops = 0
        self._t_first = None
        self.t_diff = 0.0
        self.t_stop0 = None
        self.started = False
        self.pour = None
        self.t_sim = 0.0
        self.btn_fill.config(state="normal")
        self._pipette_up()
        self.btn_water.config(state="disabled")
        self.btn_drop.config(state="disabled")
        self.btn_start.config(state="disabled")
        for rb in self.conc_btns:
            rb.config(state="normal")
        self._update_drop_label()
        self._lock_speed(False)
        self._draw_bench()
        self._redraw_paper()

    @staticmethod
    def _hand_wander(s, rng):
        """Smooth deviation of a hand-drawn pencil line [cm].

        A constant offset (where the pencil was put down relative to the
        projected line) plus a few long-wavelength components; the result is
        a slow drift of about 0.3 mm rms, never a point-to-point jitter.
        """
        span = max(s[-1] - s[0], 1e-6)
        e = np.full_like(s, rng.normal(0.0, HAND_OFFSET))
        for _ in range(4):
            period = rng.uniform(0.25, 1.0) * span
            e = e + rng.normal(0.0, HAND_WANDER) * \
                np.sin(2 * np.pi * s / period + rng.uniform(0, 2 * np.pi))
        return e

    def trace(self):
        """Copy the line onto the paper, then lay the ruler along its

        straight ends and rule the asymptote across.  The dip is measured
        down from that reference line, and the marking scheme expects it
        to be on the sheet.
        """
        if not self.laser_on:
            return
        x, y = self.trace_xy()
        rng = np.random.default_rng()
        step = np.hypot(np.diff(x), np.diff(y))
        arc = np.concatenate(([0.0], np.cumsum(step)))
        x = x + self._hand_wander(arc, rng)
        y = y + self._hand_wander(arc, rng)
        lw = rng.uniform(0.75, 1.05)
        grey = int(rng.uniform(74, 100))
        col = "#%02x%02x%02x" % (grey, grey + 4, grey + 8)
        self.pencil.append((x, y, lw, col))

        # the ruler goes on the outer quarter at each end, where the beam
        # is no longer bent, and the line is ruled right across the sheet
        n = len(x)
        if n > 40:
            k = max(n // 4, 8)
            ends = np.concatenate((np.arange(k), np.arange(n - k, n)))
            a, b = np.polyfit(x[ends], y[ends], 1)
            xr = np.array([x.min(), x.max()])
            yr = a * xr + b + rng.normal(0.0, HAND_OFFSET, 2)
            self.pencil.append((xr, yr, lw * 0.8, col))
        self._draw_paper()

    def fresh_sheet(self):
        self.pencil.clear()
        self._draw_paper()

    def save_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG image", "*.png")],
            initialfile=T("mm_paper.png"))
        if not path:
            return
        fig = Figure(figsize=(7, 7), dpi=200)
        ax = fig.add_subplot(111)
        ax.set_xlim(0, SCREEN_SIZE)
        ax.set_ylim(0, SCREEN_SIZE)
        ax.set_aspect("equal")
        for k in np.arange(0, SCREEN_SIZE + 0.001, 0.1):
            ax.axvline(k, color="#cfe0ef", lw=0.2)
            ax.axhline(k, color="#cfe0ef", lw=0.2)
        for k in np.arange(0, SCREEN_SIZE + 0.001, 1.0):
            ax.axvline(k, color="#7fa8c9", lw=0.5)
            ax.axhline(k, color="#7fa8c9", lw=0.5)
        for px, py, lw, col in self.pencil:
            ax.plot(px, py, "-", color=col, lw=lw * 0.9)
        ax.set_xlabel(T("cm"))
        ax.set_ylabel(T("cm"))
        fig.tight_layout()
        fig.savefig(path)

    # ───────────────────────── loop ─────────────────────────
    def _on_draw(self, event):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    def _tick(self):
        t0 = time.perf_counter()
        dt = t0 - self._last
        self._last = t0
        busy = False
        if self._drops or self._drop_acc >= 1.0:
            self._advance_drops(min(dt, 0.5))
            busy = True
            if getattr(self, "art_liq", None) is not None:
                self.art_liq.set_visible(self.wlevel > 1e-9)
                self.art_liq.set_height(self.wlevel)
                cxm = self.cell_x + CELL_D / 2
                self.art_drops.set_data([cxm] * len(self._drops),
                                        [d[0] for d in self._drops])
            if not self._drops and self._drop_acc < 1.0:
                self._draw_bench()
        self._maybe_unlock_speed()

        if self._t_first is not None:
            self.t_diff += dt * self.speed
        if self.started:
            self.t_sim = max(self.t_diff - self.t_stop0, 0.0)
            m, s = divmod(int(self.t_sim), 60)
            self.lbl_t.config(text=f"{m:02d}:{s:02d}")
        elif not self.filled:
            self.lbl_t.config(text=T("--:--"))

        if self.laser_on:
            x, y = self.trace_xy()
            self.live.set_data(x, y)
            f = float(self.var_focus.get())
            self.live.set_linewidth(0.9 + 7.0 * f ** 1.6)
            self.live.set_alpha(0.95 - 0.45 * f)
        else:
            self.live.set_data([], [])

        if self.background is None:
            # take a clean snapshot: no drops baked into the background
            if getattr(self, "art_drops", None) is not None:
                self.art_drops.set_data([], [])
            self.canvas.draw()
        else:
            self.canvas.restore_region(self.background)
            if busy:
                self.axb.draw_artist(self.art_liq)
                self.axb.draw_artist(self.art_drops)
            self.axp.draw_artist(self.live)
            self.canvas.blit(self.fig.bbox)

        floor = 40 if busy else 60
        self.root.after(max(floor, int(2500 * (time.perf_counter() - t0))),
                        self._tick)


def main():
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.15)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
