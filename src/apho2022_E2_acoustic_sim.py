#!/usr/bin/env python3
"""APhO 2022 (Dehradun, India, online) -- Experiment 2: Acoustic Black Box.

A line-by-line port of the official browser simulation to Tkinter, so the same
experiment can be done outside a browser.  The source is official/site/ABB/
(simulation.js, Source.js, Detector.js, LinAlg.js, basic.js, graph.js) by
Chandan Relekar, Siddhant Mukherjee, Siddharth Tiwary, Charudutt Kadolkar and
Praveen Pathak; repository github.com/SidM1811/doppler.

The page is reproduced as it stands: the same four detector fields, the same
three graph fields, a "Plot Graph" button and a scatter of the detected
frequency against time.

Hidden source, verbatim from the official simulation.js:

    Source(x, y, z, vx, vy, vz, R, omega) = (300, 500, 0, 81, 43, 0, 120, 1.5)
    r_s(t) = (300 + 81 t + 120 cos 1.5t,  500 + 43 t + 120 sin 1.5t,  0)
    f0 = 991 Hz,  c = 330 m/s

The detected frequency is the retarded-time Doppler shift

    f = f0 (c + v_D.n) / (c - v_S.n)

with the emission time found exactly as LinAlg.find_em does (gradient iteration
with alpha = 0.05), the same 200x step reduction when the sound first arrives,
and the same "drop the first two samples" at the end of initParams.

One quirk of the original is kept so the numbers match: it builds the detector
velocity as (v cos(gamma), v cos(gamma), 0) with gamma in DEGREES -- the
y-component uses cos instead of sin and the angle is never converted to radians.
Tick "physical detector velocity" (or pass --fix-detector-velocity) for the
intended (v cos g, v sin g, 0) with g in radians.  With a stationary detector,
the usual choice, the two agree exactly.

Run:  python apho2022_e2_acoustic_black_box.py
      python apho2022_e2_acoustic_black_box.py --cli --rd 500 --theta 30
"""

import argparse
import math
import sys

SPEED_OF_SOUND = 330.0
SOURCE_FREQUENCY = 991.0
REDUCING_FACTOR = 200

SRC = dict(x=300.0, y=500.0, z=0.0, vx=81.0, vy=43.0, vz=0.0, R=120.0, w=1.5)


def source_pos(t):
    return (SRC["x"] + SRC["vx"] * t + SRC["R"] * math.cos(SRC["w"] * t),
            SRC["y"] + SRC["vy"] * t + SRC["R"] * math.sin(SRC["w"] * t),
            SRC["z"] + SRC["vz"] * t)


def source_vel(t):
    return (SRC["vx"] - SRC["w"] * SRC["R"] * math.sin(SRC["w"] * t),
            SRC["vy"] + SRC["w"] * SRC["R"] * math.cos(SRC["w"] * t),
            SRC["vz"])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mag(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v):
    m = _mag(v)
    return (v[0] / m, v[1] / m, v[2] / m)


def find_em(t, det_pos, eps):
    """LinAlg.find_em: solve t_b + |r_s(t_b) - r_d(t)| / c = t."""
    alpha = 0.05
    t_b = t
    err = t_b + _mag(_sub(source_pos(t_b), det_pos)) / SPEED_OF_SOUND - t
    while err > eps:
        err = t_b + _mag(_sub(source_pos(t_b), det_pos)) / SPEED_OF_SOUND - t
        t_b -= alpha * err
    return t_b


