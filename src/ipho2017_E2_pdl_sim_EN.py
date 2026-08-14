#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2017 (Yogyakarta) Experimental Problem E2
"Parallel Dipole Line Magnetic Trap for Earthquake and Volcanic Sensing"

Virtual laboratory.

The apparatus gives only what the real apparatus gives: a Teslameter reading,
a ruler, a stopwatch and the sight of the levitating rod.  It does NOT fit
anything, does NOT plot ln B against ln x, does NOT draw the camelback
potential and does NOT display M, chi, tau or mu_A.  Subtracting B0, adding
the 4 mm Hall offset, the log-log regression, the susceptibility and the air
viscosity are all the user's work, exactly as on the answer sheet.

────────────────────────────────────────────────────────────────────────
HOW THE REAL EXPERIMENT RUNS

  TASK 1 - magnetization M                                    (A.1 - A.4)
    A.1  switch the Teslameter on with no magnet nearby and record the zero
         offset B0; every later reading has to be corrected with it
    A.2  put the single diametric magnet on the rail, rotate it so that its
         magnetization points at the Hall sensor (the reading is maximal),
         then measure B against x for 7 mm <= x <= 16 mm.  The Hall element
         sits x_OFFSET = 4.0 mm behind the tip, so x = (ruler) + 4.0 mm.
         Do not use x = 4 mm: the sensor saturates and the probe flexes.
    A.3  plot ln B against ln x and get the exponent p from the slope
    A.4  m = 2 pi L exp(a)/mu0  and  M = m/(pi R^2 L)

  TASK 2 - the camelback potential                            (A.5 - A.12)
    A.5  drop a HB/0.5 rod of 8 mm into the trap and read the levitation
         height with the insert ruler pressed on the magnets:
         y0 = R - (reading below the magnet surface)
    A.6  chi from  m g = -(mu0 M^2 chi V_r/2)(R^4/a^5) f(y0/a),
         f(u) = 4u(3-u^2)(1-u^2)/(1+u^2)^5,  a = R + g_M/2
    A.8  displace the rod along z with the toothpick (A < 4 mm) and time at
         least 5 oscillations with the stopwatch
    A.9  chi again from  k_z = -C1 mu0 chi M^2 V_r  and  k_z = m_R omega^2
    A.10 the damping time constant from the half-time: tau = dt_1/2 / ln 2
    A.11 repeat for the four rod diameters at fixed length 8 mm
    A.12 tau = b r^2 ln(0.607 l/r) with b = 2 rho /(3 mu_A) gives mu_A

────────────────────────────────────────────────────────────────────────
PHYSICAL MODEL

  Outside a uniformly, diametrically magnetized cylinder the field on the
  magnetization axis is exactly that of a two dimensional line dipole,
        B(x) = mu0 M R^2 /(2 x^2) * w(x),   w(x) = (1+(x/L)^10)^(-1/10),
  where w is the finite-length roll-over: w -> 1 for x << L, and w -> L/x for
  x >> L so that B -> mu0 m/(2 pi x^3), the point dipole limit.  A fit over
  7...16 mm therefore returns p = 2.00 and M = 1.1e6 A/m.  A misalignment phi
  of the magnetization gives B_measured = B(x) cos(2 phi).

  The trap uses the same magnets with a = R + g_M/2; the levitation height
  solves eq. (3) on the stable (falling) branch of f(u), and the oscillation
  uses k_z of eq. (6), so omega = sqrt(-C1 mu0 chi M^2/rho) is independent of
  the rod size, while tau = TAU_A + TAU_B r^2 ln(0.607 l/r) is not.

CALIBRATION against the official Marking Scheme & Solution
  built-in truth   M = 1.10e6 A/m,  chi = -1.45e-4,  mu_A(eff) = 38e-6 Pa s
  a correct measurement then returns
      p    = 2.00                 (A.3  accepts 1.8 - 2.2)
      M    = 1.1e6 A/m            (A.4  accepts 0.9 - 1.4 e6)
      y0   = 2.0 mm               (A.5  accepts 1.7 - 2.2 mm)
      chi  = -1.45e-4             (A.6, A.9 accept -(1.4 - 2.6) e-4)
      Tz   = 1.23 s               (A.8  accepts 1.2 - 1.5 s)
      tau  = 6.5 ... 17 s         (A.11 accepts 5 - 20 s, rising with d)
      mu_A = 38e-6 Pa s           (A.12 accepts 20 - 60 e-6 Pa s)
