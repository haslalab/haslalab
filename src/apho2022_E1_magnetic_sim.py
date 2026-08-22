#!/usr/bin/env python3
"""APhO 2022 (Dehradun, India, online) -- Experiment 1: Magnetic Black Box.

A line-by-line port of the official browser simulation to Tkinter, so that the
same experiment can be done outside a browser.  The source is
official/site/MBB/ (basic.js, simulation.js, Magnet.js, Mobile.js,
Magnetometer.js, Pipe.js, Scale.js, utils.js, user_input.js), written by
Chandan Relekar, Siddhant Mukherjee, Siddharth Tiwary, Charudutt Kadolkar and
Praveen Pathak; repository github.com/SidM1811/pipe.

Everything is kept as in the original:

  canvas 0.2 m wide, height = 1.2 x width, 1 cm grid, y downwards
  mu0/4pi = 1e-7,  dipole moment = 2.0 A m^2
  phone 7.0 x 15.0 cm, magnetometer at (6.0 cm, 1.0 cm) from its top-left corner
  magnet 0.25 x 0.5 cm, mass 0.012 kg,  g = 9.8 m/s^2,  fps = 500
  pipe 12 cm long, 1 cm across, with three damping regions whose constants the
  original's own CSV export prints as "K values in pipe, 1.96, 0.00, 5.88"
  readings saturate at 6500 uT on either axis

  B is the dipole field
      B = (mu0/4pi) m [ 3 (r.m) r / |r|^5 - m / |r|^3 ]
  evaluated exactly as update() does in simulation.js, then rotated into the
  phone frame to give B_w (across the width) and B_l (along the length).

Controls, as in the original page: drag the phone, the magnet, the pipe and the
scale with the mouse; arrow keys nudge the magnet (2X finer / 2X coarser change
the step); sliders rotate each object; Start Measurement records B_w and B_l
against time; Drop releases the magnet.

Run:  python apho2022_e1_magnetic_black_box.py
      python apho2022_e1_magnetic_black_box.py --cli    (text interface)
"""

import math
import sys

# --- constants, from initParams() in the official simulation.js --------------
CANVAS_SIZE = 0.2                 # metres across the canvas
CANVAS_W = 620
CANVAS_H = int(1.2 * CANVAS_W)
SCALING = CANVAS_SIZE / CANVAS_W  # metres per pixel
CONSTANT_PART = 1e-7              # mu0 / 4 pi
DIPOLE_MOMENT = 2.0
MAGNETISM_MULTIPLIER = 1e6        # tesla -> microtesla
B_CRIT = 6.5e3
GRAVITY = 9.8
FPS = 500
DT = 1.0 / FPS

MOBILE_W, MOBILE_H = 0.07, 0.15
MAGNETOMETER_X, MAGNETOMETER_Y = 0.06, 0.01
PIPE_LEN, PIPE_DIA = 0.12, 0.01
MAGNET_LEN, MAGNET_DIA = 0.005, 0.0025
MAGNET_MASS = 0.012
PIPE_K = (1.96, 0.0, 5.88)        # top third, middle, bottom third


def to_radian(a):
    return a * math.pi / 180.0


def clamp(v, lo, hi):
    return max(min(v, hi), lo)


