#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2011 (Bangkok, Thailand) - Experimental Problem 2
"Mechanical Blackbox: a cylinder with a ball inside"

HaslaLab virtual laboratory simulator.

    python3 ipho2011_e2.py                 # GUI (Korean)
    python3 ipho2011_e2.py --lang en       # GUI (English)
    python3 ipho2011_e2.py --seed 12345    # fixed session seed
    python3 ipho2011_e2.py --selftest      # virtual-student verification harness

Design rules (HaslaLab):
  * The screen shows ONLY what a real instrument or the naked eye would show.
    No derived quantity, no fit result, no hint, no scoring is ever displayed.
  * Hidden truth (L, z, M/m, g, hole pitch) is randomised per session.
  * Standard library only.
"""

import math
import random
import sys
import tkinter.font as tkfont

# --------------------------------------------------------------------------
# bilingual wrapper
# --------------------------------------------------------------------------
LANG = "ko"


def T(ko, en):
    return ko if LANG == "ko" else en


# reproduces the apparatus of the official 2011 solution sheet
OFFICIAL_SEED = 20110714


# ==========================================================================
#  hidden truth
# ==========================================================================
class Truth:
    """Hidden physical parameters of one apparatus. Never exposed to the user."""

    def __init__(self, seed):
        self.seed = seed
        rng = random.Random(seed)
        official = (seed == OFFICIAL_SEED)

        for _attempt in range(2000):
            if official:
                L = 0.3000
                hole0 = 0.0110
                pitch = 0.0100
                n_holes = 16
                ratio = 2.66744
                z = 0.252688
                g = 9.8100
                d_out = 0.0220
            else:
                L = rng.uniform(0.280, 0.320)
                hole0 = rng.uniform(0.0090, 0.0140)
                pitch = 0.0100
                n_holes = None
                ratio = rng.uniform(2.20, 3.40)
                z = rng.uniform(0.78 * L, 0.90 * L)
                g = rng.uniform(9.780, 9.830)
                d_out = rng.uniform(0.0205, 0.0235)

            m = 0.02500
            M = ratio * m
            x_cm = (m * z + M * L / 2.0) / (M + m)
            I_cm = (M * L * L / 12.0
                    + M * (x_cm - L / 2.0) ** 2
                    + m * (z - x_cm) ** 2)
            r = I_cm / (M + m)
            R_min = math.sqrt(r)

            if n_holes is None:
                n_holes = int((x_cm - 0.016 - hole0) / pitch) + 1
            holes = [hole0 + i * pitch for i in range(n_holes)]
            R_list = [x_cm - h for h in holes]

            if n_holes < 12:
                continue
            if min(R_list) < 0.0140:
                continue
            if not (min(R_list) + 0.008 < R_min < max(R_list) - 0.020):
                continue
            if z > L - 0.012:
                continue
            break

        self.L = L
        self.d_out = d_out
        self.d_in = d_out - 0.0030
        self.m = m
        self.M = M
        self.z = z
        self.g = g
        self.holes = holes          # distance of each hole from the top [m]
        self.x_cm = x_cm
        self.I_cm = I_cm
        self.r = r
        self.R_min = R_min
        self.d_ball = 0.0130
        # height of the bench top below the pin: clear of the longest swing
        self.bench_y = max(0.300, L - holes[0] + 0.012)



# ==========================================================================
#  the rig  (single source of truth for GUI *and* verification harness)
# ==========================================================================
# balance-loop contact model
LOOP_LEVER = 0.0250        # effective contact half-height  [m]
LOOP_DEADBAND = 0.00030    # loop band half-width           [m]
LOOP_MU_S = 0.78           # tightly tied loop on aluminium
LOOP_MU_K = 0.68
EYE_LEVEL_DEG = 0.55       # below this the eye calls the cylinder level
LOOP_DROP = 0.115          # thread length from the pin down to the loop [m]
RULER_LEN = 0.350          # length of the scale on the ruler [m]
RULER_H = 0.030            # width of the ruler body [m]
RULER_REACH = 0.038        # how far from the scale a mark can still be read
PENCIL_LEN = 0.110         # pencil length [m]
PENCIL_U, PENCIL_V = 0.80, 0.60      # unit vector point -> far end
ERASER_W = 0.042           # rubber block, along the tube  [m]
ERASER_H = 0.019           # rubber block, across the tube [m]


class Rig:
    """
    Public API used by the GUI and by the virtual student.
    Nothing here returns a derived physical quantity: only instrument
    readings and what is visible on the bench.
    """

    def __init__(self, truth, rng=None):
        self.truth = truth
        self.rng = rng or random.Random(truth.seed ^ 0x5EED)
        self.t = 0.0
        self.reset_all()

    # the apparatus is fixed: base plate + thin pin as one pre-installed
    # unit, ruler and pencil on the bench, stopwatch in the hand.

    # ---------------- assembly ------------------------------------------
    def reset_all(self):
        self.loop_present = True      # thread loop hanging on the pin
        self.mode = None      # None | "balance" | "pendulum" | "free"
        self.thread_x = None          # loop position from cylinder top [m]
        self.hole_index = None
        self.sel_hole = None
        self.tilt = 0.0               # rad, +: bottom end (right) low
        self.tilt_v = 0.0
        self.slipping = False
        self.fallen = False
        self.theta = 0.0              # pendulum angle [rad]
        self.omega = 0.0
        self.released = False
        self.marks = []               # pencil marks, m from top
        self.carried = False          # cylinder in the student's hand
        self.held = False
        self.sw_running = False
        self.sw_t0 = 0.0
        self.sw_value = 0.0
        # hand tools: world positions in metres, pin at the origin
        self.ruler_pos = [-self.truth.L * 0.60,
                          self.truth.bench_y + 0.022]
        self.ruler_angle = 0.0        # rotation of the ruler about its 0 mark
        self.pencil_pos = [0.075, self.truth.bench_y + 0.030]
        self.eraser_pos = [0.150, self.truth.bench_y + 0.030]
        self.free_pos = [0.0, self.truth.bench_y - self.truth.d_out * 0.5]
        self.carry_pos = None

    @staticmethod
    def _msg(s):
        return False, s

    def mount_on_loop(self, x=None):
        """Put the cylinder inside the hanging thread loop (balance setup)."""
        if not self.loop_present:
            return self._msg('먼저 실 고리를 핀에 거세요.')
        if self.mode == "pendulum":
            return self._msg('원통이 이미 핀에 걸려 있습니다.')
        self.mode = "balance"
        self.thread_x = self.truth.L * 0.5 if x is None else x
        self.tilt = 0.0
        self.tilt_v = 0.0
        self.slipping = False
        self.fallen = False
        self.carried = False
        self.held = False
        self._fall_v = 0.0
        self._fall_drop = 0.0
        return True, '원통을 실 고리 안에 넣었습니다. 고리를 좌우로 끌어 균형을 맞추세요.'

    def mount_on_pin(self, hole_index=0):
        """Hang the cylinder on the pin through one of the drilled holes."""
        if self.mode == "balance":
            return self._msg('실 고리를 먼저 치우세요.')
        if not (0 <= hole_index < len(self.truth.holes)):
            return self._msg('그런 구멍은 없습니다.')
        self.mode = "pendulum"
        self.hole_index = hole_index
        self.theta = 0.0
        self.omega = 0.0
        self.released = False
        self.fallen = False
        return True, '원통을 핀에 걸었습니다.'

    def enter_part_a(self):
        """Part A - the cylinder hangs in a thread loop on the pin."""
        if self.mode == "balance":
            return True, ""
        x = self.thread_x if self.thread_x is not None else self.truth.L * 0.5
        self.mode = None
        self.hole_index = None
        self.sel_hole = None
        self.loop_present = True
        ok, m = self.mount_on_loop(x)
        self.hold(True)
        return ok, m

    def enter_part_b(self):
        """Part B - the cylinder lies on the bench, ready to hang on the pin."""
        if self.mode in ("pendulum", "free"):
            return True, ""
        self.mode = "free"
        self.loop_present = False
        self.free_pos = [0.0, self.truth.bench_y - self.truth.d_out * 0.5]
        self.theta = self.omega = 0.0
        self.released = False
        self.fallen = False
        self.sel_hole = None
        self.hole_index = None
        return True, '원통을 실험대에 내려놓았습니다.'

    def select_hole(self, i):
        if not (0 <= i < len(self.truth.holes)):
            return False, ""
        self.sel_hole = i
        return True, '구멍 #%d 를 선택했습니다. 이제 핀 구멍을 클릭하세요.' % (i + 1)

    def connect_selected_to_pin(self):
        if self.sel_hole is None:
            return self._msg('먼저 원통의 진자 구멍을 클릭하세요.')
        return self.mount_on_pin(self.sel_hole)

    def unmount_from_pin(self):
        if self.mode != "pendulum":
            return False, ""
        self.mode = "free"
        self.hole_index = None
        self.theta = self.omega = 0.0
        self.released = False
        return True, '원통을 핀에서 뺐습니다.'

    def take_cylinder_off(self):
        self.mode = None
        self.hole_index = None
        self.thread_x = None
        self.theta = self.omega = 0.0
        self.tilt = self.tilt_v = 0.0
        self.released = False
        self.slipping = False
        self.fallen = False
        self.carried = False
        return True, '원통을 내려놓았습니다.'

    def take_thread_off(self):
        if self.mode == "balance":
            self.take_cylinder_off()
        self.loop_present = False
        return True, '실 고리를 치웠습니다.'

    # ---------------- bench actions --------------------------------------
    def drag_loop_to(self, x):
        """Slide the thread loop along the cylinder axis. x: m from the top."""
        if self.mode != "balance" or self.fallen:
            return False, ""
        self.thread_x = max(0.004, min(self.truth.L - 0.004, x))
        return True, ""

    def catch(self):
        """Stop a slipping tube with the finger, or grab it in mid-air."""
        if self.mode != "balance":
            return False, ""
        if self.fallen:
            return self.pick_up_cylinder()
        self.hold(True)
        return True, '손가락으로 받쳐 멈췄습니다.'

    def hold(self, on):
        """Support the cylinder with one hand (True) or let go (False)."""
        if self.mode != "balance":
            return False, ""
        self.held = bool(on)
        if self.held:
            self.slipping = False
            self._slide_v = 0.0
        return True, ('원통을 손으로 받치고 있습니다.' if self.held else
                      '손을 떼었습니다.')

    def nudge_loop(self, delta):
        """Move the thread loop along the axis by delta metres (mouse wheel)."""
        if self.mode != "balance" or self.fallen or self.thread_x is None:
            return False, ""
        return self.drag_loop_to(self.thread_x + delta)

    def pick_up_cylinder(self):
        """Pick the slipped-out cylinder up off the bench."""
        if self.mode != "balance" or not self.fallen:
            return False, ""
        self.carried = True
        return True, '원통을 집었습니다. 실 고리에 가져다 대고 클릭하세요.'

    def insert_into_loop(self):
        """Slide the carried cylinder back through the hanging loop."""
        if not self.carried:
            return False, ""
        x = self.thread_x if self.thread_x is not None else self.truth.L * 0.5
        self.carried = False
        self.mode = None
        self.loop_present = True
        ok, m = self.mount_on_loop(min(max(x, 0.006), self.truth.L - 0.006))
        self.hold(True)
        return ok, '원통을 다시 실 고리에 끼웠습니다.'

    def pull_aside(self, angle_deg):
        if self.mode != "pendulum" or self.fallen:
            return False, ""
        self.theta = math.radians(angle_deg)
        self.omega = 0.0
        self.released = False
        return True, ""

    def release(self):
        if self.mode != "pendulum":
            return self._msg('먼저 원통을 핀에 거세요.')
        self.released = True
        return True, ""

    def stop_swing(self):
        self.released = False
        self.theta = 0.0
        self.omega = 0.0
        return True, ""

    # ---------------- world geometry -------------------------------------
    def cyl_world(self):
        """(x, y of the top end face, ux, uy) in metres, pin at the origin."""
        tr = self.truth
        if self.mode == "balance":
            if self.carried and self.carry_pos is not None:
                return (self.carry_pos[0] - tr.L * 0.5, self.carry_pos[1],
                        1.0, 0.0)
            cx, cy = 0.0, LOOP_DROP + self.fall_drop()
            ux, uy = math.cos(self.tilt), math.sin(self.tilt)
            grip = tr.L * 0.5 if self.fallen else self.thread_x
            return cx - ux * grip, cy - uy * grip, ux, uy
        if self.mode == "pendulum":
            ux, uy = math.sin(self.theta), math.cos(self.theta)
            s = tr.holes[self.hole_index]
            return -ux * s, -uy * s, ux, uy
        if self.mode == "free":
            return (self.free_pos[0] - tr.L * 0.5, self.free_pos[1], 1.0, 0.0)
        return 0.0, 0.0, 0.0, 1.0

    def axial_of(self, x, y):
        """Axial and transverse coordinate of a world point, in metres."""
        ox, oy, ux, uy = self.cyl_world()
        return ((x - ox) * ux + (y - oy) * uy,
                -(x - ox) * uy + (y - oy) * ux)

    def on_cylinder(self, x, y, pad=0.0):
        s, t = self.axial_of(x, y)
        return (-pad <= s <= self.truth.L + pad
                and abs(t) <= self.truth.d_out * 0.5 + pad)

    def feature_world(self, feat):
        s = self.feature_position(feat)
        if s is None:
            return None
        ox, oy, ux, uy = self.cyl_world()
        return ox + ux * s, oy + uy * s

    # ---------------- hand tools ------------------------------------------
    def move_ruler(self, x, y):
        self.ruler_pos = [x, y]

    def rotate_ruler(self, d_rad, px=None, py=None):
        """Turn the ruler; about (px, py) when a pivot is given."""
        if px is not None:
            dx = self.ruler_pos[0] - px
            dy = self.ruler_pos[1] - py
            c, sn = math.cos(d_rad), math.sin(d_rad)
            self.ruler_pos = [px + dx * c - dy * sn, py + dx * sn + dy * c]
        self.ruler_angle = (self.ruler_angle + d_rad) % (2.0 * math.pi)

    def ruler_frame(self, x, y):
        """A world point in the ruler's own frame: (along scale, across)."""
        dx = x - self.ruler_pos[0]
        dy = y - self.ruler_pos[1]
        c, sn = math.cos(self.ruler_angle), math.sin(self.ruler_angle)
        return dx * c + dy * sn, -dx * sn + dy * c

    def on_ruler(self, x, y):
        s, t = self.ruler_frame(x, y)
        return -0.010 <= s <= RULER_LEN + 0.010 and abs(t) <= RULER_H * 0.5

    def ruler_read(self, feat):
        """
        The graduation of the ruler that lies against a given feature, in
        centimetres.  Returns None when the feature is not alongside the
        scale - exactly like looking at a ruler that is out of position.
        """
        p = self.feature_world(feat)
        if p is None:
            return None
        s, t = self.ruler_frame(*p)
        if s < -0.002 or s > RULER_LEN + 0.002 or abs(t) > RULER_REACH:
            return None
        return round(s * 100.0 + self.rng.uniform(-0.035, 0.035), 1)

    def pencil_to(self, x, y, drawing=False):
        """Move the pencil; while pressed the point marks the tube."""
        self.pencil_pos = [x, y]
        if not drawing:
            return False, ""
        s, t = self.axial_of(x, y)
        if 0.0 <= s <= self.truth.L and abs(t) <= self.truth.d_out * 0.5:
            if all(abs(s - m) > 0.0008 for m in self.marks):
                self.marks.append(s)
                return True, ""
        return False, ""

    def on_eraser(self, x, y):
        ex, ey = self.eraser_pos
        return (abs(x - ex) <= ERASER_W * 0.5 + 0.004
                and abs(y - ey) <= ERASER_H * 0.5 + 0.004)

    def eraser_to(self, x, y, rubbing=False):
        """Move the rubber; while pressed it wipes the marks it passes over."""
        self.eraser_pos = [x, y]
        if not rubbing:
            return False, ""
        s, t = self.axial_of(x, y)
        if abs(t) <= self.truth.d_out * 0.5 + ERASER_H * 0.5:
            keep = [m for m in self.marks if abs(m - s) > ERASER_W * 0.5]
            if len(keep) != len(self.marks):
                self.marks = keep
                return True, ""
        return False, ""

    def on_pencil(self, x, y):
        px, py = self.pencil_pos
        s = (x - px) * PENCIL_U + (y - py) * PENCIL_V
        t = -(x - px) * PENCIL_V + (y - py) * PENCIL_U
        return -0.006 <= s <= PENCIL_LEN + 0.005 and abs(t) <= 0.011

    # ---------------- instruments ----------------------------------------
    def stopwatch_start(self):
        if self.sw_running:
            return False, ""
        self.sw_running = True
        # human reaction time on the button
        self.sw_t0 = self.t + self.rng.gauss(0.0, 0.070)
        return True, ""

    def stopwatch_stop(self):
        if not self.sw_running:
            return False, ""
        self.sw_running = False
        self.sw_value = max(0.0, (self.t + self.rng.gauss(0.0, 0.070))
                            - self.sw_t0)
        return True, ""

    def stopwatch_reset(self):
        self.sw_running = False
        self.sw_value = 0.0
        return True, ""

    def stopwatch_display(self):
        """String exactly as printed on the LCD (0.01 s resolution)."""
        v = (self.t - self.sw_t0) if self.sw_running else self.sw_value
        v = max(0.0, v)
        return "%02d:%05.2f" % (int(v // 60), v % 60.0)

    def stopwatch_seconds(self):
        """The reading as a number - exactly what the LCD shows."""
        v = (self.t - self.sw_t0) if self.sw_running else self.sw_value
        return round(max(0.0, v), 2)

    # ---- ruler ----------------------------------------------------------
    def feature_position(self, feat):
        """Axial coordinate (m from the top of the cylinder) of a snap feature."""
        kind = feat[0]
        if kind == "top":
            return 0.0
        if kind == "bottom":
            return self.truth.L
        if kind == "hole":
            return self.truth.holes[feat[1]]
        if kind == "loop":
            if self.thread_x is None:
                return None
            return self.thread_x
        if kind == "mark":
            if not self.marks:
                return None
            return self.marks[feat[1]]
        if kind == "axial":
            return feat[1]
        return None

    # ---------------- what the eye sees ----------------------------------
    def bench_readout(self):
        """Everything visible on the bench. No derived physics."""
        out = {"mode": self.mode, "fallen": self.fallen}
        if self.mode == "balance":
            deg = math.degrees(self.tilt)
            if self.carried:
                view = "carried"
            elif self.held:
                view = "held"
            elif self.fallen:
                view = "fallen"
            elif abs(deg) < EYE_LEVEL_DEG:
                view = "level"
            elif deg > 0:
                view = "bottom_down"
            else:
                view = "top_down"
            out["tilt_view"] = view
            out["sliding"] = self.slipping
        elif self.mode == "free":
            out["selected_hole"] = self.sel_hole
        elif self.mode == "pendulum":
            out["angle_deg"] = round(math.degrees(self.theta) * 2.0) / 2.0
            out["swinging"] = self.released
            out["hole"] = self.hole_index
        out["stopwatch"] = self.stopwatch_display()
        return out

    def status_line(self):
        r = self.bench_readout()
        if r["mode"] is None:
            return '실험대 준비 중'
        if r["mode"] == "free":
            if self.sel_hole is None:
                return 'Part B - 원통의 진자 구멍을 클릭하세요.'
            return 'Part B - 구멍 #%d 선택됨. 핀 구멍을 클릭하세요.' % (
                         self.sel_hole + 1)
        if r["mode"] == "balance":
            d = {"level": '수평',
                 "bottom_down": '아래쪽 끝이 내려감',
                 "top_down": '위쪽 끝이 내려감',
                 "carried": '손에 들고 있음',
                 "held": '손으로 받치는 중 - 좌클릭으로 손을 떼세요',
                 "fallen": '원통이 빠져 떨어짐 - 클릭해서 집으세요'}
            s = '균형 실험 - ' + d[r["tilt_view"]]
            if r.get("sliding"):
                s += '  (미끄러지는 중!)'
            return s
        return ('진자 실험 - 구멍 #%d, 기울기 %.1f deg'
                % (r["hole"] + 1, r["angle_deg"]))

    # ---------------- time stepping --------------------------------------
    def step(self, dt):
        self.t += dt
        if self.mode == "free":
            return
        if self.mode == "balance":
            if self.carried:
                return
            if self.fallen:
                self._step_fall(dt)
            else:
                self._step_balance(dt)
        elif self.mode == "pendulum" and not self.fallen:
            self._step_pendulum(dt)

    def fall_drop(self):
        """How far the cylinder has dropped after slipping out of the loop."""
        return getattr(self, "_fall_drop", 0.0)

    def _step_fall(self, dt):
        v = getattr(self, "_fall_v", 0.0) + self.truth.g * dt
        d = self.fall_drop() + v * dt
        limit = self.truth.bench_y - LOOP_DROP - self.truth.d_out * 0.5
        if d >= limit:
            d, v = limit, 0.0
            self.tilt = 0.0
            self.tilt_v = 0.0
        self._fall_v = v
        self._fall_drop = d

    def _step_balance(self, dt):
        tr = self.truth
        if self.held:
            self.tilt += (0.0 - self.tilt) * min(1.0, 14.0 * dt)
            self.tilt_v = 0.0
            self.slipping = False
            self._slide_v = 0.0
            return
        d = tr.x_cm - self.thread_x
        if abs(d) <= LOOP_DEADBAND:
            d_eff = 0.0
        else:
            d_eff = d - math.copysign(LOOP_DEADBAND, d)
        target = math.atan2(d_eff, LOOP_LEVER)

        # settle towards the equilibrium tilt (damped 2nd order)
        w0, zeta = 11.0, 0.42
        acc = w0 * w0 * (target - self.tilt) - 2.0 * zeta * w0 * self.tilt_v
        self.tilt_v += acc * dt
        self.tilt += self.tilt_v * dt

        limit = math.atan(LOOP_MU_S)
        if abs(self.tilt) > limit:
            self.slipping = True
        if self.slipping:
            mu = LOOP_MU_K
            a = tr.g * (abs(math.sin(self.tilt)) - mu * math.cos(self.tilt))
            if a <= 0.0:
                self.slipping = False
                self._slide_v = 0.0
            else:
                self._slide_v = getattr(self, "_slide_v", 0.0) + a * dt
                # the cylinder runs down-slope: contact point moves up-slope
                self.thread_x -= math.copysign(self._slide_v * dt, d)
                if self.thread_x < 0.0 or self.thread_x > tr.L:
                    self.fallen = True
                    self.slipping = False
                    self._fall_v = 0.0
                    self._fall_drop = 0.0
        else:
            self._slide_v = 0.0

    def _step_pendulum(self, dt):
        if not self.released:
            return
        tr = self.truth
        R = tr.x_cm - tr.holes[self.hole_index]
        Ip = tr.I_cm + (tr.M + tr.m) * R * R
        Wg = (tr.M + tr.m) * tr.g * R
        b = 2.0 * Ip / 78.0                     # light air/pivot damping

        def acc(th, om):
            return (-Wg * math.sin(th) - b * om) / Ip

        # RK4
        k1v = acc(self.theta, self.omega)
        k1x = self.omega
        k2v = acc(self.theta + 0.5 * dt * k1x, self.omega + 0.5 * dt * k1v)
        k2x = self.omega + 0.5 * dt * k1v
        k3v = acc(self.theta + 0.5 * dt * k2x, self.omega + 0.5 * dt * k2v)
        k3x = self.omega + 0.5 * dt * k2v
        k4v = acc(self.theta + dt * k3x, self.omega + dt * k3v)
        k4x = self.omega + dt * k3v
        self.theta += dt / 6.0 * (k1x + 2 * k2x + 2 * k3x + k4x)
        self.omega += dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)
        if self.theta > math.pi:                   # full rotation allowed
            self.theta -= 2.0 * math.pi
        elif self.theta < -math.pi:
            self.theta += 2.0 * math.pi


# ==========================================================================
#  analysis the *student* performs  (never used by the engine)
# ==========================================================================
def linfit(xs, ys):
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    den = n * sxx - sx * sx
    a = (n * sxy - sx * sy) / den
    b = (sy - a * sx) / n
    # residual-based uncertainties
    res = [y - (a * x + b) for x, y in zip(xs, ys)]
    s2 = sum(e * e for e in res) / max(1, n - 2)
    da = math.sqrt(s2 * n / den)
    db = math.sqrt(s2 * sxx / den)
    return a, b, da, db


def _quadfit(xs, ys):
    """Least-squares y = A x^2 + B x + C  (3x3 normal equations)."""
    n = len(xs)
    s = [sum(x ** k for x in xs) for k in range(5)]
    t = [sum(y * x ** k for x, y in zip(xs, ys)) for k in range(3)]
    Mx = [[s[4], s[3], s[2]],
          [s[3], s[2], s[1]],
          [s[2], s[1], float(n)]]
    v = [t[2], t[1], t[0]]
    # Gaussian elimination
    for i in range(3):
        p = max(range(i, 3), key=lambda k: abs(Mx[k][i]))
        Mx[i], Mx[p] = Mx[p], Mx[i]
        v[i], v[p] = v[p], v[i]
        for k in range(i + 1, 3):
            f = Mx[k][i] / Mx[i][i]
            for j in range(i, 3):
                Mx[k][j] -= f * Mx[i][j]
            v[k] -= f * v[i]
    out = [0.0, 0.0, 0.0]
    for i in (2, 1, 0):
        out[i] = (v[i] - sum(Mx[i][j] * out[j] for j in range(i + 1, 3))) / Mx[i][i]
    return out


def solve_blackbox(L_cm, xcm_cm, alpha, beta):
    """
    From the straight-line fit  T^2 R = alpha R^2 + beta   (cm, s units)
    recover g [cm/s^2], r = I_cm/(M+m) [cm^2], z [cm] and M/m.
    """
    g = 4.0 * math.pi ** 2 / alpha
    r = beta / alpha
    c = xcm_cm - L_cm / 2.0
    A = c
    B = L_cm * L_cm / 12.0 + c * c - r
    C = -r * c
    disc = B * B - 4 * A * C
    u = (-B + math.sqrt(disc)) / (2 * A)
    return g, r, xcm_cm + u, u / c


def solve_minimum(L_cm, xcm_cm, R_min_cm, T_min):
    g = 8.0 * math.pi ** 2 * R_min_cm / (T_min ** 2)
    r = R_min_cm ** 2
    c = xcm_cm - L_cm / 2.0
    A, B, C = c, L_cm * L_cm / 12.0 + c * c - r, -r * c
    u = (-B + math.sqrt(B * B - 4 * A * C)) / (2 * A)
    return g, r, xcm_cm + u, u / c


# ==========================================================================
#  virtual student  (drives ONLY the public Rig API / visible readouts)
# ==========================================================================
class VirtualStudent:
    def __init__(self, rig, verbose=False):
        self.rig = rig
        self.verbose = verbose
        self.log = []

    def _say(self, s):
        self.log.append(s)
        if self.verbose:
            print("   " + s)

    # ---- setup -----------------------------------------------------------
    def settle(self, seconds=2.5, dt=0.004):
        for _ in range(int(seconds / dt)):
            self.rig.step(dt)

    # ---- part (i): centre of mass ---------------------------------------
    def find_centre_of_mass(self):
        r = self.rig
        r.loop_present = True
        ok, _ = r.mount_on_loop(r.truth.L * 0.45)
        assert ok

        def observe(x, watch=1.8, dt=0.004):
            """Re-tie the loop at x, watch the cylinder, report what the eye sees."""
            r.take_cylinder_off()
            r.mount_on_loop(x)
            verdict = "level"
            for _ in range(int(watch / dt)):
                r.step(dt)
                v = r.bench_readout()["tilt_view"]
                if v in ("bottom_down", "top_down"):
                    verdict = v
                    break
                if v == "fallen":
                    break
            return verdict

        # A careful student does not stop at the first position that looks
        # level: they find both edges of the range that still looks level and
        # take the middle of it.
        lo0, hi0 = 0.005, r.truth.L - 0.005

        def bracket(pred):
            a, b = lo0, hi0
            for _ in range(20):
                mid = 0.5 * (a + b)
                if pred(observe(mid)):
                    a = mid
                else:
                    b = mid
            return 0.5 * (a + b)

        edge_low = bracket(lambda v: v == "bottom_down")   # far end still dips
        edge_high = bracket(lambda v: v != "top_down")     # near end starts to dip
        best = 0.5 * (edge_low + edge_high)

        r.take_cylinder_off()
        r.mount_on_loop(best)
        self.settle(1.2)
        # steady the tube by hand so that it lies horizontal, lay the ruler
        # alongside with its zero against the top end, and read the scale
        r.hold(True)
        self.settle(0.6)
        self.lay_ruler_along(("top",))
        xcm = r.ruler_read(("loop",))
        L = r.ruler_read(("bottom",))
        self._say("x_CM = %.1f cm, L = %.1f cm" % (xcm, L))
        return L, xcm

    def lay_ruler_along(self, zero_feat, offset=0.022):
        """Put the ruler beside the tube with its 0 mark at a chosen point."""
        r = self.rig
        p = r.feature_world(zero_feat)
        _ox, _oy, ux, uy = r.cyl_world()
        r.ruler_angle = math.atan2(uy, ux)
        r.move_ruler(p[0] - uy * offset, p[1] + ux * offset)

    def measure_holes(self):
        """Lay the tube on the bench and read every hole against the ruler."""
        r = self.rig
        r.take_thread_off()
        r.enter_part_b()
        self.lay_ruler_along(("top",))
        holes = [r.ruler_read(("hole", i)) for i in range(len(r.truth.holes))]
        return holes

    # ---- part (ii): periods ---------------------------------------------
    def time_20_cycles(self, hole, n_cycles=20, dt=0.002):
        r = self.rig
        r.mount_on_pin(hole)
        r.pull_aside(6.0)
        r.release()
        # let the swing become regular
        for _ in range(int(1.0 / dt)):
            r.step(dt)

        prev = r.bench_readout()["angle_deg"]
        crossings = 0
        started = False
        guard = 0
        while crossings <= 2 * n_cycles and guard < 400000:
            r.step(dt)
            guard += 1
            cur = r.bench_readout()["angle_deg"]
            if prev > 0.0 >= cur or prev < 0.0 <= cur:
                if not started:
                    r.stopwatch_reset()
                    r.stopwatch_start()
                    started = True
                    crossings = 0
                else:
                    crossings += 1
                    if crossings == 2 * n_cycles:
                        r.stopwatch_stop()
                        break
            prev = cur
        total = r.stopwatch_seconds()
        r.stop_swing()
        return total / n_cycles

    def run_periods(self, xcm_cm, hole_cm_list, trials=4):
        r = self.rig
        data = []
        for i, hole_cm in enumerate(hole_cm_list):
            n = 20
            Ts = [self.time_20_cycles(i, n) for _ in range(trials)]
            data.append([hole_cm, xcm_cm - hole_cm, Ts, n])

        # the region around the minimum is flat, so those timings are
        # repeated several more times before the curve is read
        R0 = min(data, key=lambda q: sum(q[2]) / len(q[2]))[1]
        for row in data:
            if abs(row[1] - R0) <= 3.5:
                row[2] += [self.time_20_cycles(data.index(row), row[3])
                           for _ in range(4)]

        rows = []
        for i, (hole_cm, R, Ts, _n) in enumerate(data):
            Tm = sum(Ts) / len(Ts)
            rows.append((hole_cm, R, Tm))
            self._say("hole %2d  x=%5.1f cm  R=%5.1f cm  T=%.4f s  (%d runs)"
                      % (i + 1, hole_cm, R, Tm, len(Ts)))
        return rows

    # ---- full run --------------------------------------------------------
    def run(self):
        L, xcm = self.find_centre_of_mass()
        holes = self.measure_holes()
        rows = self.run_periods(xcm, holes)

        xs = [R * R for (_h, R, _T) in rows]
        ys = [T_ * T_ * R for (_h, R, T_) in rows]
        alpha, beta, da, db = linfit(xs, ys)
        g, rr, z, ratio = solve_blackbox(L, xcm, alpha, beta)

        # method (b): read the minimum off the smooth T-R curve.  A parabola
        # is fitted by least squares to the points that lie in the flat
        # region around the visually lowest point.
        centre = min(rows, key=lambda q: q[2])[1]
        Rmin = Tmin = None
        for _pass in range(4):
            win = [(q[1], q[2]) for q in rows if abs(q[1] - centre) <= 2.2]
            if len(win) < 4:
                win = [(q[1], q[2]) for q in
                       sorted(rows, key=lambda q: abs(q[1] - centre))[:5]]
            A, B, C = _quadfit([p[0] for p in win], [p[1] for p in win])
            Rmin = -B / (2 * A)
            Tmin = A * Rmin * Rmin + B * Rmin + C
            if abs(Rmin - centre) < 0.05:
                break
            centre = 0.5 * (centre + Rmin)
        g_b, r_b, z_b, ratio_b = solve_minimum(L, xcm, Rmin, Tmin)

        # error propagation exactly as in the official marking scheme,
        # plus the contribution of the +-0.05 cm reading of x_CM, which
        # shifts every lever arm R and therefore the whole fit
        dr = (da / alpha + db / beta) * rr
        _g1, _r1, z_hi, ra_hi = solve_blackbox(L, xcm, alpha,
                                               beta * (rr + dr) / rr)
        _g2, _r2, z_lo, ra_lo = solve_blackbox(L, xcm, alpha,
                                               beta * (rr - dr) / rr)
        dz_r = abs(z_hi - z_lo) / 2.0
        dra_r = abs(ra_hi - ra_lo) / 2.0
        dg_r = da / alpha * g

        zs, ras, gs, rs = [], [], [], []
        for shift in (-0.05, +0.05):
            xs2 = [(R + shift) ** 2 for (_h, R, _T) in rows]
            ys2 = [T_ * T_ * (R + shift) for (_h, R, T_) in rows]
            a2, b2, _da2, _db2 = linfit(xs2, ys2)
            gg, r2, zz, rr2 = solve_blackbox(L, xcm + shift, a2, b2)
            zs.append(zz); ras.append(rr2); gs.append(gg); rs.append(r2)
        dz = math.hypot(dz_r, abs(zs[1] - zs[0]) / 2.0)
        dratio = math.hypot(dra_r, abs(ras[1] - ras[0]) / 2.0)
        dg = math.hypot(dg_r, abs(gs[1] - gs[0]) / 2.0)
        dr = math.hypot(dr, abs(rs[1] - rs[0]) / 2.0)

        return {
            "d_r": dr, "d_z": dz, "d_ratio": dratio, "d_g": dg,
            "L": L, "x_cm": xcm,
            "alpha": alpha, "beta": beta, "d_alpha": da, "d_beta": db,
            "g": g, "r": rr, "z": z, "ratio": ratio,
            "R_min": Rmin, "T_min": Tmin,
            "g_b": g_b, "r_b": r_b, "z_b": z_b, "ratio_b": ratio_b,
            "rows": rows,
        }


# ==========================================================================
#  verification harness
# ==========================================================================
def run_selftest(seeds=None, verbose=True):
    seeds = seeds or ([OFFICIAL_SEED] + [1000 + 137 * i for i in range(11)])
    n_pass = n_fail = 0
    fails = []
    for sd in seeds:
        truth = Truth(sd)
        rig = Rig(truth, random.Random(sd * 7919 + 13))
        st = VirtualStudent(rig)
        res = st.run()

        checks = [
            ("i.  x_CM", res["x_cm"], truth.x_cm * 100.0, 0.20, "cm"),
            ("i.  L", res["L"], truth.L * 100.0, 0.15, "cm"),
            # the marking scheme asks for a value *with its error estimate*,
            # so the answer must agree with the truth inside its own quoted
            # uncertainty (2.5 sigma, floor 0.5 cm)
            ("ii. z (a)", res["z"], truth.z * 100.0,
             max(0.50, 3.5 * res["d_z"]), "cm"),
            ("iii.M/m (a)", res["ratio"], truth.M / truth.m,
             max(0.20, 3.5 * res["d_ratio"]), ""),
            ("iv. g (a)", res["g"], truth.g * 100.0,
             max(15.0, 3.5 * res["d_g"]), "cm/s^2"),
            ("ii. z (b)", res["z_b"], truth.z * 100.0,
             max(2.50, 0.15 * truth.z * 100.0), "cm"),
            ("iii.M/m (b)", res["ratio_b"], truth.M / truth.m,
             max(0.80, 0.40 * truth.M / truth.m), ""),
            ("iv. g (b)", res["g_b"], truth.g * 100.0, 90.0, "cm/s^2"),
            ("--  r", res["r"], truth.r * 1e4,
             max(3.0, 3.5 * res["d_r"]), "cm^2"),
        ]
        if verbose:
            print("\nseed %-10s  (truth: L=%.1f cm  x_CM=%.2f cm  z=%.2f cm  "
                  "M/m=%.3f  g=%.1f cm/s^2)"
                  % (sd, truth.L * 100, truth.x_cm * 100, truth.z * 100,
                     truth.M / truth.m, truth.g * 100))
            print("   quoted: z = %.1f +- %.1f cm,  M/m = %.2f +- %.2f,  "
                  "g = %.0f +- %.0f cm/s^2,  r = %.1f +- %.1f cm^2"
                  % (res["z"], res["d_z"], res["ratio"], res["d_ratio"],
                     res["g"], res["d_g"], res["r"], res["d_r"]))
        for name, got, exp, tol, unit in checks:
            ok = abs(got - exp) <= tol
            n_pass += ok
            n_fail += (not ok)
            if not ok:
                fails.append((sd, name, got, exp, tol))
            if verbose:
                print("   [%s] %-12s got %10.3f   true %10.3f   (tol %.2f) %s"
                      % ("PASS" if ok else "FAIL", name, got, exp, tol, unit))
    print("\n==== %d passed, %d failed ====" % (n_pass, n_fail))
    for f in fails:
        print("   FAIL seed %s %s got %.3f exp %.3f tol %.3f" % f)
    return n_fail == 0



# ==========================================================================
#  artwork - everything is reconstructed from the apparatus photograph
#            on page 2 of the official problem sheet
# ==========================================================================
import tkinter as tk
from tkinter import ttk
import time as _time

COL_TABLE = "#93ab8b"          # the green background of the official photo
COL_TABLE_DK = "#7e9678"
COL_AL = ["#63696d", "#8f9599", "#bcc2c6", "#e3e7e9", "#aeb4b8", "#767c80"]
COL_AL_EDGE = "#4d5255"
COL_HOLE = "#22262a"
COL_PLATE = "#d7e4e8"
COL_PIN = "#3a3f43"
COL_THREAD = "#f4f2ec"
COL_RULER = "#c9302c"
COL_MARK = "#43403c"


_FONTS = {}
_FIT = {}


def _font(size, family="TkDefaultFont", weight="normal"):
    key = (family, size, weight)
    f = _FONTS.get(key)
    if f is None:
        f = _FONTS[key] = tkfont.Font(family=family, size=size, weight=weight)
    return f


def fit_font(text, max_w, max_h, family="TkDefaultFont", weight="normal",
             floor=4):
    """
    Largest point size whose rendering of `text` really fits in the box.
    The width is measured with the toolkit's own metrics, so the result is
    correct on any platform instead of relying on a guessed glyph width.
    """
    key = (family, weight, len(text), int(max_w), int(max_h))
    hit = _FIT.get(key)
    if hit is not None:
        return hit
    size = max(floor, min(int(max_h), 64))
    while size > floor:
        f = _font(size, family, weight)
        if f.measure(text) <= max_w and f.metrics("linespace") <= max_h:
            break
        size -= 1
    _FIT[key] = size
    return size


def _pt(ox, oy, ux, uy, s, t):
    """screen point at axial offset s and transverse offset t (pixels)."""
    return (ox + ux * s - uy * t, oy + uy * s + ux * t)


def draw_cylinder(cv, ox, oy, ux, uy, ppm, truth, tag,
                  marks=(), show_holes=True):
    """
    Draw the hollow aluminium cylinder.  (ox, oy) is the screen position of
    the centre of the TOP end face, (ux, uy) the unit vector along the axis
    pointing from the top end towards the bottom end.
    The ball inside is NEVER drawn - it is a blackbox.
    """
    Lp = truth.L * ppm
    rp = truth.d_out * 0.5 * ppm
    n = len(COL_AL)
    for i in range(n):
        t0 = -rp + 2.0 * rp * i / n
        t1 = -rp + 2.0 * rp * (i + 1) / n
        pts = [_pt(ox, oy, ux, uy, 0.0, t0), _pt(ox, oy, ux, uy, Lp, t0),
               _pt(ox, oy, ux, uy, Lp, t1), _pt(ox, oy, ux, uy, 0.0, t1)]
        cv.create_polygon([c for p in pts for c in p],
                          fill=COL_AL[i], outline="", tags=tag)
    # outline
    pts = [_pt(ox, oy, ux, uy, 0.0, -rp), _pt(ox, oy, ux, uy, Lp, -rp),
           _pt(ox, oy, ux, uy, Lp, rp), _pt(ox, oy, ux, uy, 0.0, rp)]
    cv.create_polygon([c for p in pts for c in p], fill="",
                      outline=COL_AL_EDGE, width=max(1, int(ppm * 0.0006)),
                      tags=tag)
    # end faces (the tube is open, with a dark bore visible)
    for s in (0.0, Lp):
        bore = rp * 0.72
        ring = [_pt(ox, oy, ux, uy, s, -bore), _pt(ox, oy, ux, uy, s, bore)]
        cv.create_line(ring[0][0], ring[0][1], ring[1][0], ring[1][1],
                       fill="#4a4f52", width=max(2, int(ppm * 0.0022)),
                       tags=tag)
    if show_holes:
        hr = 0.0019 * ppm
        for h in truth.holes:
            s = h * ppm
            poly = []
            for k in range(8):
                a = 2.0 * math.pi * k / 8.0
                poly.append(_pt(ox, oy, ux, uy,
                                s + hr * math.cos(a), hr * 0.85 * math.sin(a)))
            cv.create_polygon([c for p in poly for c in p],
                              fill=COL_HOLE, outline="#585d60", tags=tag)
    for mk in marks:
        s = mk * ppm
        p0 = _pt(ox, oy, ux, uy, s, -rp)
        p1 = _pt(ox, oy, ux, uy, s, rp)
        cv.create_line(p0[0], p0[1], p1[0], p1[1], fill=COL_MARK,
                       width=max(1, int(ppm * 0.0009)), tags=tag)


def draw_base_plate(cv, x, y, ppm, tag):
    """
    Perspex base plate clamped to the table edge.  The thin pin passes
    through the middle of the block, so (x, y) - the pivot - is at the
    centre of the fixture.
    """
    w = 0.150 * ppm
    h = 0.062 * ppm
    d = 0.022 * ppm
    top, bot = y - h / 2, y + h / 2
    cv.create_polygon(x - w / 2, top, x + w / 2, top,
                      x + w / 2 + d, top - d, x - w / 2 + d, top - d,
                      fill="#c3d3d8", outline="#8fa2a8", tags=tag)
    cv.create_rectangle(x - w / 2, top, x + w / 2, bot,
                        fill=COL_PLATE, outline="#8fa2a8", tags=tag)
    cv.create_line(x - w / 2, bot, x + w / 2, bot, fill="#93a6ac", tags=tag)
    draw_pin_head(cv, x, y, ppm, tag)


def draw_pin_head(cv, x, y, ppm, tag):
    """The thin pin seen end-on, sticking out of the plate towards us."""
    pr = max(3.0, 0.0042 * ppm)
    cv.create_oval(x - pr * 1.5, y - pr * 1.5, x + pr * 1.5, y + pr * 1.5,
                   fill="#9aa0a4", outline="#6b7175", tags=tag)
    cv.create_oval(x - pr, y - pr, x + pr, y + pr,
                   fill=COL_PIN, outline="#22262a", tags=tag)


def draw_thread(cv, px, py, cx, cy, rp, ux, uy, ppm, tag):
    """Thread loop: two strands from the pin down to a loop round the tube."""
    w = max(1, int(ppm * 0.0008))
    span = max(2.0, 0.0035 * ppm)
    lx, ly = ux * span, uy * span
    cv.create_line(px, py, cx - lx, cy - ly, fill=COL_THREAD, width=w, tags=tag)
    cv.create_line(px, py, cx + lx, cy + ly, fill=COL_THREAD, width=w, tags=tag)
    poly = []
    for k in range(24):
        a = 2.0 * math.pi * k / 24.0
        poly.append(_pt(cx, cy, ux, uy, span * math.cos(a), rp * math.sin(a)))
    cv.create_polygon([c for p in poly for c in p], fill="", outline=COL_THREAD,
                      width=w, tags=tag)


def draw_ruler(cv, x, y, ppm, tag, length=RULER_LEN, angle=0.0):
    """
    The 35 cm plastic ruler of the photograph.  (x, y) is the 0 graduation
    and the scale runs along `angle`.

    As on a real ruler the scale is inset from the ends of the body, every
    graduation starts just inside the moulded rim instead of under it, the
    three tick lengths stay clearly different, and the numerals are printed
    in the clear band underneath, centred on their own centimetre mark.
    """
    ux, uy = math.cos(angle), math.sin(angle)
    Lp = length * ppm
    hp = RULER_H * ppm
    bw = max(1.0, hp * 0.05)                 # moulded rim
    inset = max(bw * 2.0, hp * 0.22)         # scale does not reach the ends

    pts = [_pt(x, y, ux, uy, -inset, -hp / 2), _pt(x, y, ux, uy, Lp + inset, -hp / 2),
           _pt(x, y, ux, uy, Lp + inset, hp / 2), _pt(x, y, ux, uy, -inset, hp / 2)]
    cv.create_polygon([c for p in pts for c in p], fill="#f5efe2",
                      outline=COL_RULER, width=bw, tags=tag)

    t0 = -hp / 2 + bw                        # graduations start inside the rim
    mm_px = 0.001 * ppm
    if mm_px >= 3.0:
        step = 1
    elif mm_px >= 1.2:
        step = 5
    else:
        step = 10
    for i in range(0, int(length * 1000) + 1, step):
        if i % 10 == 0:
            ln, col, wd = hp * 0.46, "#33383a", max(1.0, hp * 0.030)
        elif i % 5 == 0:
            ln, col, wd = hp * 0.30, "#3b4143", max(1.0, hp * 0.024)
        else:
            ln, col, wd = hp * 0.16, "#6a7073", 1.0
        a = _pt(x, y, ux, uy, i * mm_px, t0)
        b = _pt(x, y, ux, uy, i * mm_px, t0 + ln)
        cv.create_line(a[0], a[1], b[0], b[1], fill=col, width=wd, tags=tag)

    # numerals in the clear band below the graduations
    cm_px = 0.01 * ppm
    n_cm = int(length * 100)
    band_top = t0 + hp * 0.46
    band_bot = hp / 2 - bw
    band_c = 0.5 * (band_top + band_bot)
    band_h = min(hp * 0.36, band_bot - band_top)
    label = str(n_cm)
    for every in (1, 2, 5, 10):
        fs = fit_font(label, cm_px * every * 0.80, band_h)
        if fs >= 6:
            break
    if fs < 6:
        return
    for i in range(0, n_cm + 1, every):
        c = _pt(x, y, ux, uy, i * cm_px, band_c)
        cv.create_text(c[0], c[1], text=str(i), angle=-math.degrees(angle),
                       anchor="center", font=_font(fs), fill="#33383a",
                       tags=tag)


def draw_stopwatch(cv, x, y, r, tag, text="00:00.00"):
    """
    The hand-held stopwatch of the problem-sheet photograph: a teal oval body
    with a crown button on top, two side buttons, a lanyard eye and a pale
    rectangular LCD window carrying the reading.  `r` is the body radius in
    pixels.
    """
    # lanyard eye and crown button
    cv.create_rectangle(x - r * 0.14, y - r * 1.34, x + r * 0.14, y - r * 0.92,
                        fill="#8d9498", outline="#5f666a", tags=tag)
    cv.create_oval(x - r * 0.24, y - r * 1.56, x + r * 0.24, y - r * 1.18,
                   fill="", outline="#5f666a", width=max(2, int(r * 0.07)),
                   tags=tag)
    # side buttons
    for sx in (-1, 1):
        cv.create_rectangle(x + sx * r * 0.92, y - r * 0.66,
                            x + sx * r * 1.14, y - r * 0.40,
                            fill="#8d9498", outline="#5f666a", tags=tag)
    # body
    cv.create_oval(x - r, y - r, x + r, y + r, fill="#1d7a8b",
                   outline="#14606e", width=max(1, int(r * 0.05)), tags=tag)
    cv.create_oval(x - r * 0.90, y - r * 0.90, x + r * 0.90, y + r * 0.90,
                   fill="#2fa5b8", outline="#1d7a8b", tags=tag)
    cv.create_arc(x - r * 0.86, y - r * 0.86, x + r * 0.86, y + r * 0.86,
                  start=35, extent=110, style="arc", outline="#63c4d2",
                  width=max(1, int(r * 0.06)), tags=tag)
    # LCD window
    lw, lh = r * 0.88, r * 0.32
    cv.create_rectangle(x - lw, y - lh - r * 0.02, x + lw, y + lh - r * 0.02,
                        fill="#cdd8c6", outline="#5d675a",
                        width=max(1, int(r * 0.035)), tags=tag)
    fs = fit_font(text, 2.0 * lw * 0.86, 2.0 * lh * 0.82,
                  family="Courier", weight="bold", floor=5)
    cv.create_text(x, y - r * 0.02, text=text, fill="#1b2220",
                   font=_font(fs, "Courier", "bold"), tags=tag)
    fa = fit_font("ALBA", r * 0.80, r * 0.24)
    cv.create_text(x, y - r * 0.52, text="ALBA", fill="#e8f3f5",
                   font=_font(fa), tags=tag)
    fb = fit_font("1/100 sec", r * 1.00, r * 0.20)
    cv.create_text(x, y + r * 0.56, text="1/100 sec", fill="#cfeaef",
                   font=_font(fb), tags=tag)


def draw_finger(cv, tx, ty, ppm, tag):
    """
    A fingertip seen from the side, propping the tube up from underneath.
    (tx, ty) is the contact point on the lower surface of the cylinder.
    """
    ux, uy = 0.62, 0.79                       # finger axis, down and to the right
    ln = 0.062 * ppm
    wd = max(4.0, 0.015 * ppm)
    ex, ey = tx + ux * ln, ty + uy * ln
    cv.create_line(tx, ty, ex, ey, fill="#e3bd9c", width=wd,
                   capstyle="round", tags=tag)
    cv.create_line(tx + ux * ln * 0.10, ty + uy * ln * 0.10, ex, ey,
                   fill="#f0d0b2", width=wd * 0.52, capstyle="round", tags=tag)
    # knuckle crease
    kx, ky = tx + ux * ln * 0.55, ty + uy * ln * 0.55
    cv.create_line(kx - uy * wd * 0.42, ky + ux * wd * 0.42,
                   kx + uy * wd * 0.42, ky - ux * wd * 0.42,
                   fill="#c99f7e", width=max(1, int(wd * 0.10)), tags=tag)
    # nail
    nx, ny = tx + ux * ln * 0.17, ty + uy * ln * 0.17
    poly = []
    for k in range(12):
        a = 2.0 * math.pi * k / 12.0
        ca, sa = wd * 0.34 * math.cos(a), wd * 0.22 * math.sin(a)
        poly += [nx + ux * ca - uy * sa, ny + uy * ca + ux * sa]
    cv.create_polygon(poly, fill="#f7e6d6", outline="#d3b295", tags=tag)


def draw_eraser(cv, cx, cy, ppm, tag):
    """A rubber block with its paper sleeve, seen from above."""
    w, h = ERASER_W * ppm * 0.5, ERASER_H * ppm * 0.5
    cv.create_rectangle(cx - w, cy - h, cx + w, cy + h,
                        fill="#f2dfe0", outline="#b99aa0", tags=tag)
    cv.create_rectangle(cx - w * 0.34, cy - h, cx + w * 0.34, cy + h,
                        fill="#4d6fb0", outline="#33518a", tags=tag)
    cv.create_line(cx - w, cy - h * 0.45, cx + w, cy - h * 0.45,
                   fill="#ffffff", tags=tag)


def draw_pencil(cv, tx, ty, ppm, tag):
    """A pencil whose point is at (tx, ty), body running down to the right."""
    ux, uy = 0.80, 0.60
    ln = 0.110 * ppm
    hw = max(2.0, 0.0055 * ppm)

    def pt(s, t):
        return (tx + ux * s - uy * t, ty + uy * s + ux * t)

    wood_a, wood_b = 0.0, 0.020 * ppm
    cv.create_polygon(*pt(wood_a, 0), *pt(wood_b, -hw), *pt(wood_b, hw),
                      fill="#e4d2ae", outline="#a67f22", tags=tag)
    cv.create_polygon(*pt(wood_a, 0), *pt(0.008 * ppm, -hw * 0.42),
                      *pt(0.008 * ppm, hw * 0.42),
                      fill="#3c3a37", outline="", tags=tag)
    cv.create_polygon(*pt(wood_b, -hw), *pt(ln * 0.90, -hw),
                      *pt(ln * 0.90, hw), *pt(wood_b, hw),
                      fill="#e2b13c", outline="#a67f22", tags=tag)
    cv.create_polygon(*pt(ln * 0.90, -hw), *pt(ln, -hw),
                      *pt(ln, hw), *pt(ln * 0.90, hw),
                      fill="#c0392b", outline="#8e2c21", tags=tag)


# ==========================================================================
#  laboratory view - Part A (centre of mass & length) / Part B (periods)
# ==========================================================================
import tkinter as tk
from tkinter import ttk
import time as _time


class LabView(ttk.Frame):
    """
    One physical bench, seen twice.  `part` is "A" or "B"; it decides how the
    mouse behaves and which hardware is in use, but the apparatus and the
    hand tools are the same objects in both views.

    Rendering is split into three canvas layers so that a 60 fps animation
    does not have to recreate the 350 graduations of the ruler every frame:

        "st"  background, bench, base plate   - rebuilt on zoom / pan
        "ru"  the ruler                       - rebuilt on zoom / pan / move
        "dy"  tube, thread, finger, pencil    - rebuilt every frame
    """

    def __init__(self, master, app, part):
        super().__init__(master)
        self.app = app
        self.rig = app.rig
        self.part = part
        self.ppm_true = app.ppm_true
        self.ppm = app.ppm_true
        self.pan = [0.0, 0.0]
        self.drag_mode = None
        self.pending_hole = None
        self.press_xy = (0, 0)
        self.grab = (0.0, 0.0)
        self.last = (0, 0)
        self.anchor = 0.28 if part == "A" else 0.36
        self._fitted = False
        self._static_key = None
        self._ruler_key = None
        self._sw_cache = None
        self._scale_cache = None
        self.hover_xy = (0, 0)
        self.tip_text = '원통 위 휠: 실 이동 · 자 위 휠: 회전 · 원통 클릭: 손 떼기 · 그 외 휠: 확대' \
            if part == "A" else \
            '자 위 휠: 회전 · 그 외 휠: 확대 · 우클릭: 핀에서 빼기 · 스페이스: 초시계'

        self.cv = tk.Canvas(self, bg=COL_TABLE, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        self.panel = ttk.Frame(self, width=268)
        self.panel.pack(side="right", fill="y")
        self.panel.pack_propagate(False)
        self.build_panel()

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<ButtonPress-3>", self.on_right)
        self.cv.bind("<B1-Motion>", self.on_motion)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Motion>", self.on_hover)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 120))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -120))
        self.cv.bind("<Shift-MouseWheel>", lambda e: self.on_wheel(e, fine=True))
        self.cv.bind("<Control-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        self.cv.bind("<Configure>", self.on_configure)

    # ------------------------------------------------------------------
    #  side panel
    # ------------------------------------------------------------------
    def build_panel(self):
        p = self.panel
        head = 'Part A · 무게중심과 길이' \
            if self.part == "A" else 'Part B · 주기 측정'
        ttk.Label(p, text=head, font=("TkDefaultFont", 11, "bold")).pack(
            pady=(9, 3))

        hint = '• 마우스 휠: 실 위치 2 mm 이동\n  (Shift+휠 = 0.2 mm 미세 조정)\n• 왼쪽 클릭: 받치던 손을 뗍니다\n• 미끄러지는 도중 클릭하면 손가락으로\n  붙잡을 수 있습니다\n• 빠진 원통은 클릭해 집어서 고리에\n  가져다 대고 다시 클릭하면 끼워집니다\n• 자·연필·지우개는 끌어서 옮깁니다\n  (연필로 관을 문지르면 자국이 남고\n   지우개로 문지르면 지워집니다)\n• 자 위에서 휠을 돌리면 커서를 중심으로\n  자가 회전합니다\n• 그 밖의 곳에서 휠: 확대 / 축소\n• Ctrl+휠: 언제나 확대 / 축소' if self.part == "A" else \
            '• 원통의 진자 구멍을 클릭해 고르고\n  이어서 받침판의 핀 구멍을 클릭하면\n  그 구멍이 핀에 걸립니다\n• 우클릭: 원통을 핀에서 뺍니다\n• 걸린 원통을 끌면 젖혔다 놓을 수 있고\n  진폭 제한은 없습니다 (360°)\n• 내려놓은 원통은 끌어서 옮깁니다\n• 자·연필·지우개도 끌어서 옮깁니다\n  (자 위에서 휠을 돌리면 자가 회전)\n  Part A에서 남긴 연필 자국은 그대로\n  남아 있습니다\n• 휠: 확대 / 축소\n• 스페이스바: 초시계 시작 / 정지'
        ttk.Label(p, text=hint, justify="left",
                  font=("TkDefaultFont", 8)).pack(padx=8, anchor="w")

        ttk.Separator(p).pack(fill="x", pady=6)
        self.scale_lbl = ttk.Label(p, text="", font=("TkDefaultFont", 8))
        self.scale_lbl.pack()


        self.act = ttk.Frame(p)
        self.act.pack(fill="x")
        self.build_actions()

        if self.part == "B":
            ttk.Separator(p).pack(fill="x", pady=6)
            ttk.Label(p, text='초시계',
                      font=("TkDefaultFont", 10, "bold")).pack()
            self.sw_cv = tk.Canvas(p, width=254, height=182,
                                   bg="#eef1ec", highlightthickness=0)
            self.sw_cv.pack(pady=(2, 0))
            self.sw_cv.bind("<Button-1>", self.sw_click)
            row2 = ttk.Frame(p)
            row2.pack(pady=4)
            ttk.Button(row2, text='시작', width=7, takefocus=0,
                       command=self.sw_start).pack(side="left", padx=2)
            ttk.Button(row2, text='정지', width=7, takefocus=0,
                       command=self.sw_stop).pack(side="left", padx=2)
            ttk.Button(row2, text='리셋', width=7, takefocus=0,
                       command=self.rig.stopwatch_reset).pack(side="left",
                                                              padx=2)
        else:
            self.sw_cv = None

    def build_actions(self):
        for c in self.act.winfo_children():
            c.destroy()
        r = self.rig
        if self.part == "A":
            self.hold_btn = ttk.Button(self.act, text="", takefocus=0,
                                       command=self.do_hold)
            self.hold_btn.pack(pady=2)
            ttk.Button(self.act, text='원통 다시 걸기',
                       takefocus=0, command=self.do_rehang).pack(pady=2)
            self._sync_hold()
        else:
            self.sel_lbl = ttk.Label(self.act, text="",
                                     font=("TkDefaultFont", 9))
            self.sel_lbl.pack(pady=2)

    # ------------------------------------------------------------------
    def sw_start(self):
        self.rig.stopwatch_start()

    def sw_stop(self):
        self.rig.stopwatch_stop()

    def sw_toggle(self):
        """One press starts the watch, the next one stops it."""
        if self.rig.sw_running:
            self.sw_stop()
        else:
            self.sw_start()
        self.draw_panel_stopwatch()

    def sw_click(self, _e):
        self.sw_toggle()

    def _sync_hold(self):
        b = getattr(self, "hold_btn", None)
        if b is None or not b.winfo_exists():
            return
        b.config(text='손 떼기' if self.rig.held
                 else '손으로 받치기')

    def do_hold(self):
        _ok, m = self.rig.hold(not self.rig.held)
        self._sync_hold()
        self.app.status(m)

    def do_rehang(self):
        r = self.rig
        x = r.thread_x or r.truth.L * 0.5
        r.take_cylinder_off()
        r.loop_present = True
        r.mount_on_loop(x)
        r.hold(True)
        self._sync_hold()

    # ------------------------------------------------------------------
    #  scale and transform
    # ------------------------------------------------------------------
    def view_box(self):
        tr = self.rig.truth
        top = 0.075 if self.part == "A" else max(tr.holes[-1] + 0.012, 0.075)
        need_h = top + tr.bench_y + 0.085
        need_w = tr.L * (1.20 if self.part == "A" else 1.05)
        return need_w, need_h, top / need_h

    def scale_1to1(self):
        self.ppm = self.ppm_true
        self.anchor = self.view_box()[2]
        self.pan = [0.0, 0.0]
        self._static_key = None

    def scale_fit(self):
        w = max(self.cv.winfo_width(), 640)
        h = max(self.cv.winfo_height(), 520)
        self._fitted = True
        need_w, need_h, anchor = self.view_box()
        self.anchor = anchor
        self._static_key = None
        self.ppm = max(180.0, min(14000.0,
                                  min(w / need_w, h / need_h) * 0.94))
        self.pan = [0.0, 0.0]

    def w2s(self, x, y):
        cx = self.cv.winfo_width() * 0.5 + self.pan[0]
        cy = self.cv.winfo_height() * self.anchor + self.pan[1]
        return cx + x * self.ppm, cy + y * self.ppm

    def s2w(self, sx, sy):
        cx = self.cv.winfo_width() * 0.5 + self.pan[0]
        cy = self.cv.winfo_height() * self.anchor + self.pan[1]
        return (sx - cx) / self.ppm, (sy - cy) / self.ppm

    def on_configure(self, _e=None):
        if not self._fitted and self.cv.winfo_width() > 240:
            self.scale_fit()
        self._static_key = None
        self.redraw()

    # ------------------------------------------------------------------
    #  mouse
    # ------------------------------------------------------------------
    def hole_at(self, wx, wy):
        r = self.rig
        ox, oy, ux, uy = r.cyl_world()
        best, bd = None, 1e9
        for i, h in enumerate(r.truth.holes):
            d = math.hypot(ox + ux * h - wx, oy + uy * h - wy)
            if d < bd:
                best, bd = i, d
        return best if bd < max(0.0035, 8.0 / self.ppm) else None

    def on_press(self, e):
        """
        Hit testing follows what is drawn on top of what: the pencil and the
        rubber lie on everything, then the apparatus, and the ruler last -
        exactly the stacking order the canvas layers use.
        """
        self.last = (e.x, e.y)
        r = self.rig
        wx, wy = self.s2w(e.x, e.y)

        if r.on_eraser(wx, wy):
            self.drag_mode = "eraser"
            self.grab = (wx - r.eraser_pos[0], wy - r.eraser_pos[1])
            r.eraser_to(wx - self.grab[0], wy - self.grab[1], True)
            return
        if r.on_pencil(wx, wy):
            self.drag_mode = "pencil"
            self.grab = (wx - r.pencil_pos[0], wy - r.pencil_pos[1])
            r.pencil_to(wx - self.grab[0], wy - self.grab[1], True)
            return

        if self.part == "A":
            if r.carried:
                if math.hypot(wx, wy - LOOP_DROP) < 0.030:
                    _ok, m = r.insert_into_loop()
                    self._sync_hold()
                    self.app.status(m)
                else:
                    self.app.status('실 고리 위치에서 클릭하세요.')
                return
            if r.slipping or (r.fallen and r.on_cylinder(wx, wy, 0.010)):
                _ok, m = r.catch()
                self.hover_xy = (e.x, e.y)
                r.carry_pos = [wx, wy]
                self._sync_hold()
                self.app.status(m)
                return
            if r.held and r.on_cylinder(wx, wy, r.truth.d_out):
                _ok, m = r.hold(False)
                self._sync_hold()
                self.app.status(m)
                return
        else:
            if math.hypot(wx, wy) < max(0.008, 10.0 / self.ppm):
                _ok, m = r.connect_selected_to_pin()
                self.app.status(m)
                self.build_actions()
                return
            i = self.hole_at(wx, wy)
            if i is not None:
                # a click selects the hole, but a drag from the same point
                # moves or swings the tube instead
                self.drag_mode = "hole"
                self.pending_hole = i
                self.press_xy = (e.x, e.y)
                self.grab = (wx - r.free_pos[0], wy - r.free_pos[1])
                return
            if r.on_cylinder(wx, wy, r.truth.d_out * 0.4):
                if r.mode == "pendulum":
                    self.drag_mode = "swing"
                    r.released = False
                    return
                if r.mode == "free":
                    self.drag_mode = "move"
                    self.grab = (wx - r.free_pos[0], wy - r.free_pos[1])
                    return

        if r.on_ruler(wx, wy):
            self.drag_mode = "ruler"
            self.grab = (wx - r.ruler_pos[0], wy - r.ruler_pos[1])
            return
        self.drag_mode = "pan"

    def on_motion(self, e):
        r = self.rig
        wx, wy = self.s2w(e.x, e.y)
        if self.drag_mode == "hole":
            if math.hypot(e.x - self.press_xy[0],
                          e.y - self.press_xy[1]) < 5:
                return
            self.drag_mode = "swing" if r.mode == "pendulum" else "move"
            if self.drag_mode == "swing":
                r.released = False
        if self.drag_mode == "pan":
            self.pan[0] += e.x - self.last[0]
            self.pan[1] += e.y - self.last[1]
            self._static_key = None
        elif self.drag_mode == "ruler":
            r.move_ruler(wx - self.grab[0], wy - self.grab[1])
            self._ruler_key = None
        elif self.drag_mode == "pencil":
            r.pencil_to(wx - self.grab[0], wy - self.grab[1], True)
        elif self.drag_mode == "eraser":
            r.eraser_to(wx - self.grab[0], wy - self.grab[1], True)
        elif self.drag_mode == "move":
            r.free_pos = [wx - self.grab[0], wy - self.grab[1]]
        elif self.drag_mode == "swing":
            r.pull_aside(math.degrees(math.atan2(wx, wy)))
        self.last = (e.x, e.y)

    def on_release(self, _e):
        if self.drag_mode == "swing":
            self.rig.release()
        elif self.drag_mode == "hole":
            _ok, m = self.rig.select_hole(self.pending_hole)
            self.app.status(m)
            self.build_actions()
        self.drag_mode = None

    def on_hover(self, e):
        self.hover_xy = (e.x, e.y)
        if self.rig.carried:
            self.rig.carry_pos = list(self.s2w(e.x, e.y))

    def on_right(self, _e):
        if self.part == "B":
            _ok, m = self.rig.unmount_from_pin()
            self.app.status(m)
            self.build_actions()

    def zoom_by(self, d):
        self.ppm = max(180.0, min(14000.0,
                                  self.ppm * (1.12 if d > 0 else 1 / 1.12)))
        self._static_key = None

    def on_wheel(self, e, delta=None, fine=False, zoom=False):
        d = delta if delta is not None else e.delta
        r = self.rig
        wx, wy = self.s2w(getattr(e, "x", 0), getattr(e, "y", 0))
        if zoom:
            self.zoom_by(d)
            return
        # the loop only moves while the pointer is on the cylinder, so that
        # turning the ruler can never slide it by accident, and the tube
        # takes precedence because it is drawn on top of the ruler
        if (self.part == "A" and r.mode == "balance"
                and not (r.fallen or r.carried)
                and r.on_cylinder(wx, wy, r.truth.d_out)):
            step = 0.0002 if fine else 0.0020
            r.hold(True)
            r.nudge_loop(-step if d > 0 else step)
            self._sync_hold()
            return
        if r.on_ruler(wx, wy):
            # the wheel turns the ruler about the point under the cursor
            step = math.radians(0.5 if fine else 2.5)
            r.rotate_ruler(step if d > 0 else -step, wx, wy)
            self._ruler_key = None
            return
        self.zoom_by(d)

    # ------------------------------------------------------------------
    #  drawing
    # ------------------------------------------------------------------
    def redraw(self):
        cv = self.cv
        r = self.rig
        tr = r.truth
        w = max(cv.winfo_width(), 60)
        h = max(cv.winfo_height(), 60)
        key = (int(self.ppm), int(self.pan[0]), int(self.pan[1]), w, h)

        if key != self._static_key:
            self._static_key = key
            self._ruler_key = None
            cv.delete("st")
            by = self.w2s(0.0, tr.bench_y)[1]
            px, py = self.w2s(0.0, 0.0)
            cv.create_rectangle(0, 0, w, h, fill=COL_TABLE, outline="",
                                tags="st")
            cv.create_rectangle(0, by, w, h, fill=COL_TABLE_DK, outline="",
                                tags="st")
            cv.create_line(0, py, w, py, fill="#7d9577", dash=(6, 6),
                           tags="st")
            draw_base_plate(cv, px, py, self.ppm, "st")
            cv.tag_lower("st")

        rkey = (key, round(r.ruler_pos[0], 4), round(r.ruler_pos[1], 4),
                round(r.ruler_angle, 4))
        if rkey != self._ruler_key:
            self._ruler_key = rkey
            cv.delete("ru")
            draw_ruler(cv, *self.w2s(*r.ruler_pos), ppm=self.ppm, tag="ru",
                       angle=r.ruler_angle)
            cv.tag_raise("ru", "st")

        cv.delete("dy")
        px, py = self.w2s(0.0, 0.0)
        if r.mode is not None:
            oxw, oyw, ux, uy = r.cyl_world()
            ox, oy = self.w2s(oxw, oyw)
            if r.mode == "balance":
                cxw, cyw = (0.0, LOOP_DROP) if (r.fallen or r.carried) else \
                    (0.0, LOOP_DROP)
                cx, cy = self.w2s(cxw, cyw)
                if r.fallen or r.carried:
                    draw_thread(cv, px, py, cx, cy,
                                tr.d_out * 0.5 * self.ppm * 1.25, 1.0, 0.0,
                                self.ppm, "dy")
                else:
                    lx, ly = self.w2s(oxw + ux * r.thread_x,
                                      oyw + uy * r.thread_x)
                    draw_thread(cv, px, py, lx, ly,
                                tr.d_out * 0.5 * self.ppm * 1.25, ux, uy,
                                self.ppm, "dy")
            draw_cylinder(cv, ox, oy, ux, uy, self.ppm, tr, "dy",
                          marks=r.marks)
            if r.mode == "balance" and r.held and not (r.fallen or r.carried):
                tp = _pt(ox, oy, ux, uy, r.thread_x * self.ppm,
                         tr.d_out * 0.5 * self.ppm)
                draw_finger(cv, tp[0], tp[1], self.ppm, "dy")
            if r.sel_hole is not None and r.mode in ("free", "pendulum"):
                p = _pt(ox, oy, ux, uy, tr.holes[r.sel_hole] * self.ppm, 0.0)
                q = max(6.0, 0.005 * self.ppm)
                cv.create_oval(p[0] - q, p[1] - q, p[0] + q, p[1] + q,
                               outline="#ffd54f", width=2, tags="dy")
            draw_pin_head(cv, px, py, self.ppm, "dy")
            if r.mode == "pendulum":
                cv.create_line(px, py, px, py + tr.L * 1.05 * self.ppm,
                               fill="#7d9577", dash=(3, 5), tags="dy")

        draw_pencil(cv, *self.w2s(*r.pencil_pos), ppm=self.ppm, tag="dy")
        draw_eraser(cv, *self.w2s(*r.eraser_pos), ppm=self.ppm, tag="dy")

        cv.create_text(10, h - 10, anchor="sw", text=r.status_line(),
                       fill="#2f3a2c", font=("TkDefaultFont", 10), tags="dy")
        cv.create_text(w - 10, h - 10, anchor="se", text=self.tip_text,
                       fill="#4d5c49", font=("TkDefaultFont", 8), tags="dy")

    def draw_panel_stopwatch(self):
        if self.sw_cv is None:
            return
        txt = self.rig.stopwatch_display()
        if txt == self._sw_cache:
            return
        self._sw_cache = txt
        self.sw_cv.delete("all")
        w = max(self.sw_cv.winfo_width(), 254)
        draw_stopwatch(self.sw_cv, w * 0.5, 106, 62, "sw", txt)

    def tick(self):
        r = self.rig
        if self.part == "B":
            self.draw_panel_stopwatch()
            if hasattr(self, "sel_lbl") and self.sel_lbl.winfo_exists():
                if r.mode == "pendulum":
                    s = '핀에 걸린 구멍: #%d' \
                        % (r.hole_index + 1)
                elif r.sel_hole is not None:
                    s = '선택된 구멍: #%d' \
                        % (r.sel_hole + 1)
                else:
                    s = '선택된 구멍 없음'
                self.sel_lbl.config(text=s)
        sc = round(self.ppm / self.ppm_true, 2)
        if sc != self._scale_cache:
            self._scale_cache = sc
            self.scale_lbl.config(
                text='배율 %.2f×%s'
                % (sc, '  (실제 크기)'
                   if abs(sc - 1.0) < 0.01 else ""))
        self.redraw()


# ==========================================================================
#  application
# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed):
        super().__init__()
        self.truth = Truth(seed)
        self.rig = Rig(self.truth)
        self.title('IPhO 2011 실험 2 - 역학 블랙박스 (HaslaLab)')
        self.geometry("1300x830")
        try:
            self.ppm_true = float(self.winfo_fpixels("1i")) / 0.0254
        except Exception:
            self.ppm_true = 96.0 / 0.0254
        self.ppm_true = max(1200.0, min(6000.0, self.ppm_true))

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text='2. 역학 블랙박스: 공이 든 원통',
                  font=("TkDefaultFont", 12, "bold")).pack(side="left",
                                                           padx=10, pady=6)
        self.status_lbl = ttk.Label(top, text="")
        self.status_lbl.pack(side="right", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.pa = LabView(self.nb, self, "A")
        self.pb = LabView(self.nb, self, "B")
        self.nb.add(self.pa, text='Part A · 무게중심 / 길이')
        self.nb.add(self.pb, text='Part B · 주기')
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab)
        self.bind_all("<space>", self.on_space)
        self.bind_all("<KeyPress-space>", self.on_space)

        self.rig.enter_part_a()
        self.rig.move_ruler(-self.truth.L * 0.60, LOOP_DROP + 0.055)
        self.rig.pencil_to(self.truth.L * 0.30, LOOP_DROP + 0.090)
        self.rig.eraser_to(self.truth.L * 0.30 - 0.055, LOOP_DROP + 0.150)
        self._last = _time.perf_counter()
        self.after(30, self.loop)

    def status(self, msg):
        if msg:
            self.status_lbl.config(text=msg)

    def current(self):
        return self.pa if self.nb.index("current") == 0 else self.pb

    def on_space(self, _e=None):
        """Space bar: start the stopwatch, press again to stop it."""
        v = self.current()
        if v.sw_cv is not None:
            v.sw_toggle()
        return "break"

    def on_tab(self, _e=None):
        if self.nb.index("current") == 0:
            self.rig.enter_part_a()
        else:
            self.rig.enter_part_b()
        v = self.current()
        v.build_actions()
        v._static_key = None
        v.redraw()

    def refresh_all(self):
        self.pa.build_actions()
        self.pb.build_actions()
        self.current().redraw()

    def loop(self):
        now = _time.perf_counter()
        dt = min(0.06, now - self._last)
        self._last = now
        n = max(1, int(dt / 0.004) + 1)
        for _ in range(n):
            self.rig.step(dt / n)
        self.current().tick()
        self.after(16, self.loop)


def launch(seed):
    App(seed).mainloop()


# ==========================================================================
if __name__ == "__main__":
    _args = sys.argv[1:]
    if "--lang" in _args:
        LANG = _args[_args.index("--lang") + 1]
    _seed = OFFICIAL_SEED
    if "--seed" in _args:
        _seed = int(_args[_args.index("--seed") + 1])
    elif "--random" in _args:
        _seed = random.randrange(1, 10 ** 8)

    if "--selftest" in _args:
        sys.exit(0 if run_selftest() else 1)
    launch(_seed)