────────────────────────────────────────────────────────────────────────
"""

import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ═══════════════════════════ language ═══════════════════════════
LANG = "en"          # "en" or "ko"

_KO = {
    # ---- Part A1 ----
    "Teslameter": "테슬라미터",
    "-- OFF --": "-- 꺼짐 --",
    "power on": "전원 켜기",
    "magnet on the rail": "자석을 레일에 올림",
    "record the zero offset  B0   (A.1)": "영점 오프셋 B0 기록   (A.1)",
    "B0 not recorded": "B0 미기록",
    "Probe and magnet": "프로브와 자석",
    "ruler reading from the magnet surface (mm)": "자석 표면부터의 자 눈금 (mm)",
    "ruler reads": "자 눈금",
    "magnet rotation  (Fig. 6a)": "자석 회전  (Fig. 6a)",
    "rotate until the reading is a maximum": "읽기값이 최대가 될 때까지 돌린다",
    "Note book": "실험 노트",
    "write down": "기록",
    "erase": "지우기",
    "new page": "새 쪽",
    "ruler (mm)": "자 (mm)",
    "meter (T)": "계기 (T)",
    "export the page as CSV": "이 쪽을 CSV로 내보내기",
    "cross section of the set-up  (Fig. 5a, 6)": "장치 단면도  (Fig. 5a, 6)",
    "magnet": "자석",
    "Hall sensor\non the board": "보드 위의\n홀 센서",
    "ruler (mm), zero on the magnet surface": "자 (mm), 원점은 자석 표면",
    "over range": "측정 범위 초과",
    "settling ...": "정착 중 ...",
    "switch the meter on first": "계기를 먼저 켜세요",
    "take the magnet off the rail first (A.1)": "자석을 레일에서 먼저 치우세요 (A.1)",
    "the meter is over range": "계기가 측정 범위를 벗어났습니다",
    # ---- Part A2 ----
    "Graphite rod": "흑연 막대",
    "  l (mm)": "  l (mm)",
    "drop the rod into the trap": "막대를 트랩에 넣는다",
    "press the insert ruler on the magnets (Fig. 7b)":
        "인서트 자를 자석에 대고 누른다 (Fig. 7b)",
    "Toothpick": "이쑤시개",
    "displacement along z (mm)": "z 방향 변위 (mm)",
    "displace and release": "밀었다 놓는다",
    "Stopwatch": "스톱워치",
    "Start": "시작",
    "Stop": "정지",
    "Lap": "랩",
    "Reset": "초기화",
    "front view of the trap  (cross section)": "트랩 정면도  (단면)",
    "graphite": "흑연",
    "Δy (mm)": "Δy (mm)",
    "top view of the trap  (scale in mm)": "트랩 상면도  (눈금 단위 mm)",
    "A.5   read \u0394y below the magnet surface, y0 = R \u2212 \u0394y.\n"
    "A.8   time at least 5 oscillations with Lap.\n"
    "A.10  time the amplitude halving, \u03c4 = \u0394t\u00bd / ln 2, "
    "for each diameter.":
        "A.5   자석 표면 아래로 Δy를 읽는다. y0 = R − Δy.\n"
        "A.8   랩으로 5주기 이상을 잰다.\n"
        "A.10  진폭이 반으로 줄 때까지의 시간을 재고 τ = Δt½ / ln 2,\n"
        "      지름마다 반복한다.",
    # ---- Part B ----
    "HB/0.5,  l = 8 mm": "HB/0.5,  l = 8 mm",
    "drop the rod in at the centre": "막대를 가운데에 넣는다",
    "Levelling screw": "수평 조정 나사",
    "Put the mouse over the screw head and roll the wheel: one notch is an "
    "eighth of a turn.  Hold Shift for a fortieth.  Turn it slowly and count "
    "the turns off the head yourself.":
        "나사 머리 위에 마우스를 올리고 휠을 굴리세요. 한 칸에 8분의 1바퀴, "
        "Shift를 누른 채로는 40분의 1바퀴입니다. 천천히 돌리고, 나사 머리를 "
        "보며 몇 바퀴인지 직접 세세요.",
    "unscrew back to level": "다시 풀어 수평으로",
    "the rod is still swinging - wait": "막대가 아직 흔들립니다 - 기다리세요",
    "lay the ruler beside the platform": "플랫폼 옆에 자를 놓는다",
    "B.3   derive \u0394z against S and N.\n"
    "B.4   turn the screw, let the rod settle, read \u0394z off the mm scale.  "
    "Measure D with the ruler and take \u03c9 from A.8.\n"
    "B.5   which Q settles fastest?":
        "B.3   Δz를 S와 N으로 유도한다.\n"
        "B.4   나사를 돌리고 막대가 멎으면 mm 눈금에서 Δz를 읽는다.\n"
        "      D는 자로 재고 ω는 A.8에서 가져온다.\n"
        "B.5   어떤 Q가 가장 빨리 멎는가?",
    "centre": "중심",
    "side view of the platform  (tilt drawn %.0fx)":
        "플랫폼 측면도  (기울기는 %.0f배로 그림)",
    "screw head\n(roll the wheel here)": "나사 머리\n(여기서 휠을 굴리세요)",
    "reference": "기준선",
    "top view of the trap  (scale printed on the platform, mm)":
        "트랩 상면도  (플랫폼에 인쇄된 눈금, mm)",
    "  Part A1  -  magnetization  (A.1 - A.4)  ":
        "  Part A1  -  자화 M  (A.1 - A.4)  ",
    "  Part A2  -  levitation and oscillation  (A.5 - A.12)  ":
        "  Part A2  -  부상과 진동  (A.5 - A.12)  ",
    "  Part B  -  tiltmeter  (B.1 - B.5)  ":
        "  Part B  -  경사계  (B.1 - B.5)  ",
    "CSV file": "CSV 파일",
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


# ═══════════════════════ constants and data ═══════════════════════
MU0   = 1.257e-6      # H/m
R     = 3.2e-3        # m, magnet radius
LMAG  = 25.4e-3       # m, magnet length
GM    = 1.5e-3        # m, gap of the PDL trap
A_PDL = R + GM / 2    # m
RHO   = 1680.0        # kg/m3, graphite
GRAV  = 9.8           # m/s2
C1    = 198.6         # 1/m2

X_OFFSET = 4.0e-3     # m, magnet centre -> Hall element when touching
METER_FS = 0.300      # T, Teslameter full scale
ROD_D = {"HB/0.3": 0.38e-3, "HB/0.5": 0.56e-3,
         "HB/0.7": 0.70e-3, "HB/0.9": 0.90e-3}

M_TRUE   = 1.10e6
CHI_TRUE = -1.45e-4

# Equation (3) treats the magnets as infinite line dipoles and the rod as a
# point.  Both are finite, and the rod actually floats a few per cent higher
# than that formula predicts (see Ref. [1], the finite size effect).  This is
# why the official solution gets chi = -1.85e-4 from y0 but -1.5e-4 from the
# oscillation period: the bench here reproduces the same honest discrepancy.
Y0_FINITE = 1.06
TAU_A, TAU_B = 3.15, 29.40      # s, s/mm2

# ---- Part B: the trap used as a tiltmeter (problem [6]) ----
#   The trap sits on a plank.  One end rests on a fixed screw, the other
#   on an adjustment screw a distance D away.  N turns of that screw lift
#   it by N*S, so the plank tilts by theta = N*S/D and the rod slides to
#   a new equilibrium:   k_z*dz = m*g*sin(theta)  ->  dz = g*S*N/(w^2*D)
D_TILT  = 0.220        # m, distance between the two screws (student measures it)
S_TRUE  = 0.80e-3      # m per turn, thread size (marking scheme: 0.8 +- 0.1)
TILT_EXAG = 20.0       # the tilt is drawn this much larger, or it is invisible
WHEEL_TURN = 0.125     # turns of the screw per notch of the mouse wheel
WHEEL_FINE = 0.025     # ... with Shift held down


# ═══════════════════════════ physics ═══════════════════════════
def b_magnet(x, M=M_TRUE):
    x = np.maximum(np.asarray(x, dtype=float), 1e-4)
    return MU0 * M * R ** 2 / (2 * x ** 2) * (1 + (x / LMAG) ** 10) ** (-0.1)


def f_Y(u):
    return 4 * u * (3 - u ** 2) * (1 - u ** 2) / (1 + u ** 2) ** 5


def levitation_height(M=M_TRUE, chi=CHI_TRUE):
    coef = MU0 * M ** 2 * abs(chi) / 2 * R ** 4 / A_PDL ** 5
    target = RHO * GRAV / coef
    # f(u) rises, peaks near u = 0.28 and returns to zero at u = 1;
    # only the falling branch is a stable levitation point.
    u = np.linspace(0.02, 0.99, 40000)
    fv = f_Y(u)
    top = int(np.argmax(fv))
    u, fv = u[top:], fv[top:]
    return u[np.argmin(np.abs(fv - target))] * A_PDL


def omega_z(chi=CHI_TRUE, M=M_TRUE):
    return np.sqrt(-C1 * MU0 * chi * M ** 2 / RHO)


def tau_damping(diameter, length):
    r_mm, l_mm = diameter * 1e3 / 2.0, length * 1e3
    return TAU_A + TAU_B * r_mm ** 2 * np.log(0.607 * l_mm / r_mm)


class Bench:
    """One set-up.  Small imperfections are drawn once."""

    def __init__(self, seed=None):
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.M = M_TRUE * (1 + rng.normal(0, 0.012))
        self.chi = CHI_TRUE * (1 + rng.normal(0, 0.02))
        self.B0 = rng.normal(0.0, 1.2e-3)
        self.drift = rng.normal(0.0, 0.15e-3)
        self.y0 = levitation_height(self.M, self.chi) * Y0_FINITE \
            * (1 + rng.normal(0, 0.02))
        self.tau_scale = 1 + rng.normal(0, 0.03)
        # the adjustment screw of this particular bench
        self.S = S_TRUE * (1 + rng.normal(0, 0.04))
        self.D = D_TILT

    def teslameter_true(self, x, phi_deg):
        b = b_magnet(x, self.M) * np.cos(2 * np.deg2rad(phi_deg))
        return b + self.B0 + self.drift

    def noise(self):
        return self.rng.normal(0.0, 0.15e-3)

    def tau(self, diameter, length):
        return tau_damping(diameter, length) * self.tau_scale

    def omega(self):
        return omega_z(self.chi, self.M)


# ═══════════════════════════ Task 1 ═══════════════════════════
class PartA1(ttk.Frame):
    """Determination of the magnet's magnetization - raw readings only."""

    def __init__(self, master, bench):
        super().__init__(master, padding=8)
        self.bench = bench
        self.rows = []
        self.shown = 0.0
        self.B0_rec = None
        self._last_val = 0.0
        self._t = time.perf_counter()

        self._controls()
        self._figure()
        self._draw()
        self._on_move()
        self._tick()

    # ------------------------------------------------ controls
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        r = 0
        ttk.Label(c, text=T("Teslameter"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        disp = tk.Frame(c, bg="#101418", bd=2, relief="sunken")
        disp.grid(row=r, column=0, sticky="ew", pady=(4, 2))
        self.lbl_read = tk.Label(disp, text=T("-- OFF --"),
                                 font=("Consolas", 23, "bold"),
                                 fg="#39ff88", bg="#101418", anchor="e", width=12)
        self.lbl_read.pack(fill="x", padx=8, pady=6)
        self.lbl_stable = tk.Label(disp, text="", font=("Consolas", 9),
                                   fg="#ffb84d", bg="#101418", anchor="e")
        self.lbl_stable.pack(fill="x", padx=8, pady=(0, 4))
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 6))
        self.var_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text=T("power on"), variable=self.var_on).pack(side="left")
        self.var_present = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text=T("magnet on the rail"), variable=self.var_present,
                        command=self._draw).pack(side="left", padx=(10, 0))
        r += 1
        ttk.Button(c, text=T("record the zero offset  B0   (A.1)"),
                   command=self.record_zero).grid(row=r, column=0, sticky="ew")
        r += 1
        self.lbl_b0 = ttk.Label(c, text=T("B0 not recorded"), foreground="#a33")
        self.lbl_b0.grid(row=r, column=0, sticky="w", pady=(2, 6))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Probe and magnet"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("ruler reading from the magnet surface (mm)")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_dx = tk.DoubleVar(value=8.0)
        ttk.Scale(c, from_=0.0, to=40.0, variable=self.var_dx, length=250,
                  orient="horizontal",
                  command=lambda *_: self._on_move()).grid(row=r, column=0,
                                                           sticky="ew")
        r += 1
        self.lbl_dx = ttk.Label(c, text="")
        self.lbl_dx.grid(row=r, column=0, sticky="w", pady=(2, 6))
        r += 1
        ttk.Label(c, text=T("magnet rotation  (Fig. 6a)")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_phi = tk.DoubleVar(value=25.0)
        ttk.Scale(c, from_=-90.0, to=90.0, variable=self.var_phi, length=250,
                  orient="horizontal",
                  command=lambda *_: self._draw()).grid(row=r, column=0,
                                                        sticky="ew")
        r += 1
        ttk.Label(c, text=T("rotate until the reading is a maximum"),
                  foreground="#666").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Note book"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        bt = ttk.Frame(c)
        bt.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        ttk.Button(bt, text=T("write down"), command=self.record).pack(side="left")
        ttk.Button(bt, text=T("erase"), command=self.delete).pack(side="left", padx=4)
        ttk.Button(bt, text=T("new page"), command=self.clear).pack(side="left")
        r += 1
        self.tree = ttk.Treeview(c, columns=("dx", "b"), show="headings",
                                 height=11)
        self.tree.heading(T("dx"), text=T("ruler (mm)"))
        self.tree.heading("b", text=T("meter (T)"))
        self.tree.column("dx", width=110, anchor="e")
        self.tree.column("b", width=110, anchor="e")
        self.tree.grid(row=r, column=0, sticky="ew", pady=4)
        r += 1
        ttk.Button(c, text=T("export the page as CSV"),
                   command=self.export).grid(row=r, column=0, sticky="ew")
        r += 1
        self.lbl_msg = ttk.Label(c, text="", wraplength=250, foreground="#a33")
        self.lbl_msg.grid(row=r, column=0, sticky="w", pady=(6, 0))

    # ------------------------------------------------ figure
    def _figure(self):
        self.fig = Figure(figsize=(8.0, 5.2), dpi=96)
        self.axt = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")

    def _draw(self):
        x = self.x_actual
        xm = x * 1e3
        phi = float(self.var_phi.get())
        present = self.var_present.get()

        # ---------- cross section perpendicular to the magnet axis ----------
        b = self.axt
        b.clear()
        b.set_title(T("cross section of the set-up  (Fig. 5a, 6)"), fontsize=10)
        if present:
            th = np.linspace(0, 2 * np.pi, 200)
            b.fill(R * 1e3 * np.cos(th), R * 1e3 * np.sin(th),
                   color="#c9ccd1", ec="#555", zorder=3)
            b.annotate("", xy=(5.6 * np.cos(np.deg2rad(phi)),
                               5.6 * np.sin(np.deg2rad(phi))),
                       xytext=(0, 0), zorder=4,
                       arrowprops=dict(arrowstyle="-|>", color="#cc0000", lw=2.4))
            b.text(0, -R * 1e3 - 2.6, T("magnet"), ha="center", fontsize=8.5)
        b.add_patch(Rectangle((xm, -7.0), 1.7, 14.0, facecolor="#2f4f6f",
                              edgecolor="#222", lw=0.8, zorder=3))
        b.add_patch(Rectangle((xm - 1.5, -1.7), 1.5, 3.4, facecolor="#ffcc00",
                              edgecolor="#222", lw=0.8, zorder=3))
        b.text(xm + 3.2, 6.4, T("Hall sensor\non the board"), fontsize=8.5, va="top")
        # ruler, its zero on the surface of the magnet
        x_surf = R * 1e3
        for t in np.arange(0, 41, 1):
            hgt = 1.2 if t % 5 else 2.2
            b.plot([x_surf + t] * 2, [-9.5, -9.5 + hgt], color="#444", lw=0.7)
            if t % 5 == 0:
                b.text(x_surf + t, -12.2, f"{t:.0f}", ha="center", fontsize=7.5)
        b.plot([x_surf - 2, x_surf + 41], [-9.5, -9.5], color="#444", lw=1.0)
        tip = xm - X_OFFSET * 1e3 + x_surf          # front face of the probe
        b.plot([tip, tip], [-9.5, -1.8], "-", color="#c00000", lw=0.9,
               alpha=0.8, zorder=2)
        b.text(24, -14.0, T("ruler (mm), zero on the magnet surface"),
               ha="center", fontsize=7.5, color="#555")
        b.set_xlim(-9, 47)
        b.set_ylim(-15.5, 10.5)
        b.set_aspect("equal")
        b.set_xticks([])
        b.set_yticks([])
        for sp in b.spines.values():
            sp.set_visible(False)

        self.canvas.draw_idle()

    # ------------------------------------------------ logic
    @property
    def x_actual(self):
        return float(self.var_dx.get()) * 1e-3 + X_OFFSET

    def _on_move(self):
        self.lbl_dx.config(
            text=T("ruler reads") + f"  {self.var_dx.get():.1f} mm")
        self._draw()

    def _tick(self):
        if not self.var_on.get():
            self.lbl_read.config(text=T("-- OFF --"))
            self.lbl_stable.config(text="")
            self._t = time.perf_counter()
            self.after(120, self._tick)
            return

        now = time.perf_counter()
        dt = max(now - self._t, 0.0)
        self._t = now
        if self.var_present.get():
            target = self.bench.teslameter_true(self.x_actual,
                                                float(self.var_phi.get()))
        else:
            target = self.bench.B0 + self.bench.drift
        self.shown += (target - self.shown) * (1 - np.exp(-dt / 0.6))
        val = self.shown + self.bench.noise()

        if abs(val) > METER_FS:
            self.lbl_read.config(text=T("  O L  "), fg="#ff5555")
            self.lbl_stable.config(text=T("over range"))
        else:
            self.lbl_read.config(text=f"{val*1e3:8.1f} mT", fg="#39ff88")
            self.lbl_stable.config(
                text="" if abs(target - self.shown) < 3e-4
                     else T("settling ..."))
        self._last_val = val
        self.after(120, self._tick)

    def record_zero(self):
        if not self.var_on.get():
            return self._msg(T("switch the meter on first"))
        if self.var_present.get():
            return self._msg(T("take the magnet off the rail first (A.1)"))
        self.B0_rec = self._last_val
        self.lbl_b0.config(text=f"B0 = {self.B0_rec*1e3:+.2f} mT",
                           foreground="#282")
        self._msg("")

    def record(self):
        if not self.var_on.get():
            return self._msg(T("switch the meter on first"))
        if abs(self._last_val) > METER_FS:
            return self._msg(T("the meter is over range"))
        dx = float(self.var_dx.get())
        self.rows.append((dx, self._last_val))
        self.tree.insert("", "end", values=(f"{dx:.1f}", f"{self._last_val:.4f}"))
        self._msg("")

    def delete(self):
        for it in self.tree.selection():
            i = self.tree.index(it)
            self.tree.delete(it)
            del self.rows[i]

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()

    def export(self):
        if not self.rows:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            initialfile=T("E2_task1.csv"))
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("ruler_mm,meter_T\n")
            for dx, b in self.rows:
                fh.write(f"{dx:.2f},{b:.5f}\n")

    def _msg(self, text):
        self.lbl_msg.config(text=text)


