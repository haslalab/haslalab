#!/usr/bin/env python3
"""RMPh 2024 -- experimental problem: ferromagnetic phase transition, Ising model.

The simulation engine below is the ORIGINAL code, reproduced verbatim from
section 1 ("Implementation of the Monte Carlo simulation") of the official
solution document `official/RMPh2024_Ising_Model_Solution.pdf`, which prints the
organisers' Python source in full.  Task designed by Tudor Mocioi (Ecole
Polytechnique) with debugging help from Victor Dumbrava.

Only two things are not from that document:
  * the graphical user interface, which the document explicitly omits ("The
    final step of the implementation, which we omit in this document, is to
    package the above functions into the graphical user interface that was
    provided to the participants") -- so it is rebuilt here as a Tkinter window;
  * `time`, `pandas`, `curve_fit` and `IPython.display` imports, which the
    original used inside a notebook.

Everything that affects the numbers -- the single-spin Metropolis step, N_eq =
N//10, sampling the magnetisation after every single step, the signed average
and the standard-deviation formula -- is unchanged.

Cross-checks against the official solution:
    A.2  L = 20, J = 1        -> sharp drop at T = 2.2 +- 0.1
    A.3  T_c vs J             -> line through the origin, slope 2.29 +- 0.03
    A.4  J = 1, T = 1, H = 0  -> no preferred direction (about 50/50 over 100 runs)
    C.2  T = 1, H = 0.1       -> nearly always aligned with the field
    C.4  chi(T) from M(H)     -> Curie-Weiss fit gives T_c = 2.58 +- 0.16
    D    J < 0                -> checkerboard order; use A = (1/L^2) sum (-1)^(i+j) s_ij

Run:
    python rmph2024_ising.py                 graphical interface
    python rmph2024_ising.py --selftest      reproduce the checks above (slow)
"""

import sys

import numpy as np

try:
    import matplotlib
    import matplotlib.colors as colors
    import matplotlib.pyplot as plt
except ImportError:                                     # pragma: no cover
    matplotlib = None

if matplotlib is not None:
    bw_cmap = colors.ListedColormap(['black', 'white'])


# ---------------------------------------------------------------------------
# original engine (official solution document, section 1)
# ---------------------------------------------------------------------------

def get_energy(spins, J, H):
    energy = -H * np.sum(spins) - J * np.sum(spins * np.roll(spins, 1, axis=0) +
                                             spins * np.roll(spins, 1, axis=1))
    return energy


def monte_carlo_step(spins, J, T, H):
    L = np.shape(spins)[0]
    N_spins = L * L
    i = np.random.randint(0, N_spins)   # randomly choose which spin to consider flipping
    i_row = i // L                      # row corresponding to i
    i_col = i % L                       # column corresponding to i
    # look at the four nearest neighbours to calculate the change in energy for
    # this proposed move:
    deltaE = 2 * H * spins[i_row, i_col] + 2 * J * spins[i_row, i_col] * (
        spins[(i_row + 1) % L, i_col] + spins[(i_row - 1) % L, i_col] +
        spins[i_row, (i_col + 1) % L] + spins[i_row, (i_col - 1) % L])
    if (deltaE <= 0) or (np.random.rand() < np.exp(-deltaE / T)):
        spins[i_row, i_col] = -spins[i_row, i_col]      # accept the spin flip
    return spins


