#!/usr/bin/env python3
"""EuPhO 2020 Online -- Experimental Problem 2: (Mechanical) Black Box.

Faithful Python port of the official C++ simulator (Exp2-WIN.exe / Exp2-Linux /
Exp2-OSX), reconstructed from the officially published source code
(sources.zip -> Experiment_2/, by Richard Luhtaru).

Everything that matters for grading is identical to the original: the hidden
masses and spring constants, the non-linear springs, the two damping laws, the
modified-Euler integrator with dt = 0.1 ms, the 5 mN Gaussian force noise, the
command grammar, the abort conditions and the layout of the .txt output file.

Run:   python eupho2020_e2_black_box.py            (real-time pacing, as in the exam)
       python eupho2020_e2_black_box.py --nowait   (run as fast as possible)
Quit:  type "quit", or Ctrl+C
"""

import math
import os
import random
import sys
import time as _time

# --- hidden parameters (constants.h) -----------------------------------------
G = 9.81
Y1_INIT = 1.8          # initial height of the upper side of the box [m]
Y_CEIL = 3.0
Y_FLOOR = 0.0
BOX_SIZE = 0.6

M1, M2, M3 = 0.857, 0.236, 0.413

K1_LIN, K1_SQ, K1_CUB = 32.06, 20.0, 0.0    # k1_local = 39.2 N/m at equilibrium
K2_LIN, K2_SQ, K2_CUB = 16.37, 15.0, 0.0    # k2_local = 22.6 N/m at equilibrium

B1 = 0.22              # box:    F = -b1 * v|v|
B2 = 0.08              # mass 2: F = -b2 * (v - v_box)
B3 = 0.08              # mass 3: F = -b3 * (v - v_box)

DT = 0.0001            # integrator step [s]
FORCE_ERROR = 0.005    # sigma of the force reading [N]
HEIGHT_ERROR = 0.0

# --- interface limits (input.h, simulation.h) --------------------------------
MAX_REPEAT_NUM = 1000
MIN_SAMPLING_TIME = 10           # ms
MAX_SAMPLING_TIME = 1000 * 1000  # ms
MIN_ACC_DURATION = 10            # ms
MAX_ACC_DURATION = 10000 * 1000  # ms
MAX_ACCELERATION = 30            # m/s^2
OUTPUT_RESOLUTION = 50           # ms between terminal refreshes

HEADER = "| Time (s) | Force (N) | Accel (m/s^2) |"

CHANGE_ACCELERATION, CHANGE_SAMPLING_TIME, REPEAT, END_REPEAT = range(4)

STATUS_OK, HIT_CEILING, HIT_FLOOR, HIT_M1_M2, HIT_M2_M3, HIT_M1_M3 = range(6)

STATUS_TEXT = {
    STATUS_OK:   "Experiment ended successfully.",
    HIT_CEILING: "The box hit the ceiling. Experiment ended.",
    HIT_FLOOR:   "The box hit the floor. Experiment ended.",
    HIT_M1_M2:   "Masses and/or the box collided. Experiment ended.",
    HIT_M2_M3:   "Masses and/or the box collided. Experiment ended.",
    HIT_M1_M3:   "Masses and/or the box collided. Experiment ended.",
}

REALTIME = "--nowait" not in sys.argv


def k_of(lin, sq, cub, x):
    return lin + sq * x + cub * x * x