class Rect:
    """Common behaviour of the draggable objects: a rectangle with a centre,
    a rotation angle and corner points, exactly as in the original classes."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width / SCALING
        self.height = height / SCALING
        self.angle = 0.0
        self.points = []
        self.aux = {}
        self.make_rects()

    def make_rects(self):
        w, h = self.width / 2.0, self.height / 2.0
        self.points = [[self.x - w, self.y - h], [self.x + w, self.y - h],
                       [self.x + w, self.y + h], [self.x - w, self.y + h]]
        self.make_aux()

    def make_aux(self):
        """The decorations the original render() methods draw on top of the
        body.  They are kept as plain point lists so that transform() rotates
        them with the body, exactly as the JS classes rotate their screenpoints,
        button centre, camera centre and ticks.  A plain rectangle has none."""
        self.aux = {}

    def all_points(self):
        pts = list(self.points)
        for extra in self.aux.values():
            pts.extend(extra)
        return pts

    def transform(self, angle):
        ta = angle - self.angle
        self.angle = angle
        c, s = math.cos(to_radian(ta)), math.sin(to_radian(ta))
        for p in self.all_points():
            px, py = p[0] - self.x, p[1] - self.y
            p[0] = px * c - py * s + self.x
            p[1] = px * s + py * c + self.y

    def set_pose(self, x, y, angle):
        self.x, self.y = x, y
        self.make_rects()
        self.angle = 0.0
        self.transform(angle)

    def contains(self, x, y):
        n = len(self.points)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = self.points[i]
            xj, yj = self.points[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside


class Mobile(Rect):
    """The phone.  Mobile.render() draws, on top of the translucent grey body,
    the screen outline, the home button, the camera and the two arrows that
    show which way B_w and B_l point."""

    def make_aux(self):
        h = self.height
        w2, h2 = self.width / 2.0, h / 2.0
        sidebezel = (4 / 150.0) * h
        topbezel = (1 / 15.0) * h
        bottombezel = (14 / 150.0) * h
        self.button_radius = (5 / 150.0) * h
        self.camera_radius = (2 / 150.0) * h
        self.aux = {
            "screen": [[self.x - w2 + sidebezel, self.y - h2 + topbezel],
                       [self.x + w2 - sidebezel, self.y - h2 + topbezel],
                       [self.x + w2 - sidebezel, self.y + h2 - bottombezel],
                       [self.x - w2 + sidebezel, self.y + h2 - bottombezel]],
            "button": [[self.x, self.y + (68 / 150.0) * h]],
            "camera": [[self.x, self.y - (70 / 150.0) * h]],
        }

    def arrows(self):
        """makeArrows(): the B_w arrow, then the B_l arrow, each as
        (start_x, start_y, end_x, end_y, label_x, label_y)."""
        p0, p1 = self.points[0], self.points[1]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        out = []
        for theta, turn in ((math.pi / 2, 0.0), (math.pi, math.pi / 2)):
            ct, st = math.cos(theta), math.sin(theta)
            ux, uy = dx * ct + dy * st, -dx * st + dy * ct
            m = math.hypot(ux, uy)
            ux, uy = ux / m * 0.005 / SCALING, uy / m * 0.005 / SCALING
            a = to_radian(self.angle) + turn
            ex, ey = 0.03 * math.cos(a) / SCALING, 0.03 * math.sin(a) / SCALING
            sx, sy = p0[0] + ux, p0[1] + uy
            out.append((sx, sy, sx + ex, sy + ey,
                        sx + ex + 0.01 * math.cos(a) / SCALING,
                        sy + ey + 0.01 * math.sin(a) / SCALING))
        return out


class Scale(Rect):
    """The ruler.  Scale.render() strokes the outline and the ticks only; the
    least count is 2 mm and every fifth tick reaches the middle of the ruler."""

    def make_aux(self):
        lc = 0.002 / SCALING
        w2, h2 = self.width / 2.0, self.height / 2.0
        ticks = []
        i = 1
        while i < self.height / lc:
            y = self.y + i * lc - h2
            ticks.append([self.x if i % 5 == 0 else self.x + self.width / 4.0, y])
            ticks.append([self.x + w2, y])
            i += 1
        self.aux = {"ticks": ticks}


class Magnet(Rect):
    def __init__(self, x, y):
        Rect.__init__(self, x, y, MAGNET_DIA, MAGNET_LEN)
        self.velocity = 0.0
        self.on_ground = False
        self.current_k = 0.0
        self.segment_y0 = y
        self.segment_t0 = 0.0
        self.segment_v0y = 0.0
        self.backup = (x, y, 0.0)

    def make_aux(self):
        w2, h2 = self.width / 2.0, self.height / 2.0
        self.aux = {"north": [[self.x - w2, self.y - h2], [self.x + w2, self.y - h2],
                              [self.x + w2, self.y], [self.x - w2, self.y]]}

    # -- the free / damped fall of Magnet.js ---------------------------------
    def free_fall_distance(self, t0, y0, v0, t1):
        dt = t1 - t0
        return y0 + (0.5 * GRAVITY * dt * dt + v0 * dt) / SCALING

    def free_fall_velocity(self, t0, y0, v0, t1):
        return v0 + GRAVITY * (t1 - t0)

    def damped_fall_distance(self, k, t0, y0, v0, t1):
        dt = t1 - t0
        temp = 0.0 if k * dt / MAGNET_MASS > 40 else math.exp(-k * dt / MAGNET_MASS)
        return y0 + (MAGNET_MASS * GRAVITY * dt / k +
                     MAGNET_MASS / k * (v0 - MAGNET_MASS * GRAVITY / k) *
                     (1 - temp)) / SCALING

    def damped_fall_velocity(self, k, t0, y0, v0, t1):
        dt = t1 - t0
        temp = 0.0 if k * dt / MAGNET_MASS > 40 else math.exp(-k * dt / MAGNET_MASS)
        return ((v0 - MAGNET_MASS * GRAVITY / k) * temp +
                MAGNET_MASS * GRAVITY / k)

    def inside_pipe(self, pipe, y=None):
        y = self.y if y is None else y
        if pipe.points[0][0] < self.x < pipe.points[1][0]:
            top = pipe.points[0][1]
            if top < y < top + 3 * pipe.height / 12:
                return 1
            if top + 3 * pipe.height / 12 < y < top + 7 * pipe.height / 12:
                return 2
            if top + 7 * pipe.height / 12 < y < top + pipe.height:
                return 3
        return 0

    def init_fall(self, pipe, time):
        region = self.inside_pipe(pipe)
        self.current_k = PIPE_K[region - 1] if 1 <= region <= 3 else 0.0
        self.segment_y0 = self.y
        self.segment_t0 = time
        self.segment_v0y = 0.0
        self.velocity = 0.0

    def fall(self, pipe, time):
        old_y = self.y
        k = self.current_k
        region = self.inside_pipe(pipe)
        if k != 0:
            new_y = self.damped_fall_distance(k, self.segment_t0, self.segment_y0,
                                              self.segment_v0y, time)
            new_v = self.damped_fall_velocity(k, self.segment_t0, self.segment_y0,
                                              self.segment_v0y, time)
        else:
            new_y = self.free_fall_distance(self.segment_t0, self.segment_y0,
                                            self.segment_v0y, time)
            new_v = self.free_fall_velocity(self.segment_t0, self.segment_y0,
                                            self.segment_v0y, time)
        new_region = self.inside_pipe(pipe, new_y)
        if new_region != region:
            # the original steps exactly to the boundary and restarts the segment
            self.segment_t0 = time
            self.segment_y0 = new_y
            self.segment_v0y = new_v
            self.current_k = PIPE_K[new_region - 1] if 1 <= new_region <= 3 else 0.0
        self.y = new_y
        self.velocity = new_v
        if self.y + self.height / 2 > CANVAS_H:
            self.y = CANVAS_H - self.height / 2
            self.on_ground = True
            self.velocity = 0.0
            self.segment_v0y = 0.0
        else:
            self.on_ground = False
        for p in self.all_points():
            p[1] += self.y - old_y
        return not self.on_ground


class Magnetometer:
    """Hidden sensor inside the phone (Magnetometer.js)."""

    def __init__(self, mobile):
        self.relative_x = MAGNETOMETER_X / SCALING + mobile.points[0][0] - mobile.x
        self.relative_y = MAGNETOMETER_Y / SCALING + mobile.points[0][1] - mobile.y
        self.angle = 0.0
        self.x = self.y = 0.0
        self.update(mobile)

    def update(self, mobile):
        self.x = mobile.x + self.relative_x
        self.y = mobile.y + self.relative_y

    def transform(self, angle, mobile):
        ta = angle - self.angle
        self.angle = angle
        c, s = math.cos(to_radian(ta)), math.sin(to_radian(ta))
        ox = self.relative_x
        self.relative_x = ox * c - self.relative_y * s
        self.relative_y = ox * s + self.relative_y * c
        self.update(mobile)


class Simulation:
    """State of the whole board, mirroring simulation.js."""

    def __init__(self):
        i, j = 4.23, 4.69                       # grid position of the phone
        mob_x = (i * 0.01 + MOBILE_W / 2) / SCALING
        mob_y = (j * 0.01 + MOBILE_H / 2) / SCALING
        self.mobile = Mobile(mob_x, mob_y, MOBILE_W, MOBILE_H)
        self.magnetometer = Magnetometer(self.mobile)
        self.magnet = Magnet(mob_x + (0.033 + MOBILE_W / 2) / SCALING,
                             CANVAS_H / 2 + 0.014 / SCALING)
        self.pipe = Rect(0.1765 / SCALING, 0.0458 / SCALING + CANVAS_H / 2,
                         PIPE_DIA, PIPE_LEN)
        self.scale = Scale(3 * CANVAS_W / 5, CANVAS_H / 2, 0.02, 0.15)
        self.time = 0.0
        self.falling = False
        self.measuring = False
        self.show_scale = False
        self.fine_factor = 1.0
        self.records = []
        self.magnet.backup = (self.magnet.x, self.magnet.y, self.magnet.angle)

    # -- the field, exactly as update() in simulation.js ---------------------
    def reading(self):
        distance = math.hypot(self.magnet.x - self.magnetometer.x,
                              self.magnet.y - self.magnetometer.y) * SCALING
        if distance == 0:
            return None, None
        disp_x = (self.magnetometer.x - self.magnet.x) * SCALING
        disp_y = (self.magnetometer.y - self.magnet.y) * SCALING
        magnet_x = math.sin(to_radian(self.magnet.angle))
        magnet_y = -math.cos(to_radian(self.magnet.angle))
        rdotm = disp_x * magnet_x + disp_y * magnet_y
        bx = (CONSTANT_PART * DIPOLE_MOMENT *
              (3 * rdotm * disp_x / distance ** 5 - magnet_x / distance ** 3) *
              MAGNETISM_MULTIPLIER)
        by = (CONSTANT_PART * DIPOLE_MOMENT *
              (3 * rdotm * disp_y / distance ** 5 - magnet_y / distance ** 3) *
              MAGNETISM_MULTIPLIER)
        if math.hypot(bx, by) > B_CRIT:
            return None, None
        o = to_radian(self.mobile.angle)
        return (math.cos(o) * bx + math.sin(o) * by,
                -math.sin(o) * bx + math.cos(o) * by)

    def set_mobile_angle(self, angle):
        self.mobile.set_pose(self.mobile.x, self.mobile.y, angle)
        self.magnetometer.transform(angle, self.mobile)

    def move_mobile(self, x, y):
        self.mobile.set_pose(x, y, self.mobile.angle)
        self.magnetometer.update(self.mobile)

    def drop(self):
        if not self.falling and not self.magnet.on_ground:
            self.magnet.backup = (self.magnet.x, self.magnet.y, self.magnet.angle)
            self.magnet.init_fall(self.pipe, self.time)
            self.falling = True

    def reset_magnet(self):
        x, y, a = self.magnet.backup
        self.magnet.velocity = 0.0
        self.magnet.on_ground = False
        self.falling = False
        self.magnet.set_pose(x, y, a)

    def tick(self):
        if self.falling:
            if not self.magnet.fall(self.pipe, self.time):
                self.falling = False
        if self.measuring:
            bw, bl = self.reading()
            self.records.append((self.time,
                                 self.magnet.x * SCALING, self.magnet.y * SCALING,
                                 bw, bl))
            self.time += DT

    def export_csv(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("Magnet in Pipe Simulation Data\n")
            fh.write("Pipe corner points as (x,y) ,")
            for p in self.pipe.points:
                fh.write("%g,%g," % (p[0] * SCALING, p[1] * SCALING))
            fh.write("\n")
            fh.write("K values in pipe, 1.96, 0.00, 5.88 \n")
            fh.write("Magnetometer Location : ,%g,%g\n"
                     % (self.magnetometer.x * SCALING, self.magnetometer.y * SCALING))
            fh.write("Scale Factor = %g\n" % SCALING)
            fh.write("t, Mx, My, Bx, By\n")
            for t, mx, my, bw, bl in self.records:
                fh.write("%g,%g,%g,%s,%s\n"
                         % (t, mx, my, "" if bw is None else "%g" % bw,
                            "" if bl is None else "%g" % bl))
        return path


# ---------------------------------------------------------------------------
# graphical interface, laid out like the original page
# ---------------------------------------------------------------------------

def launch_gui():
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog

    # -- the palette and type of the official page (style.css + materialize) --
    BG = "#06040a"          # body background-color of style.css
    FG = "white"            # every p, b and heading is white there
    PURPLE = "#4a148c"      # the "purple darken-4" every button carries
    PURPLE_HI = "#6a1b9a"
    LINK = "#8fadff"        # a { color: rgba(143,173,255,0.979) }
    GRIDLINE = "#cccccc"    # rgba(0,0,0,0.2) laid over the white canvas
    PHONE = "#bfbfbf"       # rgba(128,128,128,0.5) laid over the white canvas
    FIELD = "#1a1526"

    sim = Simulation()
    root = tk.Tk()
    root.title("Magnetic Blackbox - APhO 2022 Experiment 1")
    root.configure(bg=BG)

    have = set(tkfont.families(root))
    UI = next((f for f in ("Gill Sans MT", "Gill Sans", "Calibri",
                           "Trebuchet MS", "Segoe UI") if f in have),
              "TkDefaultFont")

    def label(parent, text, size=11, bold=False, **kw):
        kw.setdefault("bg", BG)
        kw.setdefault("fg", FG)
        return tk.Label(parent, text=text,
                        font=(UI, size, "bold" if bold else "normal"), **kw)

    def button(parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=PURPLE, fg="white",
                         activebackground=PURPLE_HI, activeforeground="white",
                         relief="flat", bd=0, highlightthickness=0,
                         font=(UI, 10), padx=14, pady=7, cursor="hand2")

    # The page scrolls so that the canvas, the controls, the graph and the
    # credits keep the order they have in simulation.html.
    shell = tk.Canvas(root, bg=BG, highlightthickness=0)
    bar = tk.Scrollbar(root, orient="vertical", command=shell.yview)
    shell.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y")
    shell.pack(side="left", fill="both", expand=True)
    page = tk.Frame(shell, bg=BG)
    shell.create_window((0, 0), window=page, anchor="nw")
    page.bind("<Configure>",
              lambda _e: shell.configure(scrollregion=shell.bbox("all")))
    shell.bind("<MouseWheel>",
               lambda e: shell.yview_scroll(-e.delta // 120, "units"))

    row = tk.Frame(page, bg=BG)
    row.pack(fill="x", padx=24, pady=(18, 0))

    left = tk.Frame(row, bg=BG)
    left.pack(side="left", anchor="n")
    cv = tk.Canvas(left, width=CANVAS_W, height=CANVAS_H, bg="white",
                   highlightthickness=0)
    cv.pack()
    tk.Frame(left, bg="red", height=5).pack(fill="x")   # border-bottom: 5px red

    side = tk.Frame(row, bg=BG)
    side.pack(side="left", anchor="n", fill="both", expand=True, padx=(44, 0))

    label(side, "Intergrid spacing: 1 cm").pack()
    b_display = label(side, "", size=12)
    b_display.pack(pady=8)
    err_display = tk.Label(side, text="Maximum magnetic field exceeded",
                           font=(UI, 10, "bold"), bg="black", fg="white",
                           padx=10, pady=10, highlightbackground="red",
                           highlightcolor="red", highlightthickness=2)

    angles = {}
    for key, text in (("mob", "Rotate mobile:"), ("magnet", "Rotate magnet:"),
                      ("scale", "Rotate scale:")):
        label(side, text, size=10).pack(pady=(10, 0))
        angles[key] = tk.DoubleVar(value=0)
        # a materialize range input: light track, dark thumb, no number
        tk.Scale(side, from_=0, to=359, resolution=1, variable=angles[key],
                 orient="horizontal", length=240, bg=BG, fg=FG,
                 troughcolor="#9b93ad", activebackground=PURPLE_HI,
                 highlightthickness=0, bd=0, sliderrelief="flat",
                 showvalue=0, width=12,
                 command=lambda _v, k=key: rotate(k)).pack()

    label(side, "Graph start time, t_i (s):", size=10).pack(pady=(10, 2))
    t_i = tk.StringVar(value="0")
    tk.Entry(side, textvariable=t_i, width=16, justify="center", bg=FIELD,
             fg=FG, insertbackground=FG, relief="flat",
             font=(UI, 10)).pack(ipady=3)
    label(side, "Graph end time, t_f (s):", size=10).pack(pady=(8, 2))
    t_f = tk.StringVar(value="120")
    tk.Entry(side, textvariable=t_f, width=16, justify="center", bg=FIELD,
             fg=FG, insertbackground=FG, relief="flat",
             font=(UI, 10)).pack(ipady=3)

    status = label(side, "t = 0.000 s", size=10)
    status.pack(pady=(12, 6))

    measure_btn = button(side, "Start Measurement", lambda: measure_toggle())
    measure_btn.pack(pady=4)
    button(side, "Reset Graph", lambda: reset_graph()).pack(pady=4)
    pair = tk.Frame(side, bg=BG)
    pair.pack(pady=4)
    drop_btn = button(pair, "Drop", lambda: sim.drop())
    drop_btn.pack(side="left", padx=3)
    button(pair, "Reset Positions",
           lambda: (sim.reset_magnet(), redraw())).pack(side="left", padx=3)
    button(side, "Export CSV", lambda: save_csv()).pack(pady=4)

    # the graph goes in the space left over beside the canvas, under the
    # controls, instead of below the whole board
    label(side, "B_w & B_l vs t graph", size=14, bold=True).pack(pady=(12, 2))
    fig_frame = tk.Frame(side, bg=BG)
    fig_frame.pack(fill="both", expand=True)

    centre = tk.Frame(page, bg=BG)
    centre.pack(pady=16)
    button(centre, "2X Finer magnet movement",
           lambda: finer()).pack(side="left", padx=4)
    button(centre, "2X Coarser magnet movement",
           lambda: coarser()).pack(side="left", padx=4)
    scale_btn = button(centre, "Show Scale", lambda: scale_toggle())
    scale_btn.pack(side="left", padx=4)

    try:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        fig, ax = plt.subplots(figsize=(3.4, 1.9))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color("white")
        ax.tick_params(colors="white", labelsize=7)
        ax.set_xlabel("Time (s)", color="white", fontsize=9)
        ax.set_ylabel("Magnetic field (μT)", color="white", fontsize=9)
        line_bw, = ax.plot([], [], ".", color="#ffffff", markersize=1.6,
                           label="B_w (in μT)")
        line_bl, = ax.plot([], [], ".", color="#00ff00", markersize=1.6,
                           label="B_l (in μT)")
        ax.grid(color="white", linewidth=0.25)
        ax.legend(fontsize=8, facecolor=BG, edgecolor="white",
                  labelcolor="white")
        fig.tight_layout()
        chart = FigureCanvasTkAgg(fig, master=fig_frame)
        chart.get_tk_widget().pack(fill="both", expand=True)
    except ImportError:
        fig = ax = chart = None
        line_bw = line_bl = None

    tk.Frame(page, bg="#ffffff", height=1).pack(fill="x", padx=24, pady=(18, 12))
    label(page, "This Simulation was developed by Chandan Relekar, Siddhant "
                "Mukherjee, Siddharth Tiwary,\nCharudutt Kadolkar, and Praveen "
                "Pathak for Asian Physics Olympaid-2022 which was held\nat "
                "Dehradun, India.", size=10, justify="center").pack()
    label(page, "https://github.com/SidM1811/pipe", size=10,
          fg=LINK).pack(pady=(6, 18))

    # -- interaction ---------------------------------------------------------
    drag = {"obj": None, "dx": 0.0, "dy": 0.0}

    def rotate(key):
        a = float(angles[key].get())
        if key == "mob":
            sim.set_mobile_angle(a)
        elif key == "magnet":
            sim.magnet.set_pose(sim.magnet.x, sim.magnet.y, a)
        else:
            sim.scale.set_pose(sim.scale.x, sim.scale.y, a)
        redraw()

    def on_press(ev):
        for name, obj in (("magnet", sim.magnet),
                          ("scale", sim.scale if sim.show_scale else None),
                          ("mobile", sim.mobile), ("pipe", sim.pipe)):
            if obj is not None and obj.contains(ev.x, ev.y):
                drag["obj"] = name
                drag["dx"] = obj.x - ev.x
                drag["dy"] = obj.y - ev.y
                return

    def on_move(ev):
        name = drag["obj"]
        if not name or sim.falling:
            return
        x, y = ev.x + drag["dx"], ev.y + drag["dy"]
        if name == "magnet":
            sim.magnet.set_pose(x, y, sim.magnet.angle)
        elif name == "mobile":
            sim.move_mobile(x, y)
        elif name == "pipe":
            sim.pipe.set_pose(x, y, sim.pipe.angle)
        else:
            sim.scale.set_pose(x, y, sim.scale.angle)
        redraw()

    def on_release(_ev):
        drag["obj"] = None

    def on_key(ev):
        step = 0.0002 / SCALING / sim.fine_factor
        dx = {"Left": -step, "Right": step}.get(ev.keysym, 0.0)
        dy = {"Up": -step, "Down": step}.get(ev.keysym, 0.0)
        if dx or dy:
            sim.magnet.set_pose(sim.magnet.x + dx, sim.magnet.y + dy,
                                sim.magnet.angle)
            redraw()

    cv.bind("<Button-1>", on_press)
    cv.bind("<B1-Motion>", on_move)
    cv.bind("<ButtonRelease-1>", on_release)
    root.bind("<Key>", on_key)

    def measure_toggle():
        sim.measuring = not sim.measuring
        measure_btn.configure(text="Pause Measurement" if sim.measuring
                              else "Start Measurement")

    def reset_graph():
        sim.records.clear()
        sim.time = 0.0
        draw_graph()

    def scale_toggle():
        sim.show_scale = not sim.show_scale
        scale_btn.configure(text="Hide Scale" if sim.show_scale
                            else "Show Scale")
        state = "normal" if sim.show_scale else "hidden"
        cv.itemconfigure(item["scale"], state=state)
        for line in item["ticks"]:
            cv.itemconfigure(line, state=state)
        redraw()

    def finer():
        sim.fine_factor *= 2

    def coarser():
        sim.fine_factor /= 2

    def save_csv():
        fn = filedialog.asksaveasfilename(defaultextension=".csv")
        if fn:
            sim.export_csv(fn)

    # -- drawing -------------------------------------------------------------
    # Every item is created once and afterwards only moved.  Deleting and
    # rebuilding the grid and the polygons on each frame is what made the
    # window crawl; Tk keeps the display list itself, so coords() is far
    # cheaper.  The order below is the order of render() in simulation.js:
    # phone, magnet, scale, pipe.
    def flat(pts):
        return [c for p in pts for c in p]

    step = 0.01 / SCALING
    g = 0.0
    while g < CANVAS_W:
        cv.create_line(g, 0, g, CANVAS_H, fill=GRIDLINE)
        g += step
    g = 0.0
    while g < CANVAS_H:
        cv.create_line(0, g, CANVAS_W, g, fill=GRIDLINE)
        g += step

    HEAD = (8.66, 8.66, 5.0)          # the 10 px, 30 deg head of drawArrow()
    BANDS = 32
    item = {}

    # the phone: translucent grey body, screen outline, home button, camera
    item["mobile"] = cv.create_polygon(flat(sim.mobile.points), fill=PHONE,
                                       outline="black")
    item["screen"] = cv.create_polygon(flat(sim.mobile.aux["screen"]), fill="",
                                       outline="black")
    item["button"] = cv.create_oval(0, 0, 0, 0, outline="black", fill="")
    item["camera"] = cv.create_oval(0, 0, 0, 0, outline="black", fill="black")
    item["arrow_w"] = cv.create_line(0, 0, 0, 0, fill="black", arrow="last",
                                     arrowshape=HEAD)
    item["arrow_l"] = cv.create_line(0, 0, 0, 0, fill="black", arrow="last",
                                     arrowshape=HEAD)
    item["b_w"] = cv.create_text(0, 0, text="B", anchor="sw", fill="black",
                                 font=("Calibri", -30))
    item["sub_w"] = cv.create_text(0, 0, text="w", anchor="sw", fill="black",
                                   font=("Calibri", -20))
    item["b_l"] = cv.create_text(0, 0, text="B", anchor="sw", fill="black",
                                 font=("Calibri", -30))
    item["sub_l"] = cv.create_text(0, 0, text="l", anchor="sw", fill="black",
                                   font=("Calibri", -20))

    # the magnet: blue body, red north half, black centre dot of radius 1
    item["magnet"] = cv.create_polygon(flat(sim.magnet.points), fill="#1f51ff",
                                       outline="black")
    item["north"] = cv.create_polygon(flat(sim.magnet.aux["north"]),
                                      fill="#ff1818", outline="black")
    item["core"] = cv.create_oval(0, 0, 0, 0, fill="black", outline="black")

    # the ruler: outline and ticks only, never filled
    item["scale"] = cv.create_polygon(flat(sim.scale.points), fill="",
                                      outline="black", state="hidden")
    item["ticks"] = [cv.create_line(0, 0, 0, 0, fill="black", state="hidden")
                     for _ in range(len(sim.scale.aux["ticks"]) // 2)]

    # the pipe: Pipe.render() fills it with a black -> #888888 -> black
    # gradient across its width; Tk has no gradients, so the same ramp is laid
    # down as thin bands under the outline.
    def band_colour(f):
        v = int(round(0x88 * (1.0 - abs(2.0 * f - 1.0))))
        return "#%02x%02x%02x" % (v, v, v)

    item["bands"] = [cv.create_rectangle(0, 0, 0, 0, width=0,
                                         fill=band_colour((i + 0.5) / BANDS))
                     for i in range(BANDS)]
    item["pipe"] = cv.create_polygon(flat(sim.pipe.points), fill="",
                                     outline="black")

    def redraw():
        m = sim.mobile
        cv.coords(item["mobile"], *flat(m.points))
        cv.coords(item["screen"], *flat(m.aux["screen"]))
        bx, by = m.aux["button"][0]
        r = m.button_radius
        cv.coords(item["button"], bx - r, by - r, bx + r, by + r)
        cx, cy = m.aux["camera"][0]
        r = m.camera_radius
        cv.coords(item["camera"], cx - r, cy - r, cx + r, cy + r)
        (wsx, wsy, wex, wey, wlx, wly), (lsx, lsy, lex, ley, llx, lly) = m.arrows()
        cv.coords(item["arrow_w"], wsx, wsy, wex, wey)
        cv.coords(item["arrow_l"], lsx, lsy, lex, ley)
        cv.coords(item["b_w"], wlx, wly)
        cv.coords(item["sub_w"], wlx + 15, wly + 10)
        cv.coords(item["b_l"], llx - 5, lly)
        cv.coords(item["sub_l"], llx + 7, lly + 10)

        n = sim.magnet
        cv.coords(item["magnet"], *flat(n.points))
        cv.coords(item["north"], *flat(n.aux["north"]))
        cv.coords(item["core"], n.x - 1, n.y - 1, n.x + 1, n.y + 1)

        sc = sim.scale
        cv.coords(item["scale"], *flat(sc.points))
        pts = sc.aux["ticks"]
        for k, line in enumerate(item["ticks"]):
            a, b = pts[2 * k], pts[2 * k + 1]
            cv.coords(line, a[0], a[1], b[0], b[1])

        p = sim.pipe.points
        x0, x1 = p[0][0], p[1][0]
        y0, y1 = p[0][1], p[3][1]
        w = (x1 - x0) / BANDS
        for k, rect in enumerate(item["bands"]):
            cv.coords(rect, x0 + k * w, y0, x0 + (k + 1) * w + 1, y1)
        cv.coords(item["pipe"], *flat(p))

    MAX_POINTS = 1500          # more than the plot can resolve anyway

    def draw_graph():
        if ax is None:
            return
        try:
            lo, hi = float(t_i.get()), float(t_f.get())
        except ValueError:
            lo, hi = 0.0, 120.0
        rows = [r for r in sim.records
                if lo <= r[0] <= hi and r[3] is not None and r[4] is not None]
        if len(rows) > MAX_POINTS:                 # thin out, keep the shape
            k = len(rows) // MAX_POINTS + 1
            rows = rows[::k]
        ts = [r[0] for r in rows]
        line_bw.set_data(ts, [r[3] for r in rows])
        line_bl.set_data(ts, [r[4] for r in rows])
        ax.relim()
        ax.autoscale_view()
        chart.draw_idle()

    frame = {"n": 0, "b": None, "err": False, "t": None}

    def loop():
        for _ in range(10):                     # 10 physics steps per redraw
            sim.tick()
        bw, bl = sim.reading()
        if bw is None:
            btxt, bad = "", True
        else:
            btxt = "B_w: %.2f μT\nB_l: %.2f μT" % (bw, bl)
            bad = False
        # every configure() makes Tk relayout that label, so write only when
        # the text has actually changed
        if btxt != frame["b"]:
            frame["b"] = btxt
            b_display.configure(text=btxt)
        if bad != frame["err"]:
            frame["err"] = bad
            if bad:
                err_display.pack(pady=6)
            else:
                err_display.pack_forget()
        ttxt = "t = %.3f s" % sim.time
        if ttxt != frame["t"]:
            frame["t"] = ttxt
            status.configure(text=ttxt)
        if sim.falling:
            redraw()
        frame["n"] += 1
        if sim.measuring and frame["n"] % 25 == 0:
            draw_graph()
        root.after(20, loop)

    redraw()
    draw_graph()
    root.update_idletasks()
    root.geometry("%dx%d" % (min(1060, root.winfo_screenwidth() - 60),
                             min(900, root.winfo_screenheight() - 80)))
    root.after(20, loop)
    root.mainloop()

# ---------------------------------------------------------------------------

def launch_cli():
    sim = Simulation()
    print(__doc__.split("Controls,")[0].strip())
    print()
    print("commands: phone X Y [A] | magnet X Y [A] | read | scan x|y FROM TO STEP")
    print("          drop | state | quit")
    print("positions in cm; phone X Y is its top-left corner, magnet X Y its centre,")
    print("angles in degrees, y increases downwards, as on the original canvas")
    while True:
        sys.stdout.write("MBB> ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            break
        p = line.split()
        if not p:
            continue
        c = p[0].lower()
        try:
            if c in ("quit", "exit"):
                break
            if c == "phone":
                # X Y is the top-left corner of the unrotated phone, the same
                # reference the original uses for i, j in initParams() and the
                # one "state" prints back
                sim.move_mobile((float(p[1]) / 100 + MOBILE_W / 2) / SCALING,
                                (float(p[2]) / 100 + MOBILE_H / 2) / SCALING)
                if len(p) > 3:
                    sim.set_mobile_angle(float(p[3]))
            elif c == "magnet":
                sim.magnet.set_pose(float(p[1]) / 100 / SCALING,
                                    float(p[2]) / 100 / SCALING,
                                    float(p[3]) if len(p) > 3 else sim.magnet.angle)
            elif c == "read":
                bw, bl = sim.reading()
                print("  saturated" if bw is None
                      else "  B_w = %9.2f uT   B_l = %9.2f uT" % (bw, bl))
            elif c == "scan":
                axis = p[1].lower()
                a, b, d = float(p[2]), float(p[3]), float(p[4])
                x0, y0 = sim.magnet.x, sim.magnet.y
                v = a
                print("  %8s %12s %12s" % (axis + " (cm)", "B_w (uT)", "B_l (uT)"))
                while (d > 0 and v <= b) or (d < 0 and v >= b):
                    if axis == "x":
                        sim.magnet.set_pose(v / 100 / SCALING, y0, sim.magnet.angle)
                    else:
                        sim.magnet.set_pose(x0, v / 100 / SCALING, sim.magnet.angle)
                    bw, bl = sim.reading()
                    print("  %8.2f %12s %12s" % (v, "sat" if bw is None else "%.2f" % bw,
                                                 "sat" if bl is None else "%.2f" % bl))
                    v += d
                sim.magnet.set_pose(x0, y0, sim.magnet.angle)
            elif c == "drop":
                sim.measuring = True
                sim.drop()
                print("  %8s %12s %12s %10s" % ("t (s)", "B_w (uT)", "B_l (uT)", "y (cm)"))
                while sim.falling:
                    sim.tick()
                    if len(sim.records) % 25 == 0:
                        t, _mx, my, bw, bl = sim.records[-1]
                        print("  %8.3f %12s %12s %10.2f"
                              % (t, "sat" if bw is None else "%.2f" % bw,
                                 "sat" if bl is None else "%.2f" % bl, my * 100))
                sim.measuring = False
            elif c == "state":
                print("  phone  top-left (%.2f, %.2f) cm, angle %g deg"
                      % ((sim.mobile.x - sim.mobile.width / 2) * SCALING * 100,
                         (sim.mobile.y - sim.mobile.height / 2) * SCALING * 100,
                         sim.mobile.angle))
                print("  magnet          (%.2f, %.2f) cm, angle %g deg"
                      % (sim.magnet.x * SCALING * 100, sim.magnet.y * SCALING * 100,
                         sim.magnet.angle))
                print("  board is %g cm x %g cm, 1 cm grid, y increases downwards"
                      % (CANVAS_SIZE * 100, CANVAS_H * SCALING * 100))
            else:
                print("  unknown command")
        except (IndexError, ValueError):
            print("  bad arguments")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        s = Simulation()
        print("default geometry: B_w = %.2f uT, B_l = %.2f uT" % s.reading())
        print("magnetometer at (%.3f, %.3f) cm"
              % (s.magnetometer.x * SCALING * 100, s.magnetometer.y * SCALING * 100))
        print("pipe damping constants: %s" % (PIPE_K,))
        sys.exit(0)
    try:
        if "--cli" in sys.argv:
            launch_cli()
        else:
            launch_gui()
    except (KeyboardInterrupt, EOFError):
        print()
