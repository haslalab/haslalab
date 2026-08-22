#!/usr/bin/env python3
"""
RMPh 2023 -- experimental round: experimental studies in rotating reference frames.

This is the RMPh22 program of the original exam, rebuilt from the shipped
executable.  `official/simulation/RMPh22.exe` is a PyInstaller one-file bundle;
unpacking its CArchive yields the compiled main script, and its constants,
names and bytecode give back the structure below verbatim -- the dialog flow,
the prompts, the physical constants, the equations of motion, the integrator,
the figure setup and the animation are the original ones.

The original header, recovered from the bundle, reads:

    Author: Tudor Mocioi, tudor-gabriel.mocioi@polytechnique.edu

    Animation part based on:
    Matplotlib Animation Example
    author: Jake Vanderplas
    email: vanderplas@astro.washington.edu
    website: http://jakevdp.github.com
    license: BSD
    Please feel free to use and modify this, but keep the above information.

Recovered constants:
    password  'Coriolis'                title 'RMPh2022'
    w = 30 * np.pi / 60                 = pi/2 rad/s
    R = 0.15                            m, so 1 a.u.l. = 15 cm
    v0 = speed_in_cm_per_s / 100        m/s
    fps = 240,  dt = 1 / fps,  t = np.linspace(0, 1, fps)
    cannon 1: 5 to 30 cm/s              cannon 2: np.random.normal(150, 15)
    axes xlim = ylim = (-1.2, 1.2)      = +-8 a.u.l.
    output: <name>.avi, libx264

Two things differ from the original, both forced by the environment rather than
by choice:
  * the original used easygui for its dialogs; this uses easygui when it is
    installed and otherwise draws the same four dialogs with tkinter;
  * .avi writing needs ffmpeg on PATH.  Without it the run still produces the
    numbered PNG sequence (which Tracker opens as a video), an animated GIF and
    the tracked positions as CSV.

Run:  python rmph2023_rotating_frame.py
      python rmph2023_rotating_frame.py --cannon 2 --out fast01     (no dialogs)
"""

import argparse
import math
import os
import sys

import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib import animation
import scipy.integrate as integrate

password = 'Coriolis'
title = 'RMPh2022'

FPS_ANIM = 240


# ---------------------------------------------------------------------------
# dialogs: easygui in the original, tkinter fallback here
# ---------------------------------------------------------------------------
try:
    import easygui
except ImportError:
    easygui = None

if easygui is None:
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    class _EasyGuiShim(object):
        def _root(self):
            r = tk.Tk()
            r.withdraw()
            return r

        def passwordbox(self, msg, title):
            r = self._root()
            v = simpledialog.askstring(title, msg, show="*", parent=r)
            r.destroy()
            return v

        def msgbox(self, msg, title, ok_button="OK"):
            r = self._root()
            messagebox.showinfo(title, msg, parent=r)
            r.destroy()

        def choicebox(self, msg, title, choices):
            r = self._root()
            win = tk.Toplevel(r)
            win.title(title)
            tk.Label(win, text=msg).pack(padx=20, pady=10)
            picked = {"v": None}

            def choose(c):
                picked["v"] = c
                win.destroy()
                r.quit()

            for c in choices:
                tk.Button(win, text=c, width=24,
                          command=lambda c=c: choose(c)).pack(padx=20, pady=4)
            win.protocol("WM_DELETE_WINDOW", lambda: choose(None))
            r.mainloop()
            try:
                r.destroy()
            except tk.TclError:
                pass
            return picked["v"]

        def enterbox(self, msg, title):
            r = self._root()
            v = simpledialog.askstring(title, msg, parent=r)
            r.destroy()
            return v

    easygui = _EasyGuiShim()


# ---------------------------------------------------------------------------
# original dialog chain
# ---------------------------------------------------------------------------

class IntervalError(Exception):
    pass


def interface(msg='Please enter the password:', fieldvalue=None):
    fieldvalue = easygui.passwordbox(msg, title)
    if fieldvalue is None:
        sys.exit(0)
    if fieldvalue != password:
        easygui.msgbox('Wrong password!', title, 'Try again')
        return interface()
    return cannon_choice()


def cannon_choice(msg='Please choose cannon:', cannon=None):
    cannon = easygui.choicebox(msg, title, ['Cannon 1', 'Cannon 2'])
    if cannon is None:
        sys.exit(0)
    if cannon == 'Cannon 1':
        return cannon_1_speed()
    return cannon_2_speed()


def cannon_1_speed(msg='Please enter speed (cm/s)', v0=None):
    raw = easygui.enterbox(msg, title)
    if raw is None:
        sys.exit(0)
    try:
        v0 = float(raw)
        if v0 < 5 or v0 > 30:
            raise IntervalError
    except IntervalError:
        easygui.msgbox('Invalid speed! Only use speeds between 5 cm/s and 30 cm/s',
                       title, 'Try again')
        return cannon_1_speed()
    except ValueError:
        easygui.msgbox('Invalid speed! Only input numbers with . as decimal separator!',
                       title, 'Try again')
        return cannon_1_speed()
    return v0, filename_choice()


def cannon_2_speed():
    v0 = np.random.normal(150, 15)
    return v0, filename_choice()


def filename_choice(msg='Please choose output file name (no extension)'):
    name = easygui.enterbox(msg, title)
    if name is None:
        sys.exit(0)
    return name


# ---------------------------------------------------------------------------
# original physics
# ---------------------------------------------------------------------------