def run(rd, theta_deg, vd, gamma_deg, ti, tf, step, fixed=False):
    """initParams() of the original, returning the (t, f) samples it plots."""
    theta = math.radians(theta_deg)
    d0 = (rd * math.cos(theta), rd * math.sin(theta), 0.0)
    if fixed:
        g = math.radians(gamma_deg)
        dv = (vd * math.cos(g), vd * math.sin(g), 0.0)
    else:
        dv = (vd * math.cos(gamma_deg), vd * math.cos(gamma_deg), 0.0)

    def det_pos(t):
        return (d0[0] + dv[0] * t, d0[1] + dv[1] * t, d0[2] + dv[2] * t)

    out = []
    t = ti
    cur_step = step
    reduced = step / REDUCING_FACTOR
    detected = False
    guard = 0
    while t < tf and guard < 400000:
        guard += 1
        eps = min(1e-10, cur_step)
        dp = det_pos(t)
        t_em = find_em(t, dp, eps)
        if t_em >= 0:
            if not detected:
                t -= cur_step
                cur_step = reduced
                t -= cur_step
                detected = True
                out.append((t, float("nan")))
                t += cur_step
                continue
            cur_step = step
            sp, sv = source_pos(t_em), source_vel(t_em)
            comp_s = _dot(_norm(_sub(dp, sp)), sv)
            comp_d = _dot(_norm(_sub(sp, dp)), dv)
            out.append((t, SOURCE_FREQUENCY *
                        (SPEED_OF_SOUND + comp_d) / (SPEED_OF_SOUND - comp_s)))
        else:
            out.append((t, float("nan")))
        t += cur_step
    return out[2:]


def sanitise(rd, theta, vd, gamma, ti, tf, dt):
    """The blank/negative handling of the original initParams()."""
    if ti < 0:
        ti = 0.0
    if dt < 0.001:
        dt = 0.001
    if tf < ti:
        tf = ti
    if (tf - ti) / dt > 25000:
        tf = ti + 25000 * dt
    if rd < 0:
        rd = 0.0
    return rd, theta, vd, gamma, ti, tf, dt


# ---------------------------------------------------------------------------