class Simulation:
    def __init__(self):
        # equilibrium heights of the two inner masses, solved iteratively
        f1 = (M2 + M3) * G
        f2 = M3 * G
        y2 = Y1_INIT
        for _ in range(20):
            y2 = Y1_INIT - f1 / k_of(K1_LIN, K1_SQ, K1_CUB, Y1_INIT - y2)
        y3 = y2
        for _ in range(20):
            y3 = y2 - f2 / k_of(K2_LIN, K2_SQ, K2_CUB, y2 - y3)

        self.y1, self.v1 = Y1_INIT, 0.0
        self.y2, self.v2 = y2 + random.gauss(0, HEIGHT_ERROR) if HEIGHT_ERROR else y2, 0.0
        self.y3, self.v3 = y3 + random.gauss(0, HEIGHT_ERROR) if HEIGHT_ERROR else y3, 0.0
        self.a1 = 0.0

    def force(self):
        k1 = k_of(K1_LIN, K1_SQ, K1_CUB, self.y1 - self.y2)
        return (M1 * self.a1 + B1 * self.v1 * abs(self.v1)
                + k1 * (self.y1 - self.y2) + M1 * G
                + random.gauss(0.0, FORCE_ERROR))

    def step(self, dt):
        v1, y1 = self.v1, self.y1
        v2, y2 = self.v2, self.y2
        v3, y3 = self.v3, self.y3

        v1n = v1 + self.a1 * dt
        y1n = y1 + 0.5 * (v1 + v1n) * dt

        k1 = k_of(K1_LIN, K1_SQ, K1_CUB, y1 - y2)
        k2 = k_of(K2_LIN, K2_SQ, K2_CUB, y2 - y3)
        v2d0 = -B2 / M2 * (v2 - v1) + k1 / M2 * (y1 - y2) - k2 / M2 * (y2 - y3) - G
        v3d0 = -B3 / M3 * (v3 - v1) + k2 / M3 * (y2 - y3) - G
        y2d0, y3d0 = v2, v3

        v2g, y2g = v2 + v2d0 * dt, y2 + y2d0 * dt
        v3g, y3g = v3 + v3d0 * dt, y3 + y3d0 * dt

        k1 = k_of(K1_LIN, K1_SQ, K1_CUB, y1n - y2g)
        k2 = k_of(K2_LIN, K2_SQ, K2_CUB, y2g - y3g)
        v2d1 = -B2 / M2 * (v2g - v1n) + k1 / M2 * (y1n - y2g) - k2 / M2 * (y2g - y3g) - G
        v3d1 = -B3 / M3 * (v3g - v1n) + k2 / M3 * (y2g - y3g) - G
        y2d1, y3d1 = v2g, v3g

        self.v1, self.y1 = v1n, y1n
        self.v2 = v2 + 0.5 * (v2d0 + v2d1) * dt
        self.y2 = y2 + 0.5 * (y2d0 + y2d1) * dt
        self.v3 = v3 + 0.5 * (v3d0 + v3d1) * dt
        self.y3 = y3 + 0.5 * (y3d0 + y3d1) * dt

        if self.y1 > Y_CEIL:
            return HIT_CEILING
        if self.y1 - BOX_SIZE < Y_FLOOR:
            return HIT_FLOOR
        if self.y2 > self.y1:
            return HIT_M1_M2
        if self.y3 > self.y2:
            return HIT_M2_M3
        if self.y3 < self.y1 - BOX_SIZE:
            return HIT_M1_M3
        return STATUS_OK


# --- input parsing (input.cpp) -----------------------------------------------

class ParseError(Exception):
    pass


def _to_int(tok):
    try:
        return int(tok)
    except ValueError:
        raise ParseError("Invalid entry. Please try again.")


def _to_float(tok):
    try:
        return float(tok)
    except ValueError:
        raise ParseError("Invalid entry. Please try again.")


def process_inputline(seq, state, text):
    """Append actions to seq. Returns 'ok', 'begin' or 'quit'."""
    toks = [t for t in text.split(' ') if t != '']
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "repeat":
            if state["inrepeat"]:
                raise ParseError("Cannot repeat actions inside another repeat. Please try again.")
            if i + 1 >= len(toks):
                raise ParseError("Invalid entry. Please try again.")
            n = _to_int(toks[i + 1])
            if n < 1 or n > MAX_REPEAT_NUM:
                raise ParseError("Number of repeat times is out of range. Please try again.")
            seq.append((REPEAT, n))
            state["inrepeat"] = True
            i += 2
        elif t == "sample":
            if i + 1 >= len(toks):
                raise ParseError("Invalid entry. Please try again.")
            s = _to_float(toks[i + 1])
            if s * 1000 > MAX_SAMPLING_TIME:
                raise ParseError("Sampling time is out of range. Please try again.")
            ms = int(round(s * 1000 / MIN_SAMPLING_TIME)) * MIN_SAMPLING_TIME
            if ms <= 0:
                ms = MIN_SAMPLING_TIME
            seq.append((CHANGE_SAMPLING_TIME, ms))
            i += 2
        elif t == "endrepeat":
            if not state["inrepeat"]:
                raise ParseError("Cannot end repeat outside repeat. Please try again.")
            state["inrepeat"] = False
            seq.append((END_REPEAT, None))
            i += 1
        elif t == "begin":
            return "begin"
        elif t == "quit":
            return "quit"
        else:
            d = _to_float(t)
            if d * 1000 > MAX_ACC_DURATION or d < 0:
                raise ParseError("Duration is out of range. Please try again.")
            if i + 1 >= len(toks):
                raise ParseError("Invalid entry. Please try again.")
            a = _to_float(toks[i + 1])
            if a < -MAX_ACCELERATION or a > MAX_ACCELERATION:
                raise ParseError("Acceleration is out of range. Please try again.")
            seq.append((CHANGE_ACCELERATION, (a, int(round(d * 1000 / MIN_ACC_DURATION)) * MIN_ACC_DURATION)))
            i += 2
    return "ok"


def describe_sequence(seq, current, out):
    out.append("Current experiment sequence:" if current else "Experiment sequence:")
    inrepeat = False
    for typ, arg in seq:
        pad = "    " if inrepeat else "  "
        if typ == CHANGE_ACCELERATION:
            a, dur = arg
            out.append("%sAccelerate the box with a = %+.2f m/s^2 for %.2f seconds." % (pad, a, dur / 1000.0))
        elif typ == CHANGE_SAMPLING_TIME:
            out.append("%sChange sampling time to every %.2f seconds." % (pad, arg / 1000.0))
        elif typ == REPEAT:
            out.append("  Repeat %d times:" % arg)
            inrepeat = True
        elif typ == END_REPEAT:
            inrepeat = False
    out.append("")