# ═══════════════════════════ Task 2 ═══════════════════════════
class PartA2(ttk.Frame):
    """The camelback potential - the rod, the ruler and the stopwatch only."""

    def __init__(self, master, bench):
        super().__init__(master, padding=8)
        self.bench = bench
        self.rod_key = "HB/0.5"
        self.rod_len = 8.0e-3
        self.placed = False
        self.osc_t0 = None
        self.amp = 3.0e-3
        self.sim_t = 0.0
        self.sw_running = False
        self.sw_t0 = 0.0
        self._swv = 0.0
        self.laps = []
        self._last = time.perf_counter()

        self._controls()
        self._figure()
        self._static()
        self._tick()

    # ------------------------------------------------ controls
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        r = 0
        ttk.Label(c, text=T("Graphite rod"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 4))
        self.var_rod = tk.StringVar(value=self.rod_key)
        cb = ttk.Combobox(row, textvariable=self.var_rod, width=9,
                          state="readonly", values=list(ROD_D))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda *_: self.place())
        ttk.Label(row, text=T("  l (mm)")).pack(side="left")
        self.var_len = tk.StringVar(value="8")
        e = ttk.Entry(row, textvariable=self.var_len, width=5)
        e.pack(side="left", padx=(2, 0))
        e.bind("<Return>", lambda *_: self.place())
        r += 1
        ttk.Button(c, text=T("drop the rod into the trap"),
                   command=self.place).grid(row=r, column=0, sticky="ew")
        r += 1
        self.var_ruler = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text=T("press the insert ruler on the magnets "
                                "(Fig. 7b)"), variable=self.var_ruler,
                        command=self._static).grid(row=r, column=0,
                                                   sticky="w", pady=(4, 2))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Toothpick"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("displacement along z (mm)")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_amp = tk.DoubleVar(value=3.0)
        ttk.Scale(c, from_=0.2, to=4.0, variable=self.var_amp, length=250,
                  orient="horizontal").grid(row=r, column=0, sticky="ew")
        r += 1
        ttk.Button(c, text=T("displace and release"),
                   command=self.release).grid(row=r, column=0,
                                              sticky="ew", pady=(4, 2))
        r += 1
        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Stopwatch"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        disp = tk.Frame(c, bg="#101418", bd=2, relief="sunken")
        disp.grid(row=r, column=0, sticky="ew", pady=(4, 2))
        self.lbl_sw = tk.Label(disp, text=T("0.00 s"),
                               font=("Consolas", 21, "bold"),
                               fg="#8fd6ff", bg="#101418", anchor="e", width=12)
        self.lbl_sw.pack(fill="x", padx=8, pady=6)
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        self.btn_sw = ttk.Button(row, text=T("Start"), width=8, command=self.sw_toggle)
        self.btn_sw.pack(side="left")
        ttk.Button(row, text=T("Lap"), width=6,
                   command=self.sw_lap).pack(side="left", padx=3)
        ttk.Button(row, text=T("Reset"), width=7,
                   command=self.sw_reset).pack(side="left")
        r += 1
        self.lst = tk.Listbox(c, height=9, font=("Consolas", 9))
        self.lst.grid(row=r, column=0, sticky="ew", pady=4)
        r += 1
        ttk.Label(c, wraplength=250, foreground="#555",
                  text=(T("A.5   read \u0394y below the magnet surface, "
                        "y0 = R \u2212 \u0394y.\n"
                        "A.8   time at least 5 oscillations with Lap.\n"
                        "A.10  time the amplitude halving, \u03c4 = \u0394t\u00bd / ln 2, "
                        "for each diameter."))
                  ).grid(row=r, column=0, sticky="w", pady=(4, 0))

    # ------------------------------------------------ figure
    def _figure(self):
        self.fig = Figure(figsize=(8.0, 7.4), dpi=96)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.28, 1.0],
                                   hspace=0.24)
        self.axf = self.fig.add_subplot(gs[0, 0])
        self.axt = self.fig.add_subplot(gs[1, 0])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.background = None
        self.canvas.mpl_connect("draw_event", self._on_draw)

    def _on_draw(self, event):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    def _blit(self):
        self.axt.draw_artist(self.rodtop)

    # ------------------------------------------------ rod
    @property
    def Vr(self):
        return np.pi * (ROD_D[self.rod_key] / 2) ** 2 * self.rod_len

    def place(self):
        self.rod_key = self.var_rod.get()
        try:
            self.rod_len = max(float(self.var_len.get()), 1.0) * 1e-3
        except ValueError:
            self.rod_len = 8.0e-3
        self.placed = True
        self.osc_t0 = None
        self._static()

    def release(self):
        if self.placed:
            self.amp = float(self.var_amp.get()) * 1e-3
            self.osc_t0 = self.sim_t

    def z_now(self):
        if not self.placed or self.osc_t0 is None:
            return 0.0
        t = self.sim_t - self.osc_t0
        tau = self.bench.tau(ROD_D[self.rod_key], self.rod_len)
        return self.amp * np.exp(-t / tau) * np.cos(self.bench.omega() * t)

    # ------------------------------------------------ stopwatch
    def sw_toggle(self):
        if self.sw_running:
            self.sw_running = False
            self.btn_sw.config(text=T("Start"))
        else:
            self.sw_running = True
            self.sw_t0 = self.sim_t - self._swv
            self.btn_sw.config(text=T("Stop"))

    def sw_lap(self):
        if not self.sw_running:
            return
        v = self._swv + self.bench.rng.normal(0.0, 0.12)   # reaction time
        self.laps.append(v)
        n = len(self.laps)
        prev = self.laps[-2] if n > 1 else 0.0
        self.lst.insert("end", f"{n:2d}   {v:7.2f} s   (+{v-prev:5.2f})")
        self.lst.see("end")

    def sw_reset(self):
        self.sw_running = False
        self._swv = 0.0
        self.laps.clear()
        self.lst.delete(0, "end")
        self.btn_sw.config(text=T("Start"))

    # ------------------------------------------------ drawing
    def _static(self):
        y0 = self.bench.y0
        d = ROD_D[self.rod_key]
        Rm, Am, Lm = R * 1e3, A_PDL * 1e3, LMAG * 1e3

        # ---------- front view (Fig. 7a) ----------
        a = self.axf
        a.clear()
        a.set_title(T("front view of the trap  (cross section)"), fontsize=10)
        th = np.linspace(0, 2 * np.pi, 200)
        for sx in (-Am, Am):
            a.fill(sx + Rm * np.cos(th), Rm * np.sin(th),
                   color="#c9ccd1", ec="#555", zorder=2)
            a.annotate("", xy=(sx + 2.2, 0), xytext=(sx - 0.4, 0), zorder=4,
                       arrowprops=dict(arrowstyle="-|>", color="#cc0000", lw=1.8))
        a.text(-Am, -Rm - 1.7, T("magnet"), ha="center", fontsize=8)
        if self.placed:
            a.add_patch(Circle((0.0, y0 * 1e3), max(d / 2 * 1e3, 0.22),
                               facecolor="#202020", edgecolor="#000",
                               lw=0.6, zorder=5))
            a.annotate(T("graphite"), xy=(0.4, y0 * 1e3 + 0.25), xytext=(2.2, 6.4),
                       fontsize=8,
                       arrowprops=dict(arrowstyle="-", color="#666", lw=0.7))
        if self.var_ruler.get():
            xr = 8.8
            a.plot([xr, xr], [Rm - 5.2, Rm + 1.6], color="#444", lw=1.3)
            for k in np.arange(-1.0, 5.01, 0.5):
                w = 1.7 if abs(k - round(k)) < 1e-6 else 0.9
                a.plot([xr, xr - w], [Rm - k] * 2, color="#444", lw=0.7)
                if abs(k - round(k)) < 1e-6:
                    a.text(xr + 0.35, Rm - k, f"{k:.0f}", fontsize=7,
                           va="center")
            a.text(xr - 0.2, Rm + 2.2, T("\u0394y (mm)"), fontsize=7, ha="center")
            if self.placed:
                a.plot([0.4, xr - 1.8], [y0 * 1e3] * 2, ":", color="#c00000",
                       lw=0.9, zorder=6)
        a.plot([-Am - Rm - 1, Am + Rm + 1], [0, 0], "--", color="#bbb", lw=0.7)
        a.set_xlim(-9, 13)
        a.set_ylim(-5.5, 8.2)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ---------- top view with the mm scale (Fig. A.10a) ----------
        c = self.axt
        c.clear()
        c.set_title(T("top view of the trap  (scale in mm)"), fontsize=10)
        for sx in (-Am, Am):
            c.add_patch(Rectangle((-Lm / 2, sx - Rm), Lm, 2 * Rm,
                                  facecolor="#dcdee2", edgecolor="#888",
                                  lw=0.8, zorder=1))
        for k in np.arange(-10, 10.1, 1):
            hgt = 1.0 if k % 5 else 1.9
            c.plot([k, k], [7.8, 7.8 - hgt], color="#444", lw=0.8)
            if k % 5 == 0:
                c.text(k, 8.3, f"{k:.0f}", ha="center", fontsize=7.5)
        c.plot([-10.5, 10.5], [7.8, 7.8], color="#444", lw=1.0)
        (self.rodtop,) = c.plot([0], [0], "-", color="#101010", lw=6,
                                solid_capstyle="butt", animated=True)
        c.set_xlim(-16, 16)
        c.set_ylim(-8.4, 10.2)
        c.set_aspect("equal")
        c.set_xticks([])
        c.set_yticks([])
        for sp in c.spines.values():
            sp.set_visible(False)

        self.background = None
        self.canvas.draw_idle()

    # ------------------------------------------------ loop
    def _tick(self):
        t0 = time.perf_counter()
        dt = t0 - self._last
        self._last = t0
        self.sim_t += dt
        if self.sw_running:
            self._swv = self.sim_t - self.sw_t0
        self.lbl_sw.config(text=f"{self._swv:.2f} s")

        if not self.winfo_ismapped():
            self.after(150, self._tick)
            return

        z = self.z_now()
        half = self.rod_len / 2 * 1e3
        self.rodtop.set_data([z * 1e3 - half, z * 1e3 + half], [0, 0])

        if self.background is None:
            self.canvas.draw()
        self.canvas.restore_region(self.background)
        self._blit()
        self.canvas.blit(self.fig.bbox)

        self.after(max(60, int(2500 * (time.perf_counter() - t0))), self._tick)