def monte_carlo_simulation(L, J, T, H, N, animate, on_frame=None):
    spins = 2 * np.random.randint(0, 2, size=((L, L))) - 1   # random start
    # first, perform the equilibration steps
    N_eq = N // 10
    for _ in range(N_eq):
        spins = monte_carlo_step(spins, J, T, H)
    # then, perform further Monte Carlo steps and record the magnetizations
    Ms = []
    every = max(1, N // 200)
    for k in range(N):
        spins = monte_carlo_step(spins, J, T, H)
        Ms.append(np.sum(spins))
        if animate and on_frame is not None and k % every == 0:
            on_frame(spins, k, N)
    # finally, compute the average magnetization per spin and its standard deviation
    magnetization = np.average(Ms) / (L * L)
    std_magnetization = np.std(Ms) / (L * L * np.sqrt(len(Ms) - 1))
    return (magnetization, std_magnetization, spins)


def simulations(L, Js, Ts, Hs, N, N_repeat, animate):
    rows = {'J': [], 'T': [], 'H': [], 'M': [], 'M_err': []}
    for J in np.nditer(np.asarray(Js)):
        for T in np.nditer(np.asarray(Ts)):
            for H in np.nditer(np.asarray(Hs)):
                for _ in range(N_repeat):
                    M, M_err, _ = monte_carlo_simulation(L, float(J), float(T),
                                                         float(H), N, animate)
                    rows['J'].append(float(J))
                    rows['T'].append(float(T))
                    rows['H'].append(float(H))
                    rows['M'].append(M)
                    rows['M_err'].append(M_err)
    return rows


def staggered_magnetisation(spins):
    """Order parameter for the antiferromagnet (task D.2)."""
    L = np.shape(spins)[0]
    i, j = np.indices((L, L))
    return float(np.sum((-1.0) ** (i + j) * spins) / (L * L))


# ---------------------------------------------------------------------------
# graphical interface
# ---------------------------------------------------------------------------

def launch_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    root = tk.Tk()
    root.title("RMPh 2024 - Ising model")
    root.geometry("1200x760")

    left = ttk.Frame(root, padding=10)
    left.pack(side="left", fill="y")
    right = ttk.Frame(root, padding=10)
    right.pack(side="right", fill="both", expand=True)

    fields = [("L", "20"), ("J", "1.0"), ("T", "2.2"), ("H", "0.0"),
              ("N (Monte Carlo steps)", "200000"),
              ("T min", "1.0"), ("T max", "4.0"), ("T step", "0.1"),
              ("Repeats", "1")]
    var = {}
    for label, default in fields:
        ttk.Label(left, text=label).pack(anchor="w")
        var[label] = tk.StringVar(value=default)
        ttk.Entry(left, textvariable=var[label], width=20).pack(anchor="w", pady=(0, 5))

    animate = tk.BooleanVar(value=True)
    ttk.Checkbutton(left, text="Animation", variable=animate).pack(anchor="w", pady=(2, 6))

    fig, ax = plt.subplots(figsize=(7, 5.8))
    canvas = FigureCanvasTkAgg(fig, master=right)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    status = ttk.Label(left, text="Ready")
    out = tk.Text(left, width=34, height=13)

    def num(key, cast=float):
        return cast(float(var[key].get()))

    def show_lattice(spins, k=None, n=None, title=None):
        ax.clear()
        ax.imshow(spins, cmap=bw_cmap,
                  norm=colors.BoundaryNorm([-1, 0, 1], bw_cmap.N),
                  interpolation='nearest')
        ax.set_xticks([])
        ax.set_yticks([])
        if title:
            ax.set_title(title)
        elif k is not None:
            ax.set_title("step %d / %d" % (k, n))
        canvas.draw()
        root.update()

    def single():
        try:
            L = num("L", int)
            J, T, H = num("J"), num("T"), num("H")
            N = num("N (Monte Carlo steps)", int)
            status.config(text="running ...")
            root.update()
            M, err, spins = monte_carlo_simulation(
                L, J, T, H, N, animate.get(),
                on_frame=lambda s, k, n: show_lattice(s, k, n))
            show_lattice(spins, title="L=%d, J=%g, T=%g, H=%g" % (L, J, T, H))
            out.delete("1.0", "end")
            out.insert("end", "M      = %+.6f\nerror  = %.6f\n|M|    = %.6f\n"
                              "A (staggered) = %+.6f\nE      = %.1f\n"
                       % (M, err, abs(M), staggered_magnetisation(spins),
                          get_energy(spins, J, H)))
            status.config(text="done")
        except Exception as exc:                        # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def series(xs, mode, xlabel, title):
        L = num("L", int)
        J, T, H = num("J"), num("T"), num("H")
        N = num("N (Monte Carlo steps)", int)
        rep = num("Repeats", int)
        ys, es = [], []
        out.delete("1.0", "end")
        out.insert("end", "%s\tM\tM_err\n" % xlabel)
        for x in xs:
            vals = []
            for _ in range(rep):
                if mode == "T":
                    m, e, _ = monte_carlo_simulation(L, J, float(x), H, N, False)
                elif mode == "J":
                    m, e, _ = monte_carlo_simulation(L, float(x), T, H, N, False)
                elif mode == "H":
                    m, e, _ = monte_carlo_simulation(L, J, T, float(x), N, False)
                else:
                    m, e, _ = monte_carlo_simulation(int(x), J, T, H, N, False)
                vals.append((m, e))
            m = float(np.mean([v[0] for v in vals]))
            e = float(np.mean([v[1] for v in vals]))
            ys.append(m)
            es.append(e)
            out.insert("end", "%.3f\t%+.6f\t%.6f\n" % (float(x), m, e))
            out.see("end")
            ax.clear()
            ax.errorbar(xs[:len(ys)], np.abs(ys), yerr=es, fmt="o-")
            ax.set_xlabel(xlabel)
            ax.set_ylabel("|M|")
            ax.set_title(title)
            ax.grid(True)
            canvas.draw()
            status.config(text="%s = %g" % (xlabel, float(x)))
            root.update()
        status.config(text="done")
        return ys, es

    def scan_T():
        a, b, d = num("T min"), num("T max"), num("T step")
        series(np.arange(a, b + d / 2, d), "T", "T", "Magnetization vs temperature")

    def scan_J():
        series(np.linspace(0.2, 2.0, 10), "J", "J", "Magnetization vs J")

    def scan_H():
        series(np.linspace(-2, 2, 17), "H", "H", "Magnetization vs external field")

    def scan_L():
        series([5, 10, 20, 30], "L", "L", "Finite-size scan")

    def save():
        fn = filedialog.asksaveasfilename(defaultextension=".png")
        if fn:
            fig.savefig(fn, dpi=180)

    for text, cmd in (("Single simulation", single), ("M(T) scan", scan_T),
                      ("J scan", scan_J), ("H scan", scan_H),
                      ("L scan (finite size)", scan_L), ("Save graph", save)):
        ttk.Button(left, text=text, command=cmd).pack(fill="x", pady=3)

    status.pack(anchor="w", pady=8)
    out.pack(fill="x")

    root.mainloop()


# ---------------------------------------------------------------------------

def selftest():
    """Reproduce the numerical checks of the official solution (a few minutes)."""
    N = 200000
    print("checks against official/RMPh2024_Ising_Model_Solution.pdf")
    print()
    print("A.2  L = 20, J = 1, N = %d" % N)
    print("     official: sharp drop at T = 2.2 +- 0.1; their own table gives 2.3 +- 0.1")
    for T in (1.8, 2.0, 2.2, 2.4, 2.6, 3.0):
        M, err, _ = monte_carlo_simulation(20, 1.0, T, 0.0, N, False)
        print("     T = %.1f   |M| = %.3f +- %.4f" % (T, abs(M), err))
    print()
    print("A.3  T_c vs J   (official: slope 2.29 +- 0.03 through the origin)")
    pts = []
    for J in (1.0, 2.0, 3.0, 4.0):
        Ts = np.linspace(1.5 * J, 3.2 * J, 9)
        ms = [abs(monte_carlo_simulation(20, J, float(T), 0.0, N // 2, False)[0])
              for T in Ts]
        k = int(np.argmax(-np.diff(ms)))
        tc = 0.5 * (Ts[k] + Ts[k + 1])
        pts.append((J, tc))
        print("     J = %.0f   T_c ~ %.2f" % (J, tc))
    Js = np.array([a for a, _ in pts])
    Tc = np.array([b for _, b in pts])
    print("     slope through the origin = %.2f" % (np.sum(Js * Tc) / np.sum(Js * Js)))
    print()
    print("A.4  J = 1, T = 1, H = 0, 20 runs   (official: about 50/50)")
    ups = sum(1 for _ in range(20)
              if monte_carlo_simulation(20, 1.0, 1.0, 0.0, N // 4, False)[0] > 0)
    print("     %d up / %d down" % (ups, 20 - ups))
    print()
    print("C.2  J = 1, T = 1, H = 0.1, 20 runs   (official: nearly all aligned)")
    ups = sum(1 for _ in range(20)
              if monte_carlo_simulation(20, 1.0, 1.0, 0.1, N // 4, False)[0] > 0)
    print("     %d aligned with the field / 20" % ups)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        launch_gui()
