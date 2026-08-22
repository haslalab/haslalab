#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2026 Experimental Problem 1 — "Fiber Bragg Grating"
Virtual FBG-Writer.

Same forward model as the HaslaLab browser version, so the two agree.

    grating period      Lambda = v / f
    Bragg resonance     lam_B  = 2 n_c Lambda
    coupled mode theory a'' = kappa^2 a   ->   T = 1 / cosh^2(kappa L)
    focus height        kappa(dY) = kappa0 exp(-((dY-dY0)/w)^2)
    temperature         d lam_B = lam_B A dt,  A = alpha + (dn/dt)/n_c
    strain              d lam_B = lam_B B F,   B = (1 + (dn/de)/n_c)/(E S)

Nothing is computed for the user.  The interrogator shows a transmission
spectrum and two numbers; n_c, dY0, kappa, A, B and the LDPE solidification
temperature are all left to be measured and fitted by hand.

    python ispho2026_E1_fbg_sim.py
    pyinstaller --onedir --noupx --windowed ispho2026_E1_fbg_sim.py
"""

import math, random, csv
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

LANG = "KO"          # build_editions.py rewrites this line for the EN edition

TXT = {
 "KO": dict(
   title="ISPhO 2026 E1 — 광섬유 브래그 격자",
   tabs=["A  격자 쓰기", "C  온도 보정", "D  응고 곡선", "E  힘 측정"],
   dY="ΔY  초점 높이 (µm)", v="v  스테이지 속도 (mm/s)", L="L  격자 길이 (mm)",
   write="격자를 쓴다", temp="t  수조 온도 (℃)", tau="τ  경과 시간 (분)",
   force="F  가한 힘 (N)", lamB="브래그 파장 λB", tmin="투과 최소 Tmin",
   rec="현재 값 기록", dele="마지막 줄 삭제", csv="CSV로 저장",
   nowrite="아직 격자를 쓰지 않았습니다.",
   note=("f = 1.00 kHz 고정.  nc, ΔY₀, ϰ, 계수 A·B, 응고 온도는 직접 구하세요."),
   cols=("조건", "λB (nm)", "Tmin (dB)")),
 "EN": dict(
   title="ISPhO 2026 E1 — Fiber Bragg Grating",
   tabs=["A  write a grating", "C  temperature", "D  solidification", "E  force"],
   dY="ΔY  focus height (µm)", v="v  stage velocity (mm/s)", L="L  grating length (mm)",
   write="write the grating", temp="t  bath temperature (°C)", tau="τ  elapsed time (min)",
   force="F  applied force (N)", lamB="Bragg wavelength λB", tmin="transmission minimum",
   rec="record this reading", dele="delete last row", csv="save as CSV",
   nowrite="No grating has been written yet.",
   note=("f = 1.00 kHz.  n_c, ΔY0, kappa, A, B and the solidification "
         "temperature are yours to find."),
   cols=("setting", "lambda_B (nm)", "Tmin (dB)")),
}[LANG]

F_PULSE = 1.00e3          # Hz, given in the problem


class Bench:
    """One bench.  Its imperfections are drawn once, at start-up."""

    def __init__(self):
        g = random.gauss
        self.nc     = 1.4500 * (1 + g(0, 0.008))
        self.dY0    = random.uniform(-0.9, 0.9)
        self.wY     = random.uniform(1.05, 1.35)
        self.kap0   = random.uniform(0.055, 0.075)      # 1/mm
        self.floor  = random.uniform(-46, -40)          # dB, background light
        self.alphaT = 5.5e-7 * (1 + g(0, 0.04))         # 1/degC
        self.dndt   = 1.00e-5 * (1 + g(0, 0.04))
        self.E      = 72.0e9 * (1 + g(0, 0.03))         # Pa
        self.S      = math.pi * (62.5e-6) ** 2          # 125 um fibre
        self.dnde   = -0.320 * (1 + g(0, 0.04))
        self.A      = self.alphaT + self.dndt / self.nc
        self.B      = (1 + self.dnde / self.nc) / (self.E * self.S)
        # the grating parts C, D and E are performed with
        self.lam_fixed = 1550.0 * (1 + g(0, 3e-4))
        self.kap_fixed = random.uniform(0.060, 0.070)
        self.L_fixed   = 60.0
        # LDPE cooling
        self.t0      = random.uniform(96, 102)
        self.t_start = random.uniform(128, 134)
        self.t_air   = random.uniform(22, 26)
        self.cool_k  = random.uniform(0.055, 0.075)
        self.plateau = random.uniform(11, 16)

    def kappa(self, dY):
        return self.kap0 * math.exp(-((dY - self.dY0) / self.wY) ** 2)

    def lam(self, v_mm_s):
        return 2 * self.nc * (v_mm_s * 1e-3 / F_PULSE) * 1e9      # nm

    def ldpe(self, tau):
        hit = math.log((self.t_start - self.t_air) /
                       (self.t0 - self.t_air)) / self.cool_k
        if tau < hit:
            return self.t_air + (self.t_start - self.t_air) * math.exp(-self.cool_k * tau)
        if tau < hit + self.plateau:
            return self.t0 + random.gauss(0, 0.03)
        return self.t_air + (self.t0 - self.t_air) * math.exp(-self.cool_k * (tau - hit - self.plateau))

    def t_db(self, kap, L):
        x = kap * L
        t = 1.0 / math.cosh(x) ** 2
        return max(10 * math.log10(max(t, 1e-12)), self.floor)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"])
        self.geometry("1180x760")
        self.b = Bench()
        self.written = False
        self.lam0 = self.kap = self.Lw = 0.0
        self.rows = []
        self._build()
        self._redraw()

    # ─────────────────────────── layout ───────────────────────────
    def _build(self):
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=10); right.pack(side="right", fill="both", expand=True)

        self.nb = ttk.Notebook(left); self.nb.pack(fill="x")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._redraw())
        pans = [ttk.Frame(self.nb, padding=8) for _ in range(4)]
        for p, name in zip(pans, TXT["tabs"]):
            self.nb.add(p, text=name.split()[0])

        self.dY   = self._slider(pans[0], TXT["dY"], -3, 3, 0.0, 0.05)
        self.v    = self._slider(pans[0], TXT["v"], 0.400, 0.700, 0.5345, 0.0005, "%.4f")
        self.L    = self._slider(pans[0], TXT["L"], 0, 1000, 50, 5, "%.0f")
        ttk.Button(pans[0], text=TXT["write"], command=self._write).pack(fill="x", pady=6)
        for s in (self.dY, self.v, self.L):
            s["var"].trace_add("write", lambda *a: self._unwrite())

        self.temp = self._slider(pans[1], TXT["temp"], 25, 100, 25, 0.5)
        self.tau  = self._slider(pans[2], TXT["tau"], 0, 59, 0, 1, "%.0f")
        self.F    = self._slider(pans[3], TXT["force"], 0, 5, 0, 0.05)

        box = ttk.LabelFrame(left, text="", padding=8); box.pack(fill="x", pady=10)
        self.lbl_lam = ttk.Label(box, text="", font=("Consolas", 15, "bold"))
        self.lbl_tmin = ttk.Label(box, text="", font=("Consolas", 15, "bold"))
        self.lbl_lam.pack(anchor="e"); self.lbl_tmin.pack(anchor="e")
        ttk.Button(box, text=TXT["rec"], command=self._record).pack(fill="x", pady=(6, 2))
        ttk.Button(box, text=TXT["dele"], command=self._delete).pack(fill="x", pady=2)
        ttk.Button(box, text=TXT["csv"], command=self._csv).pack(fill="x", pady=2)
        ttk.Label(left, text=TXT["note"], wraplength=250,
                  foreground="#7a8794").pack(fill="x", pady=6)

        self.fig = Figure(figsize=(7.4, 4.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.tree = ttk.Treeview(right, columns=("x", "l", "t"),
                                 show="headings", height=9)
        for c, h in zip(("x", "l", "t"), TXT["cols"]):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="e", width=140 if c == "x" else 110)
        self.tree.pack(fill="x", pady=(8, 0))

    def _slider(self, parent, label, lo, hi, init, step, fmt="%.2f"):
        var = tk.DoubleVar(value=init)
        head = ttk.Frame(parent); head.pack(fill="x", pady=(8, 0))
        ttk.Label(head, text=label).pack(side="left")
        val = ttk.Label(head, text=fmt % init, font=("Consolas", 10, "bold"))
        val.pack(side="right")
        sc = ttk.Scale(parent, from_=lo, to=hi, variable=var, orient="horizontal")
        sc.pack(fill="x")

        def on(*_):
            v = round(var.get() / step) * step
            val.config(text=fmt % v)
            self._redraw()
        var.trace_add("write", on)
        return {"var": var, "fmt": fmt}

    # ─────────────────────────── model ───────────────────────────
    def _unwrite(self):
        self.written = False

    def _write(self):
        self.written = True
        self.lam0 = self.b.lam(self.v["var"].get())
        self.kap = self.b.kappa(self.dY["var"].get())
        self.Lw = self.L["var"].get()
        self._redraw()

    def _spectrum(self):
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            if not self.written:
                return None
            return self.lam0, self.kap, self.Lw
        lam = self.b.lam_fixed
        if tab == 1:
            lam *= 1 + self.b.A * (self.temp["var"].get() - 25)
        elif tab == 2:
            lam *= 1 + self.b.A * (self.b.ldpe(round(self.tau["var"].get())) - 25)
        else:
            lam *= 1 + self.b.B * self.F["var"].get()
        return lam, self.b.kap_fixed, self.b.L_fixed

    def _trace(self):
        sp = self._spectrum()
        if sp is None:
            return None
        lam0, kap, L = sp
        dl = 0.55 + 26 * kap
        lam = np.linspace(lam0 - 4, lam0 + 4, 1400)
        d = (lam - lam0) / dl
        eff = kap / np.sqrt(1 + 9 * d ** 4)
        y = np.array([self.b.t_db(k, L) for k in eff])
        y = y + np.random.normal(0, 0.16, y.size)
        i = int(np.argmin(y))
        return lam, y, lam[i], y[i]

    # ─────────────────────────── view ───────────────────────────
    def _redraw(self):
        tr = self._trace()
        self.ax.clear()
        self.ax.set_xlabel("λ (nm)"); self.ax.set_ylabel("T (dB)")
        self.ax.set_ylim(self.b.floor - 4, 2)
        self.ax.grid(alpha=.25)
        if tr is None:
            self.ax.text(.5, .5, TXT["nowrite"], ha="center", va="center",
                         transform=self.ax.transAxes, color="#98a6b4")
            self.lbl_lam.config(text=f'{TXT["lamB"]}   ---- . --- nm')
            self.lbl_tmin.config(text=f'{TXT["tmin"]}   -- . -- dB')
        else:
            lam, y, lamB, tmin = tr
            self.ax.plot(lam, y, color="#e02424", lw=1.6)
            self.ax.axhline(self.b.floor, color="#b4cadc", ls="--", lw=1)
            self.lbl_lam.config(text=f'{TXT["lamB"]}   {lamB:9.3f} nm')
            self.lbl_tmin.config(text=f'{TXT["tmin"]}   {tmin:8.2f} dB')
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ─────────────────────────── table ───────────────────────────
    def _record(self):
        tr = self._trace()
        if tr is None:
            return
        _, _, lamB, tmin = tr
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            x = f'ΔY={self.dY["var"].get():.2f} v={self.v["var"].get():.4f} L={self.L["var"].get():.0f}'
        elif tab == 1:
            x = f't={self.temp["var"].get():.1f}C'
        elif tab == 2:
            x = f'tau={round(self.tau["var"].get())} min'
        else:
            x = f'F={self.F["var"].get():.2f} N'
        self.rows.append((x, lamB, tmin))
        self.tree.insert("", "end", values=(x, f"{lamB:.3f}", f"{tmin:.2f}"))

    def _delete(self):
        if not self.rows:
            return
        self.rows.pop()
        self.tree.delete(self.tree.get_children()[-1])

    def _csv(self):
        if not self.rows:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         initialfile="ISPhO2026_E1_FBG.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["setting", "lambdaB_nm", "Tmin_dB"])
            for r in self.rows:
                w.writerow([r[0], f"{r[1]:.4f}", f"{r[2]:.3f}"])


if __name__ == "__main__":
    App().mainloop()