def get_input():
    seq = []
    state = {"inrepeat": False}
    while True:
        if seq:
            lines = []
            describe_sequence(seq, True, lines)
            print("\n".join(lines))
        print('Enter "(duration in s) (acceleration in m/s^2)" (e.g. "1.5 -0.4") to add to sequence. (Max acceleration: 30 m/s^2)')
        print('Enter "repeat (number of times)" (e.g. "repeat 10") to repeat actions.')
        print('Enter "endrepeat" to end repeating actions.')
        print('Enter "sample (time in s)" (e.g. "sample 0.4") to change sampling time for the output file. (Default: 0.01 s)')
        print('Enter "begin" to start the experiment.')
        print('Enter "quit" to exit the program.')
        print('You can write multiple instructions on the same line (e.g. "1.5 -0.4 repeat 10 1.5 0.4 endrepeat").')

        line = sys.stdin.readline()
        if not line:
            return None, None
        print()
        try:
            status = process_inputline(seq, state, line.rstrip("\n").rstrip("\r"))
        except ParseError as exc:
            print("\n******* %s *******\n" % exc)
            continue

        if status == "ok":
            print("\n********************************")
        elif status == "quit":
            return None, None
        else:
            print('Enter name for output file (e.g. "results"). You should use Latin '
                  'letters and numbers because some special characters are not allowed.')
            name = sys.stdin.readline()
            name = (name or "").strip() or "results"
            print("\n******* Begin experiment. *******\n")
            return seq, name + ".txt"


def run_experiment(seq, sim, filename):
    # unpack repeats
    flat = []
    i = 0
    while i < len(seq):
        typ, arg = seq[i]
        if typ in (CHANGE_SAMPLING_TIME, CHANGE_ACCELERATION):
            flat.append((typ, arg))
            i += 1
        elif typ == REPEAT:
            block = []
            i += 1
            while i < len(seq):
                if seq[i][0] == END_REPEAT:
                    i += 1
                    break
                block.append(seq[i])
                i += 1
            flat.extend(block * arg)
        else:
            i += 1

    rows = []
    header_written = False
    time_ms = 0
    last_sample = -MAX_SAMPLING_TIME
    sampling = 10
    begin_wall = _time.monotonic()
    first_output = True
    status = STATUS_OK

    def sample_now():
        nonlocal header_written
        if not header_written:
            header_written = True
            rows.append("EuPhO 2020 - Experiment 2")
            rows.append("")
            describe_sequence(seq, False, rows)
            rows.append(HEADER)
        rows.append("| %8.2f | %9.2f | %+13.2f |" % (time_ms / 1000.0, sim.force(), sim.a1))

    def terminal_now():
        nonlocal first_output
        txt = "| %8.2f | %9.2f | %+13.2f |" % (time_ms / 1000.0, sim.force(), sim.a1)
        if first_output:
            first_output = False
            print(HEADER)
            sys.stdout.write(txt)
        else:
            sys.stdout.write("\b" * len(HEADER) + txt)
        sys.stdout.flush()

    substeps = int(round(1.0 / (1000 * DT)))
    for typ, arg in flat:
        if typ == CHANGE_SAMPLING_TIME:
            sampling = arg
            continue
        a, duration = arg
        sim.a1 = a
        t_start = time_ms
        while time_ms - t_start < duration:
            if time_ms - last_sample >= sampling:
                sample_now()
                last_sample = time_ms
            if time_ms % OUTPUT_RESOLUTION == 0:
                if REALTIME:
                    while (_time.monotonic() - begin_wall) * 1000 < time_ms:
                        _time.sleep(0.002)
                terminal_now()
            for _ in range(substeps):
                status = sim.step(1.0 / 1000 / substeps)
                if status != STATUS_OK:
                    break
            if status != STATUS_OK:
                rows.append("")
                rows.append(STATUS_TEXT[status])
                _write(filename, rows)
                return status
            time_ms += 1

    if time_ms - last_sample >= sampling:
        sample_now()
    if time_ms % OUTPUT_RESOLUTION == 0:
        terminal_now()
    rows.append("")
    rows.append(STATUS_TEXT[STATUS_OK])
    _write(filename, rows)
    return STATUS_OK


def _write(filename, rows):
    try:
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")
    except OSError:
        pass  # invalid filename -> readings are simply not saved, as in the original


def main():
    print("EuPhO 2020 - Experiment 2")
    print()
    while True:
        sim = Simulation()
        seq, filename = get_input()
        if seq is None:
            break
        status = run_experiment(seq, sim, filename)
        print()
        print()
        print(STATUS_TEXT[status])
        print()
        print()
        print("********************************")
        print()
        if os.path.exists(filename):
            print("Readings saved to %s" % os.path.abspath(filename))
            print()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
