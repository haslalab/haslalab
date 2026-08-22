#!/usr/bin/env python3
"""RMPh 2021 -- experimental round: measure the lifetime of the D0 meson.

This is the "D0 Exercise" half of the LHCb Masterclass application that the
organisers ran inside a Proxmox virtual machine (see
official/RMPh-2021_Technical-guide.pdf).  The application itself was never
handed out, but CERN preserves both the program and, more importantly, the very
same data:

    LHCb event file for real measurement  -- CERN Open Data record 401
    root://eospublic.cern.ch//eos/opendata/lhcb/MasterclassDatasets/D0lifetime/
        2014/MasterclassData.root
    https://opendata.cern.ch/record/401

That file ships with this archive as official/data/MasterclassData.root.  It is
real LHCb 2011 data: 91 583 D0 -> K- pi+ candidates, and it carries exactly the
four variables the exam describes, and nothing else:

    D0_MM          invariant mass, MeV        ("D0 mass")
    D0_TAU         decay time, ns             ("D0 TAU")
    D0_MINIPCHI2   minimum impact-parameter chi2, plotted and cut as log10
                                              ("D0 IP")
    D0_PT          transverse momentum, MeV   ("D0 PT")

so this program runs the exam on the original numbers.  The analysis follows the
procedure in the exam paper: fit the mass peak, define a signal window, subtract
the mass sidebands, fit the decay-time distribution, and repeat while moving one
cut to expose the systematic effect of tasks 2.3-2.6.

What the real data gives (see --selftest):
    loose IP cut  -> tau ~ 0.50 ps
    tightening it -> the fit falls and settles at about 0.42 ps
    PDG value       0.4101 ps

Usage:
    python rmph2021_d0_lifetime.py                     graphical interface
    python rmph2021_d0_lifetime.py --nscan 1           one measurement, text only
    python rmph2021_d0_lifetime.py --scan ip --nscan 9
    python rmph2021_d0_lifetime.py --selftest
"""

import argparse
import math
import os
import sys

import numpy as np

HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
NPZ = os.path.join(HERE, "d0_masterclass.npz")
ROOT_FILE = os.path.join(HERE, os.pardir, "official", "data", "MasterclassData.root")

M_LO, M_HI = 1816.0, 1914.0        # the range the exam paper quotes
TAU_LO, TAU_HI = 0.15, 20.0        # ps, as present in the data
# log10(IPCHI2).  The limits come from the sample itself; a fixed upper limit of
# 1.5 used to shut about a quarter of the candidates out for good, so the uncut
# lifetime -- the biased end the whole exercise scans away from -- could not be
# measured at all.
IP_LO, IP_HI = -5.0, 6.0


def load():
    """Real LHCb candidates as (mass/MeV, tau/ps, log10 IPCHI2, pT/GeV)."""
    if os.path.exists(NPZ):
        d = np.load(NPZ)
        return (d["mass"].astype(float), d["tau_ps"].astype(float),
                d["log10_ipchi2"].astype(float), d["pt_gev"].astype(float))
    try:
        import uproot
    except ImportError:
        sys.exit("neither %s nor uproot is available; run\n    pip install uproot\n"
                 "or keep d0_masterclass.npz next to this script" % NPZ)
    t = uproot.open(os.path.normpath(ROOT_FILE))["DecayTree;1"]
    mm = np.asarray(t["D0_MM"].array(library="np"), float)
    tau = np.asarray(t["D0_TAU"].array(library="np"), float)
    pt = np.asarray(t["D0_PT"].array(library="np"), float)
    ip = np.asarray(t["D0_MINIPCHI2"].array(library="np"), float)
    g = tau > 0
    return mm[g], tau[g] * 1000.0, np.log10(ip[g]), pt[g] / 1000.0


# ---------------------------------------------------------------------------
# fits
# ---------------------------------------------------------------------------