def launch_gui():
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    # -- the palette and type of the official page (style.css + materialize) --
    BG = "#06040a"          # body background-color of style.css
    FG = "white"
    PURPLE = "#4a148c"      # the "purple darken-4" of the Plot Graph button
    PURPLE_HI = "#6a1b9a"
    LINK = "#8fadff"        # a { color: rgba(143,173,255,0.979) }
    FIELD = "#1a1526"

    root = tk.Tk()
    root.title("Acoustic Blackbox - APhO 2022 Experiment 2")
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

    # the two centred input rows of simulation.html
    fields = [("rd", "rᴅ (m):", "0"), ("theta", "θ (degrees):", "0"),
              ("vd", "vᴅ (m/s):", "0"), ("gamma", "γ (degrees):", "0"),
              ("ti", "Graph start time, tᵢ (s):", "0"),
              ("tf", "Graph end time, tꜰ (s):", "25"),
              ("dt", "Data-point interval Δ (s):", "0.02")]
    var = {}

    row1 = tk.Frame(root, bg=BG)
    row1.pack(pady=(18, 4))
    row2 = tk.Frame(root, bg=BG)
    row2.pack(pady=(4, 10))
    for n, (key, text, default) in enumerate(fields):
        parent = row1 if n < 4 else row2
        cell = tk.Frame(parent, bg=BG)
        cell.pack(side="left", padx=14)
        label(cell, text, size=10).pack()
        var[key] = tk.StringVar(value=default)
        tk.Entry(cell, textvariable=var[key], width=13, justify="center",
                 bg=FIELD, fg=FG, insertbackground=FG, relief="flat",
                 font=(UI, 10)).pack(ipady=3, pady=(2, 0))

    plot_btn = button(row2, "Plot Graph", lambda: plot_graph())
    plot_btn.pack(side="left", padx=(18, 0))

    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    line, = ax.plot([], [], ".", color="#ffffff", markersize=1.6,
                    label="Frequency (Hz)")
    ax.set_xlabel("Time (s)", color="white", fontsize=13)
    ax.set_ylabel("Frequency (Hz)", color="white", fontsize=13)
    ax.tick_params(colors="white", labelsize=9)
    ax.grid(color=(1, 1, 1, 0.3), linewidth=0.5)
    for s in ax.spines.values():
        s.set_color("white")
    ax.legend(fontsize=9, facecolor=BG, edgecolor="white", labelcolor="white")
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=16)

    info = label(root, "", size=10)
    info.pack(pady=(8, 0))

    fixed = tk.BooleanVar(value=False)
    extra = tk.Frame(root, bg=BG)
    extra.pack(pady=(6, 0))
    tk.Checkbutton(extra, variable=fixed, bg=BG, fg=FG, selectcolor=FIELD,
                   activebackground=BG, activeforeground=FG, bd=0,
                   highlightthickness=0, font=(UI, 9),
                   text="physical detector velocity (not the original's "
                        "quirk)").pack(side="left", padx=(0, 10))
    button(extra, "Export CSV", lambda: save_csv()).pack(side="left")

    tk.Frame(root, bg="#ffffff", height=1).pack(fill="x", padx=24, pady=(16, 12))
    label(root, "This Simulation was developed by Chandan Relekar, Siddhant "
                "Mukherjee, Siddharth Tiwary,\nCharudutt Kadolkar, and Praveen "
                "Pathak for Asian Physics Olympaid-2022 which was held\nat "
                "Dehradun, India.", size=10, justify="center").pack()
    label(root, "https://github.com/SidM1811/doppler", size=10,
          fg=LINK).pack(pady=(6, 16))

    rows = {"data": []}

    def save_csv():
        fn = filedialog.asksaveasfilename(defaultextension=".csv")
        if not fn:
            return
        with open(fn, "w", encoding="utf-8") as fh:
            fh.write("t,f\n")
            for t, f in rows["data"]:
                fh.write("%.6f,%s\n" % (t, "" if f != f else "%.6f" % f))

    def plot_graph():
        try:
            vals = [float(var[k].get() or 0) for k, _l, _d in fields]
        except ValueError:
            info.configure(text="all fields must be numbers")
            return
        rd, theta, vd, gamma, ti, tf, dt = sanitise(*vals)
        for k, v in zip([f[0] for f in fields], (rd, theta, vd, gamma, ti, tf, dt)):
            var[k].set(("%g" % v))
        data = run(rd, theta, vd, gamma, ti, tf, dt, fixed.get())
        rows["data"] = data
        ts = [t for t, f in data if f == f]
        fs = [f for _t, f in data if f == f]
        line.set_data(ts, fs)
        ax.relim()
        ax.autoscale_view()
        canvas.draw_idle()
        if fs:
            info.configure(text="%d points; f from %.2f to %.2f Hz; sound first "
                                "arrives at t = %.3f s"
                                % (len(fs), min(fs), max(fs), ts[0]))
        else:
            info.configure(text="the sound has not reached the detector in this "
                                "time window")

    plot_graph()
    root.update_idletasks()
    root.geometry("%dx%d" % (min(1060, root.winfo_screenwidth() - 60),
                             min(880, root.winfo_screenheight() - 80)))
    root.mainloop()

def launch_cli(args):
    rd, theta, vd, gamma, ti, tf, dt = sanitise(
        args.rd or 0.0, args.theta or 0.0, args.vd, args.gamma,
        args.ti or 0.0, args.tf if args.tf is not None else 25.0,
        args.dt if args.dt is not None else 0.02)
    data = run(rd, theta, vd, gamma, ti, tf, dt, args.fixed)
    print("      t (s)      f (Hz)")
    for t, f in data:
        print("%11.5f %11s" % (t, "-" if f != f else "%.4f" % f))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as fh:
            fh.write("t,f\n")
            for t, f in data:
                fh.write("%.6f,%s\n" % (t, "" if f != f else "%.6f" % f))
        print("\nsaved to %s" % args.csv)


def main():
    ap = argparse.ArgumentParser(description="APhO 2022 E2: Acoustic Black Box")
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--rd", type=float)
    ap.add_argument("--theta", type=float)
    ap.add_argument("--vd", type=float, default=0.0)
    ap.add_argument("--gamma", type=float, default=0.0)
    ap.add_argument("--ti", type=float)
    ap.add_argument("--tf", type=float)
    ap.add_argument("--dt", type=float)
    ap.add_argument("--csv")
    ap.add_argument("--fix-detector-velocity", action="store_true", dest="fixed")
    args = ap.parse_args()
    if args.cli or args.rd is not None:
        launch_cli(args)
    else:
        launch_gui()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