class PartB(ttk.Frame):
    """Section B - the PDL trap as a tiltmeter  (problems B.1 - B.5).

    The set-up of Fig. 9: the top platform rests on three levelling
    screws above the bottom platform, and the trap sits in the middle of
    it.  Screwing one of them down tips the platform by theta = N S / D,
    and the rod slides downhill to a new equilibrium.

    The bench gives what the bench gives: the screw (grab its head and
    turn it), a ruler along the platform for D, and the millimetre scale
    printed on the platform for dz.  Counting the turns is the student's
    job - nothing here reads out an angle.
    """

    ROD_KEY = "HB/0.5"          # fixed by the problem sheet
    ROD_LEN = 8.0e-3            # m

    def __init__(self, master, bench):
        super().__init__(master, padding=8)
        self.bench = bench
        self.placed = False
        self.turns = 0.0         # total turns of the screw (never displayed)
        self.z = 0.0             # m, rod position along the trap axis
        self.vz = 0.0            # m/s
        self._jit = 0.0
        self._last = time.perf_counter()

        self._controls()
        self._figure()
        self._static()
        self._tick()

    # ------------------------------------------------ physics
    @property
    def tau(self):
        return self.bench.tau(ROD_D[self.ROD_KEY], self.ROD_LEN)

    def z_equilibrium(self):
        """k_z dz = m g sin(theta),  theta = N S / D.

        The rod slides towards the low end, hence the minus sign.
        """
        w = self.bench.omega()
        theta = self.turns * self.bench.S / self.bench.D
        return -GRAV * np.sin(theta) / w ** 2

    # ------------------------------------------------ controls
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        r = 0
        ttk.Label(c, text=T("Graphite rod"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("HB/0.5,  l = 8 mm")).grid(
            row=r, column=0, sticky="w", pady=(1, 3))
        r += 1
        ttk.Button(c, text=T("drop the rod in at the centre"),
                   command=self.place).grid(row=r, column=0, sticky="ew")
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=9)
        r += 1
        ttk.Label(c, text=T("Levelling screw"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, wraplength=252, foreground="#555",
                  text=(T("Put the mouse over the screw head and roll the "
                        "wheel: one notch is an eighth of a turn.  Hold "
                        "Shift for a fortieth.  Turn it slowly and count "
                        "the turns off the head yourself."))
                  ).grid(row=r, column=0, sticky="w", pady=(3, 4))
        r += 1
        ttk.Button(c, text=T("unscrew back to level"),
                   command=self.relevel).grid(row=r, column=0, sticky="ew")
        r += 1
        self.lbl_state = ttk.Label(c, text="", foreground="#8a5a00")
        self.lbl_state.grid(row=r, column=0, sticky="w", pady=(5, 0))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=9)
        r += 1
        self.var_ruler = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text=T("lay the ruler beside the platform"),
                        variable=self.var_ruler,
                        command=self._static).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, wraplength=252, foreground="#555",
                  text=(T("B.3   derive \u0394z against S and N.\n"
                        "B.4   turn the screw, let the rod settle, read "
                        "\u0394z off the mm scale.  Measure D with the "
                        "ruler and take \u03c9 from A.8.\n"
                        "B.5   which Q settles fastest?"))
                  ).grid(row=r, column=0, sticky="w", pady=(9, 0))

    # ------------------------------------------------ actions
    def place(self):
        self.placed = True
        self.turns = 0.0
        self.z = 0.0
        self.vz = 0.0
        self._static()

    def relevel(self):
        self.turns = 0.0
        self._static()

    # -- the wheel over the screw head ------------------------------
    def _scroll(self, ev):
        """Roll the wheel over the head to drive the screw in or out."""
        if ev.inaxes is not self.axh:
            return
        fine = bool(getattr(ev, "guiEvent", None)) and \
            (getattr(ev.guiEvent, "state", 0) & 0x0001)      # Shift held
        self.turns += ev.step * (WHEEL_FINE if fine else WHEEL_TURN)
        self._static()

    # ------------------------------------------------ figure
    def _figure(self):
        self.fig = Figure(figsize=(8.0, 6.9), dpi=96)
        gs = self.fig.add_gridspec(2, 2, height_ratios=[1.12, 1.0],
                                   width_ratios=[3.5, 1.0],
                                   hspace=0.14, wspace=0.04)
        self.axs = self.fig.add_subplot(gs[0, 0])
        self.axh = self.fig.add_subplot(gs[0, 1])
        self.axt = self.fig.add_subplot(gs[1, :])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.background = None
        self.canvas.mpl_connect("draw_event", self._on_draw)
        self.canvas.mpl_connect("scroll_event", self._scroll)

    def _on_draw(self, event):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    # ------------------------------------------------ drawing
    def _static(self):
        Dmm = self.bench.D * 1e3
        theta = self.turns * self.bench.S / self.bench.D
        ang = theta * TILT_EXAG
        ca, sa = np.cos(ang), np.sin(ang)
        x0, x1 = 0.0, Dmm                 # the two screws in the side view
        lift = Dmm * np.tan(ang)
        PT = 5.0                          # thickness of a platform

        a = self.axs
        a.clear()
        a.set_title(T("side view of the platform  (tilt drawn %.0fx)")
                    % TILT_EXAG, fontsize=9.5)

        # ---- bottom platform ----
        a.add_patch(Rectangle((-40, -PT), Dmm + 80, PT,
                              facecolor="#d5d8dc", edgecolor="#333",
                              lw=1.0, zorder=1))

        # ---- top platform, hinged on the left screw ----
        def on_top(px, py):
            """plank coordinates -> figure coordinates"""
            return (x0 + (px - x0) * ca - py * sa,
                    14.0 + (px - x0) * sa + py * ca)

        corners = [on_top(px, py) for px, py in
                   ((-34, 0), (Dmm + 34, 0), (Dmm + 34, PT), (-34, PT))]
        a.add_patch(Polygon(corners, closed=True, facecolor="#e9ecef",
                            edgecolor="#333", lw=1.1, zorder=4))
        self._plank = (x0, ca, sa)

        # ---- the two levelling screws: head above, point on the plate ----
        for xs, ext in ((x0, 0.0), (x1, lift)):
            top = on_top(xs, PT)
            a.plot([top[0], xs], [top[1], 0.0], "-", color="#5d6369",
                   lw=2.6, zorder=3)
            a.add_patch(Polygon([(xs - 1.8, 1.6), (xs + 1.8, 1.6), (xs, -0.4)],
                                closed=True, facecolor="#8d939a",
                                edgecolor="#444", lw=0.7, zorder=3))
            a.add_patch(Rectangle((top[0] - 5.0, top[1] + 0.6), 10.0, 2.6,
                                  facecolor="#9aa0a6", edgecolor="#444",
                                  lw=0.8, zorder=6))

        # ---- theta, marked at the raised end as in Fig. 9 ----
        if abs(lift) > 0.6:
            xe = Dmm + 22
            pe = on_top(xe, 0.0)
            a.annotate("", xy=(pe[0], pe[1]), xytext=(pe[0], 0.0), zorder=6,
                       arrowprops=dict(arrowstyle="<->", color="#222", lw=0.9))
            a.text(pe[0] - 3, (pe[1] + 0.0) / 2, "\u03b8", fontsize=12,
                   ha="right", va="center")

        # ---- the trap assembly, drawn schematically as in Fig. 9 ----
        cxp = Dmm / 2
        HW, HT = 30.0, 62.0                # half width and height of the frame
        for dz in (-HW, HW - 3.0):
            a.add_patch(Polygon([on_top(cxp + dz, PT),
                                 on_top(cxp + dz, PT + HT),
                                 on_top(cxp + dz + 3.0, PT + HT),
                                 on_top(cxp + dz + 3.0, PT)],
                                closed=True, facecolor="#e4e7ea",
                                edgecolor="#333", lw=1.1, zorder=5))
        for hy in (PT + 12.0, PT + 52.0):
            pl, pr = on_top(cxp - HW, hy), on_top(cxp + HW, hy)
            a.plot([pl[0], pr[0]], [pl[1], pr[1]], "-", color="#333",
                   lw=1.4, zorder=5)
        pm = on_top(cxp + 14.0, PT + 23.0)
        pml = on_top(cxp + HW + 30.0, PT + HT - 14.0)
        a.annotate(T("magnet"), xy=pm, xytext=pml, fontsize=9, ha="left",
                   va="center", zorder=7,
                   arrowprops=dict(arrowstyle="-", color="#333", lw=0.8))

        # ---- centre line, dz and the graphite (animated) ----
        self._z_centre = cxp
        pc0, pc1 = on_top(cxp, PT + 4.0), on_top(cxp, PT + HT + 3.0)
        a.plot([pc0[0], pc1[0]], [pc0[1], pc1[1]], "-.", color="#333",
               lw=0.9, zorder=6)
        a.text(pc1[0], pc1[1] + 2.0, T("centre"), fontsize=9, ha="center")
        pz0, pz1 = on_top(cxp, PT + 33.0), on_top(cxp - 17.0, PT + 33.0)
        a.annotate("", xy=pz1, xytext=pz0, zorder=7,
                   arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.0))
        a.text(*on_top(cxp - 8.5, PT + 37.0), T("\u0394z"), fontsize=10,
               ha="center", va="bottom")
        (self.rodside,) = a.plot([], [], "-", color="#303030", lw=6,
                                 solid_capstyle="butt", animated=True, zorder=7)
        pgl = on_top(cxp - HW - 30.0, PT + HT - 14.0)
        a.annotate(T("graphite"), xy=on_top(cxp - 11.0, PT + 22.0), xytext=pgl,
                   fontsize=9, ha="right", va="center", zorder=7,
                   arrowprops=dict(arrowstyle="-", color="#333", lw=0.8))

        # ---- D, between the two screws, and the ruler ----
        pd0, pd1 = on_top(x0, PT + 9.0), on_top(x1, PT + 9.0)
        a.annotate("", xy=pd0, xytext=pd1, zorder=7,
                   arrowprops=dict(arrowstyle="<->", color="#222", lw=1.1))
        pdl = on_top(cxp - HW - 26.0, PT + 15.0)
        a.text(pdl[0], pdl[1], "D", fontsize=15, style="italic",
               ha="center", va="bottom")
        if self.var_ruler.get():
            yr = -16.0
            a.plot([-14, Dmm + 18], [yr, yr], color="#444", lw=1.1)
            for k in np.arange(-10, Dmm + 17.1, 10):
                big = abs(k % 50) < 1e-6
                a.plot([k, k], [yr, yr - (4.6 if big else 2.4)],
                       color="#444", lw=0.8)
                if big:
                    a.text(k, yr - 10.5, "%.0f" % (k / 10), fontsize=7.5,
                           ha="center", va="center")
            a.text(Dmm / 2, yr - 18.5, T("cm"), fontsize=8, ha="center")
            for xs in (x0, x1):
                a.plot([xs, xs], [-PT, yr], ":", color="#888", lw=0.7)

        a.set_xlim(-52, Dmm + 56)
        a.set_ylim(-40, 116)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ---------- the screw head, seen from above ----------
        h = self.axh
        h.clear()
        h.set_title(T("screw head\n(roll the wheel here)"), fontsize=9)
        h.add_patch(Circle((0, 0), 1.0, facecolor="#d8dce0",
                           edgecolor="#444", lw=1.4, zorder=2))
        for k in range(24):                     # knurling
            b0 = 2 * np.pi * k / 24
            h.plot([0.92 * np.cos(b0), 1.0 * np.cos(b0)],
                   [0.92 * np.sin(b0), 1.0 * np.sin(b0)],
                   color="#8b9096", lw=1.0, zorder=3)
        ph = 2 * np.pi * (-self.turns)          # index mark on the head
        h.plot([0, 0.78 * np.sin(ph)], [0, 0.78 * np.cos(ph)],
               color="#b03030", lw=3.0, solid_capstyle="round", zorder=4)
        h.add_patch(Circle((0, 0), 0.12, facecolor="#444",
                           edgecolor="none", zorder=5))
        h.plot([0, 0], [1.06, 1.26], color="#222", lw=1.6, zorder=4)
        h.text(0, 1.34, T("reference"), fontsize=7.5, ha="center", va="bottom")
        h.set_xlim(-1.5, 1.5)
        h.set_ylim(-1.5, 1.6)
        h.set_aspect("equal")
        h.set_xticks([])
        h.set_yticks([])
        for sp in h.spines.values():
            sp.set_visible(False)

        # ---------- top view, on the platform's mm scale ----------
        c = self.axt
        c.clear()
        c.set_title(T("top view of the trap  (scale printed on the platform, mm)"),
                    fontsize=9.5)
        Rm, Am, Lm = R * 1e3, A_PDL * 1e3, LMAG * 1e3
        for sx in (-Am, Am):
            c.add_patch(Rectangle((-Lm / 2, sx - Rm), Lm, 2 * Rm,
                                  facecolor="#dcdee2", edgecolor="#888",
                                  lw=0.8, zorder=1))
        for k in np.arange(-10, 10.1, 1):
            hgt = 1.0 if k % 5 else 1.9
            c.plot([k, k], [7.8, 7.8 - hgt], color="#444", lw=0.8)
            if k % 5 == 0:
                c.text(k, 8.3, "%.0f" % k, ha="center", fontsize=7.5)
        c.plot([-10.5, 10.5], [7.8, 7.8], color="#444", lw=1.0)
        c.plot([0, 0], [-7.6, 7.6], "-.", color="#333", lw=0.8, zorder=2)
        (self.rodtop,) = c.plot([0], [0], "-", color="#101010", lw=6,
                                solid_capstyle="butt", animated=True)
        c.set_xlim(-16, 16)
        c.set_ylim(-8.4, 10.2)
        c.set_aspect("equal")
        c.set_xticks([])
        c.set_yticks([])
        for sp in c.spines.values():
            sp.set_visible(False)

        self.background = None
        self.canvas.draw_idle()

    # ------------------------------------------------ loop
    def _tick(self):
        t0 = time.perf_counter()
        dt = min(t0 - self._last, 0.25)
        self._last = t0

        if self.placed and dt > 0:
            w = self.bench.omega()
            gam = 1.0 / self.tau
            zeq = self.z_equilibrium()
            n = max(1, int(dt / 0.004) + 1)
            hstep = dt / n
            for _ in range(n):
                self.vz += (-w * w * (self.z - zeq)
                            - 2 * gam * self.vz) * hstep
                self.z += self.vz * hstep
            self._jit += (-self._jit / 2.0) * dt + \
                self.bench.rng.normal(0.0, 1.2e-5) * np.sqrt(max(dt, 1e-4))
            ringing = abs(self.vz) > 3e-5 or abs(self.z - zeq) > 3e-5
            self.lbl_state.config(
                text=T("the rod is still swinging - wait")
                if ringing else "")

        if not self.winfo_ismapped():
            self.after(150, self._tick)
            return

        half = self.ROD_LEN / 2 * 1e3
        zc = (self.z + self._jit) * 1e3 if self.placed else 0.0
        self.rodtop.set_data([zc - half, zc + half], [0, 0])
        self.rodtop.set_visible(self.placed)

        x0, ca, sa = self._plank
        px = self._z_centre + zc
        sx = [x0 + (px + q - x0) * ca - 23.0 * sa for q in (-half, half)]
        sy = [14.0 + (px + q - x0) * sa + 23.0 * ca for q in (-half, half)]
        self.rodside.set_data(sx, sy)
        self.rodside.set_visible(self.placed)

        if self.background is None:
            self.canvas.draw()
        self.canvas.restore_region(self.background)
        self.axs.draw_artist(self.rodside)
        self.axt.draw_artist(self.rodtop)
        self.canvas.blit(self.fig.bbox)

        self.after(max(60, int(2500 * (time.perf_counter() - t0))), self._tick)


# ═══════════════════════════ application ═══════════════════════════
class App:
    def __init__(self, root):
        root.title("IPhO 2017 E2 - Parallel Dipole Line Magnetic Trap "
                   "(virtual laboratory)")
        bench = Bench()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        nb.add(PartA1(nb, bench),
               text=T("  Part A1  -  magnetization  (A.1 - A.4)  "))
        nb.add(PartA2(nb, bench),
               text=T("  Part A2  -  levitation and oscillation  (A.5 - A.12)  "))
        nb.add(PartB(nb, bench),
               text=T("  Part B  -  tiltmeter  (B.1 - B.5)  "))


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