def fit_mass(mass, nbins=98):
    """Gaussian signal on a linear background, as the original 'Fit mass
    distribution' button did.  Returns (mean, sigma, n_signal, n_background)."""
    hist, edges = np.histogram(mass, bins=nbins, range=(M_LO, M_HI))
    ctr = 0.5 * (edges[1:] + edges[:-1])
    # linear background estimated from the outer thirds
    side = (ctr < M_LO + 0.30 * (M_HI - M_LO)) | (ctr > M_HI - 0.30 * (M_HI - M_LO))
    a, b = np.polyfit(ctr[side], hist[side], 1)
    peak = hist - (a * ctr + b)
    peak[peak < 0] = 0.0
    tot = peak.sum()
    mean = float((peak * ctr).sum() / tot)
    sigma = float(math.sqrt(max((peak * (ctr - mean) ** 2).sum() / tot, 1e-6)))
    return mean, sigma, tot, hist.sum() - tot


def fit_tau(times, weights, a, b):
    """Maximum likelihood for an exponential truncated to [a, b], with the
    (possibly negative) sideband-subtraction weights."""
    sw = float(weights.sum())
    if sw <= 0:
        return float("nan"), float("nan"), 0.0
    mean = float((weights * times).sum() / sw) - a
    span = b - a
    tau = max(1e-4, mean)
    for _ in range(400):
        e = math.exp(-span / tau)
        pred = tau - span * e / (1 - e)
        d = mean - pred
        tau = max(1e-4, tau + 0.7 * d)
        if abs(d) < 1e-12:
            break
    return tau, tau / math.sqrt(max(sw, 1.0)), sw


def measure(data, m1, m2, ipmax, taumin, taumax, ptmin, ptmax):
    mass, tau, ip, pt = data
    keep = ((ip <= ipmax) & (tau >= taumin) & (tau <= taumax) &
            (pt >= ptmin) & (pt <= ptmax) & (mass >= M_LO) & (mass <= M_HI))
    insig = keep & (mass >= m1) & (mass <= m2)
    inside = keep & ~((mass >= m1) & (mass <= m2))
    sig_w = m2 - m1
    sb_w = (m1 - M_LO) + (M_HI - m2)
    if sb_w <= 0:
        raise ValueError("leave some mass sidebands outside the signal region")
    times = np.concatenate([tau[insig], tau[inside]])
    w = np.concatenate([np.ones(int(insig.sum())),
                        np.full(int(inside.sum()), -sig_w / sb_w)])
    return fit_tau(times, w, taumin, taumax)


# ---------------------------------------------------------------------------
# graphical interface, laid out like the original "D0 Exercise" window
# ---------------------------------------------------------------------------

