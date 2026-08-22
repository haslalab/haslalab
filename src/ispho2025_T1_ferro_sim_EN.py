#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2025 Theoretical Problem 1 — "Ferromagnetic domain wall dynamics"
Spin-chain simulator.

The same Landau-Lifshitz-Gilbert model the organisers' Ferromagnetic
Simulator integrates, so the answers agree:

    h_eff,k = [ beta*mx', -k1*my + beta*my', k*mz + beta*mz' + b ]
              where m' is the sum of the two neighbouring cells
    m_dot   = -gr (m x h) - alpha*gr ( m (m.h) - h ),   gr = gamma/(1+alpha^2)

Task B starts from a sharp wall at the centre of a chain of N = 201 cells.
Task C shortens the chain to L + 50 cells.

The wall width, its centre and its velocity are left for the user to measure.

    python ispho2025_T1_ferro_sim.py
    pyinstaller --onedir --noupx --windowed ispho2025_T1_ferro_sim.py
"""

import csv
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

LANG = "EN"          # build_editions.py rewrites this line for the EN edition

TXT = {
 "KO": dict(title="ISPhO 2025 T1 — 강자성 자구벽 동역학",
            task="과제", B="B — 자구벽 구조", C="C — 유한 사슬",
            alpha="α  길버트 감쇠", beta="β  교환 상수", b="b  외부 z 자기장",
            T="T  적분 시간", L="L  사슬 길이", run="계산 실행", busy="계산 중…",
            t="t  시각", play="재생 / 정지", csv="CSV로 저장",
            idle="매개변수를 정하고 계산을 실행하세요.",
            note="자구벽의 폭, 중심, 속도는 그래프에서 직접 읽으세요.",
            xlabel="셀 번호 x", ylabel="자화 성분"),
 "EN": dict(title="ISPhO 2025 T1 — Ferromagnetic Domain Wall Dynamics",
            task="Task", B="B — wall structure", C="C — finite chain",
            alpha="alpha  Gilbert damping", beta="beta  exchange", b="b  external z field",
            T="T  integration time", L="L  chain length", run="run", busy="calculating…",
            t="t  time", play="play / pause", csv="save as CSV",
            idle="Set the parameters and run.",
            note="The wall width, its centre and its velocity are yours to read off.",
            xlabel="cell number x", ylabel="magnetisation"),
}[LANG]

K_EASY, K_HARD, GAMMA, NFRAMES = 1.0, 1.0, 1.0, 200


def derivs(m, n, beta, b, alpha):
    """Right-hand side of the LLG equation for the whole chain, vectorised."""
    M = m.reshape(n, 3)
    nb = np.empty_like(M)
    nb[1:-1] = M[:-2] + M[2:]
    nb[0], nb[-1] = M[1], M[-2]
    h = np.empty_like(M)
    h[:, 0] = beta * nb[:, 0]
    h[:, 1] = -K_HARD * M[:, 1] + beta * nb[:, 1]
    h[:, 2] = K_EASY * M[:, 2] + beta * nb[:, 2] + b
    gr = GAMMA / (1 + alpha * alpha)
    cross = np.cross(M, h)
    sp = np.einsum("ij,ij->i", M, h)[:, None]
    return (-gr * cross - alpha * gr * (M * sp - h)).ravel()


def init_B(n, centre=101):
    m = np.zeros((n, 3))
    m[:centre - 2, 2] = 1.0
    m[centre - 2:centre + 3, 0] = 1.0
    m[centre + 3:, 2] = -1.0
    return m.ravel()


def init_C(L):
    """A relaxed wall: the analytic profile the organisers' file stores."""
    n = 50 + L
    x = np.arange(n) - 25.0
    d = 10.0
    m = np.zeros((n, 3))
    m[:, 0] = 1.0 / np.cosh(x / d)
    m[:, 2] = -np.tanh(x / d)
    m /= np.linalg.norm(m, axis=1)[:, None]
    return m.ravel()


def solve(task, alpha, beta, b, Tspan, L, progress=None):
    n = 201 if task == "B" else 50 + L
    m = init_B(n) if task == "B" else init_C(L)
    dt = min(1e-3, 0.15 / max(beta, 1.0))
    total = max(int(round(Tspan / dt)), 1)
    every = max(total // (NFRAMES - 1), 1)
    frames, times = [], []
    for s in range(total):
        k1 = derivs(m, n, beta, b, alpha)
        k2 = derivs(m + dt / 2 * k1, n, beta, b, alpha)
        k3 = derivs(m + dt / 2 * k2, n, beta, b, alpha)
        k4 = derivs(m + dt * k3, n, beta, b, alpha)
        m = m + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if s % every == 0 and len(frames) < NFRAMES:
            frames.append(m.copy()); times.append(s * dt)
        if progress and s % 2000 == 0:
            progress(s / total)
    frames.append(m.copy()); times.append(total * dt)
    return np.array(frames), np.array(times), n


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1120x720")
        self.frames = self.times = self.par = None
        self.n = 0; self.cur = 0; self.playing = False
        self._build(); self._redraw()
        self.after(60, self._tick)

    def _build(self):
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=10); right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text=TXT["task"]).pack(anchor="w")
        self.task = tk.StringVar(value="B")
        for k in ("B", "C"):
            ttk.Radiobutton(left, text=TXT[k], value=k, variable=self.task,
                            command=self._toggleL).pack(anchor="w")

        self.alpha = self._sl(left, TXT["alpha"], 0, 1, 0.5, "%.2f")
        self.beta  = self._sl(left, TXT["beta"], 0, 500, 100, "%.0f")
        self.b     = self._sl(left, TXT["b"], 0, 1, 0.04, "%.3f")
        self.T     = self._sl(left, TXT["T"], 1, 100, 20, "%.0f")
        self.Lfr   = ttk.Frame(left)
        self.L     = self._sl(self.Lfr, TXT["L"], 50, 200, 150, "%.0f")

        self.btn = ttk.Button(left, text=TXT["run"], command=self._run)
        self.btn.pack(fill="x", pady=8)
        self.prog = ttk.Progressbar(left, maximum=1.0); self.prog.pack(fill="x")

        self.tsl = self._sl(left, TXT["t"], 0, NFRAMES, 0, "%.0f", self._seek)
        ttk.Button(left, text=TXT["play"], command=self._play).pack(fill="x", pady=3)
        ttk.Button(left, text=TXT["csv"], command=self._csv).pack(fill="x", pady=3)
        ttk.Label(left, text=TXT["note"], wraplength=240,
                  foreground="#7a8794").pack(fill="x", pady=8)

        self.fig = Figure(figsize=(7.6, 5.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _sl(self, parent, label, lo, hi, init, fmt, cb=None):
        var = tk.DoubleVar(value=init)
        head = ttk.Frame(parent); head.pack(fill="x", pady=(8, 0))
        ttk.Label(head, text=label).pack(side="left")
        val = ttk.Label(head, text=fmt % init, font=("Consolas", 10, "bold"))
        val.pack(side="right")
        ttk.Scale(parent, from_=lo, to=hi, variable=var,
                  orient="horizontal").pack(fill="x")
        var.trace_add("write", lambda *a: (val.config(text=fmt % var.get()),
                                           cb() if cb else None))
        return var

    def _toggleL(self):
        if self.task.get() == "C":
            self.Lfr.pack(fill="x")
        else:
            self.Lfr.pack_forget()

    def _run(self):
        self.btn.config(text=TXT["busy"], state="disabled"); self.update()
        self.par = {"task": self.task.get(), "alpha": self.alpha.get(),
                    "beta": self.beta.get(), "b": self.b.get(),
                    "T": self.T.get(), "L": int(self.L.get())}
        self.frames, self.times, self.n = solve(
            self.task.get(), self.alpha.get(), self.beta.get(), self.b.get(),
            self.T.get(), int(self.L.get()),
            progress=lambda p: (self.prog.config(value=p), self.update_idletasks()))
        self.prog.config(value=1.0)
        self.cur = len(self.frames) - 1
        self.btn.config(text=TXT["run"], state="normal")
        self._redraw()

    def _seek(self):
        if self.frames is None:
            return
        self.cur = min(int(self.tsl.get()), len(self.frames) - 1)
        self._redraw()

    def _play(self):
        self.playing = not self.playing

    def _tick(self):
        if self.playing and self.frames is not None:
            self.cur = (self.cur + 1) % len(self.frames)
            self._redraw()
        self.after(45, self._tick)

    def _redraw(self):
        self.ax.clear()

        self.ax.set_ylim(-1.05, 1.05)
        self.ax.grid(True, which="major", linestyle="-", linewidth=1.0,
                     alpha=0.8, color="gray")
        self.ax.grid(True, which="minor", linestyle="--", linewidth=0.5,
                     alpha=0.5, color="gray")
        self.ax.minorticks_on()
        if self.frames is None:
            self.ax.text(.5, .5, TXT["idle"], ha="center", va="center",
                         transform=self.ax.transAxes, color="#98a6b4")
        else:
            M = self.frames[self.cur].reshape(self.n, 3)
            x = np.arange(self.n)
            for i, (c, lab) in enumerate([("#1f77b4", r"$m_x$"), ("#ff7f0e", r"$m_y$"),
                                          ("#2ca02c", r"$m_z$")]):
                self.ax.plot(x, M[:, i], color=c, lw=1.6, label=lab)
            self.ax.legend()
            p = self.par
            title = (f"[{p['task']}] | Time: {self.times[self.cur]:.2f} / {p['T']:.2f} | "
                     f"$\\alpha$: {p['alpha']:.2f} |  $\\beta$: {p['beta']:.2f} | "
                     f"$b$: {p['b']:.2f}")
            if p["task"] == "C":
                title += f" | $L$: {p['L']:.2f}"
            self.ax.set_title(title)
        self.fig.tight_layout(); self.canvas.draw_idle()

    def _csv(self):
        if self.frames is None:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         initialfile="ISPhO2025_T1.csv")
        if not p:
            return
        M = self.frames[self.cur].reshape(self.n, 3)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["x", "mx", "my", "mz"])
            for i in range(self.n):
                w.writerow([i] + [f"{v:.8e}" for v in M[i]])


if __name__ == "__main__":
    App().mainloop()