def func(u, t, w):
    x, y, vx, vy = u
    return np.asarray([vx, vy, 2 * w * vy + w ** 2 * x, -2 * w * vx + w ** 2 * y])


def solve(v0_cm_s):
    w = 30 * np.pi / 60
    R = 0.15
    v0 = v0_cm_s / 100
    fps = FPS_ANIM
    u0 = np.asarray([0, R, 0, -v0])
    t = np.linspace(0, 1, fps)
    u = integrate.odeint(func, u0, t, args=(w,))
    return w, R, fps, t, u


def render(u, R, fps, filename):
    """Original figure and animation, written to .avi when ffmpeg is available.

    The frame is drawn in arbitrary units of length, not in metres: the bead
    starts at R = 1 a.u.l. and the window is +-1.2 a.u.l.  That is what the
    official video shows -- its bead starts 0.996 of the way from the centre to
    the window edge, measured straight off the frames -- while the integration
    itself stays in SI."""
    fig = plt.figure(dpi=600)
    ax = plt.axes(xlim=(-1.2, 1.2), ylim=(-1.2, 1.2))
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.set_facecolor('silver')
    circle2 = plt.Circle((0, 0), 0.03, color='red')
    ax.add_patch(circle2)
    line, = ax.plot([], [], 'bo', lw=2, markersize=6)
    ax.set_aspect('equal')

    def init():
        line.set_data([], [])
        return line,

    def animate(i):
        line.set_data([u[i, 0] / R], [u[i, 1] / R])
        return line,

    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=len(u), interval=15, blit=True)

    wrote = None
    if animation.writers.is_available('ffmpeg'):
        try:
            anim.save(filename + '.avi', fps=fps,
                      extra_args=['-vcodec', 'libx264'])
            wrote = filename + '.avi'
        except Exception:                                # noqa: BLE001
            wrote = None
    if wrote is None:
        frames_dir = filename + '_frames'
        os.makedirs(frames_dir, exist_ok=True)
        for i in range(len(u)):
            animate(i)
            fig.savefig(os.path.join(frames_dir, 'frame%04d.png' % i), dpi=110)
        try:
            anim.save(filename + '.gif', writer='pillow', fps=60)
        except Exception:                                # noqa: BLE001
            pass
        wrote = frames_dir
    plt.close(fig)
    return wrote


def write_csv(t, u, R, filename):
    path = filename + '.csv'
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('frame,t (s),x (a.u.l.),y (a.u.l.)\n')
        for i in range(len(t)):
            fh.write('%d,%.6f,%.5f,%.5f\n' % (i, t[i], u[i, 0] / R, u[i, 1] / R))
    return path


def produce(v0_cm_s, name):
    w, R, fps, t, u = solve(v0_cm_s)
    out = render(u, R, fps, name)
    csv = write_csv(t, u, R, name)
    print()
    print('  video/frames : %s' % os.path.abspath(out))
    print('  tracked data : %s' % os.path.abspath(csv))
    print('  1 s at %d fps; the field of view is +-1.2 a.u.l., '
          '1 a.u.l. = R = %g m' % (fps, R))
    print('  open the first PNG in Tracker to reproduce the original workflow')


def main():
    ap = argparse.ArgumentParser(add_help=True,
                                 description='RMPh 2023 rotating-frame experiment')
    ap.add_argument('--cannon', type=int, choices=(1, 2))
    ap.add_argument('--speed', type=float, help='cannon 1 speed in cm/s (5-30)')
    ap.add_argument('--out', help='output name without extension')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        w, R, fps, t, u = solve(150.0)
        x, y = u[:, 0], u[:, 1]
        inside = (np.abs(x / R) <= 1.2) & (np.abs(y / R) <= 1.2)   # a.u.l.
        n = int(np.argmin(inside)) if (~inside).any() else len(t)
        A = np.c_[2 * x[:n], 2 * y[:n], np.ones(n)]
        c = np.linalg.lstsq(A, x[:n] ** 2 + y[:n] ** 2, rcond=None)[0]
        xc, yc = c[0], c[1]
        rho = math.sqrt(c[2] + xc ** 2 + yc ** 2)
        dev = np.abs(np.hypot(x[:n] - xc, y[:n] - yc) - rho).max() / rho
        print('w   = %.4f rad/s   (30*pi/60)' % w)
        print('R   = %g m         -> 1 a.u.l. = %g cm' % (R, R * 100))
        print('cannon 2 at 150 cm/s: %d of %d frames in view' % (n, len(t)))
        print('  fitted circle rho = %.3f m, v0/(2w) = %.3f m, deviation %.1f%%'
              % (rho, 1.5 / (2 * w), 100 * dev))
        print('  arc swept = %.0f deg  (rate 2w = %.3f rad/s)'
              % (math.degrees(2 * w * t[n - 1]), 2 * w))
        for v in (5, 15, 30):
            _, _, _, _, uu = solve(v)
            print('cannon 1 at %2d cm/s: |r|max = %.3f m = %.2f a.u.l.'
                  % (v, np.hypot(uu[:, 0], uu[:, 1]).max(),
                     np.hypot(uu[:, 0], uu[:, 1]).max() / R))
        return

    if args.cannon is None:
        v0, name = interface()
        produce(v0, name)
        return

    if args.cannon == 1:
        if args.speed is None or not (5 <= args.speed <= 30):
            sys.exit('cannon 1 needs --speed between 5 and 30 cm/s')
        v0 = args.speed
    else:
        v0 = float(np.random.normal(150, 15))
    produce(v0, args.out or 'output')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