def launch_gui(data):
    import tkinter as tk
    from tkinter import ttk
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    mass, tau, ip, pt = data

    root = tk.Tk()
    root.title("LHCb Masterclass - D0 Exercise  (RMPh 2021 experimental round)")
    root.geometry("1280x800")

    left = ttk.Frame(root, padding=10)
    left.pack(side="left", fill="y")
    right = ttk.Frame(root, padding=6)
    right.pack(side="right", fill="both", expand=True)

    ttk.Label(left, text="Real LHCb 2011 data\n%d D0 candidates" % len(mass),
              justify="left").pack(anchor="w", pady=(0, 8))

    var = {}
    for label, default in (("Sig range low (MeV)", "1845"),
                           ("Sig range high (MeV)", "1885"),
                           ("log10(IP) max", "%.2f" % IP_HI),
                           ("TAU min (ps)", "0.25"),
                           ("TAU max (ps)", "10"),
                           ("PT min (GeV)", "0"),
                           ("PT max (GeV)", "20")):
        ttk.Label(left, text=label).pack(anchor="w")
        var[label] = tk.StringVar(value=default)
        ttk.Entry(left, textvariable=var[label], width=18).pack(anchor="w", pady=(0, 4))

    out = tk.Text(left, width=38, height=16)
    status = ttk.Label(left, text="Ready")

    fig = plt.figure(figsize=(9, 7))
    axm = fig.add_subplot(221)
    axt = fig.add_subplot(222)
    axi = fig.add_subplot(223)
    axp = fig.add_subplot(224)
    fig.tight_layout(pad=2.4)
    canvas = FigureCanvasTkAgg(fig, master=right)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    scan_pts = []

    def num(k):
        return float(var[k].get())

    def cuts():
        return (num("Sig range low (MeV)"), num("Sig range high (MeV)"),
                num("log10(IP) max"), num("TAU min (ps)"), num("TAU max (ps)"),
                num("PT min (GeV)"), num("PT max (GeV)"))

    def plot_mass():
        mean, sigma, ns, nb = fit_mass(mass)
        axm.clear()
        axm.hist(mass, bins=98, range=(M_LO, M_HI), color="#7aa6d6")
        m1, m2 = num("Sig range low (MeV)"), num("Sig range high (MeV)")
        axm.axvspan(m1, m2, color="#ffd27f", alpha=0.35)
        axm.set_xlabel("D0 mass (MeV)")
        axm.set_title("mean %.1f, sigma %.1f MeV" % (mean, sigma))
        canvas.draw()
        out.insert("end", "mass fit: mean = %.1f MeV, sigma = %.1f MeV\n"
                          "          signal ~ %.0f, background ~ %.0f\n"
                   % (mean, sigma, ns, nb))
        out.see("end")

    def apply_cuts():
        m1, m2, ipmax, tmin, tmax, ptmin, ptmax = cuts()
        keep = ((ip <= ipmax) & (tau >= tmin) & (tau <= tmax) &
                (pt >= ptmin) & (pt <= ptmax))
        s = keep & (mass >= m1) & (mass <= m2)
        b = keep & ~((mass >= m1) & (mass <= m2))
        # every panel spans the window that was asked for, clipped only by
        # what the sample holds, so no axis quietly hides part of the data
        def win(lo, hi, arr):
            lo = max(lo, float(arr.min()))
            hi = min(hi, float(arr.max()))
            return (lo, hi) if hi > lo else (float(arr.min()), float(arr.max()))

        for ax, vs, vb, xlabel, rng, logy in (
                (axt, tau[s], tau[b], "D0 TAU (ps)", win(tmin, tmax, tau), True),
                (axi, ip[s], ip[b], "log10(D0 IPCHI2)", win(IP_LO, IP_HI, ip), False),
                (axp, pt[s], pt[b], "D0 PT (GeV)", win(ptmin, ptmax, pt), False)):
            ax.clear()
            ax.hist(vs, bins=60, range=rng, histtype="step", color="tab:blue",
                    label="signal region")
            ax.hist(vb, bins=60, range=rng, histtype="step", color="tab:red",
                    label="sidebands")
            ax.set_xlabel(xlabel)
            if logy:
                ax.set_yscale("log")
            ax.legend(fontsize=7)
        canvas.draw()

    def fit_lifetime():
        m1, m2, ipmax, tmin, tmax, ptmin, ptmax = cuts()
        t, e, y = measure(data, m1, m2, ipmax, tmin, tmax, ptmin, ptmax)
        scan_pts.append((ipmax, t, e))
        out.insert("end", "tau = %.4f +- %.4f ps   (yield %.0f, log10(IP) < %g)\n"
                   % (t, e, y, ipmax))
        out.see("end")
        status.config(text="tau = %.4f ps" % t)
        if len(scan_pts) >= 2:
            axt.clear()
            xs = [p[0] for p in scan_pts]
            ys = [p[1] for p in scan_pts]
            es = [p[2] for p in scan_pts]
            axt.errorbar(xs, ys, yerr=es, fmt="o")
            axt.axhline(0.4101, color="grey", ls="--", lw=1)
            axt.set_xlabel("upper log10(IP) cut")
            axt.set_ylabel("fitted tau (ps)")
            canvas.draw()

    def reset_scan():
        scan_pts.clear()
        out.delete("1.0", "end")
        apply_cuts()

    for text, cmd in (("Plot D0 mass", plot_mass),
                      ("Apply cuts and plot variables", apply_cuts),
                      ("Fit lifetime", fit_lifetime),
                      ("Clear measurements", reset_scan)):
        ttk.Button(left, text=text, command=cmd).pack(fill="x", pady=3)

    status.pack(anchor="w", pady=6)
    out.pack(fill="x")

    plot_mass()
    apply_cuts()
    root.mainloop()


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="RMPh 2021 D0 lifetime analysis")
    ap.add_argument("--m1", type=float, default=1845.0)
    ap.add_argument("--m2", type=float, default=1885.0)
    ap.add_argument("--ipmax", type=float, default=IP_HI)
    ap.add_argument("--taumin", type=float, default=0.25)
    ap.add_argument("--taumax", type=float, default=10.0)
    ap.add_argument("--ptmin", type=float, default=0.0)
    ap.add_argument("--ptmax", type=float, default=70.0)
    ap.add_argument("--scan", choices=["ip", "tau", "pt"], default="ip")
    ap.add_argument("--nscan", type=int, default=0,
                    help="number of scan points; 0 opens the graphical interface")
    ap.add_argument("--scan-end", type=float)
    ap.add_argument("--csv")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    data = load()
    mass = data[0]

    if args.selftest:
        mean, sigma, ns, nb = fit_mass(mass)
        print("real LHCb data: %d candidates" % len(mass))
        print("mass fit: mean = %.1f MeV (PDG 1864.84), sigma = %.1f MeV" % (mean, sigma))
        print("signal ~ %.0f, background ~ %.0f in %g-%g MeV" % (ns, nb, M_LO, M_HI))
        print()
        print("  log10(IP) cut   tau (ps)     error     yield")
        for cut in (5.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.0, -0.5):
            t, e, y = measure(data, args.m1, args.m2, cut, args.taumin,
                              args.taumax, args.ptmin, args.ptmax)
            print("  %10.1f     %8.4f  %8.4f  %8.0f" % (cut, t, e, y))
        print()
        print("PDG D0 lifetime = 0.4101 ps")
        return

    if args.nscan <= 0:
        launch_gui(data)
        return

    if args.nscan == 1:
        t, e, y = measure(data, args.m1, args.m2, args.ipmax, args.taumin,
                          args.taumax, args.ptmin, args.ptmax)
        print("tau = %.4f +- %.4f ps   (background-subtracted yield %.0f)" % (t, e, y))
        return

    key = {"ip": "ipmax", "tau": "taumax", "pt": "ptmin"}[args.scan]
    start = getattr(args, key)
    end = args.scan_end if args.scan_end is not None else {"ip": -1.0, "tau": 2.0,
                                                           "pt": 4.0}[args.scan]
    print("%-18s %12s %12s %12s" % (args.scan + " cut", "tau (ps)", "error", "yield"))
    rows = []
    for i in range(args.nscan):
        v = start + (end - start) * i / (args.nscan - 1)
        kw = dict(m1=args.m1, m2=args.m2, ipmax=args.ipmax, taumin=args.taumin,
                  taumax=args.taumax, ptmin=args.ptmin, ptmax=args.ptmax)
        kw[key] = v
        t, e, y = measure(data, **kw)
        print("%-18.3f %12.4f %12.4f %12.0f" % (v, t, e, y))
        rows.append((v, t, e, y))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as fh:
            fh.write("cut,tau_ps,error_ps,yield\n")
            for r in rows:
                fh.write("%.6f,%.6f,%.6f,%.0f\n" % r)
        print("\nsaved to %s" % args.csv)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
