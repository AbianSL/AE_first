"""
Legt zwei Spektren (.dat, zwei Spalten: λ in Å, Fluss) übereinander,
mit den Linien aus dem Blatt.
Aufruf:  python3 compare.py datei1.dat datei2.dat
Ergebnis: figuras/compare_<name1>_vs_<name2>.pdf  (ein Bereich pro Seite)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

REGIONES = [(3900, 4100), (4100, 4300), (4300, 4500), (4500, 4700),
            (4700, 5000), (5000, 6000), (6000, 6800)]

# Linien aus dem Blatt (Name, λ in Å)
LINEAS = [
    ("Hε", 3970.07), ("Hδ", 4101.73), ("Hγ", 4340.47), ("Hβ", 4861.35),
    ("He I", 4026.19), ("He I", 4120.81), ("He I", 4143.76), ("He I", 4387.93),
    ("He I", 4471.48), ("He I", 4713.37), ("He I", 4921.93),
    ("He II", 4199.87), ("He II", 4541.59), ("He II", 4685.68),
    ("Ca II K", 3933.663), ("Ca II H", 3968.49), ("N IV", 4057.759),
    ("O II", 4069.636), ("O II", 4072.164), ("O II", 4075.868),
    ("Si IV", 4088.863), ("Si IV", 4116.104), ("Si II", 4128.054),
    ("Si II", 4130.894), ("O II", 4132.00), ("C III", 4153.685),
    ("C III", 4155.80), ("O II", 4185.00), ("C III", 4186.900), ("O II", 4189.00),
    ("Si IV", 4212.00), ("N II", 4237.07), ("N II", 4241.55), ("N II", 4242.424),
    ("C II", 4267.01), ("O II", 4277.4265), ("O II", 4317.139), ("O II", 4319.631),
    ("O II", 4366.00), ("O II", 4414.90), ("O II", 4416.97), ("O II", 4452.00),
    ("Mg II", 4481.13), ("N IV", 4513.3), ("N III", 4516.12), ("N III", 4519.41),
    ("N III", 4530.84), ("N III", 4534.57), ("Si III", 4539.00),
    ("Si III", 4552.654), ("Si III", 4554.00), ("Si III", 4567.872),
    ("Si III", 4574.777), ("N V", 4603.73), ("N IV", 4607.30), ("N III", 4634.12),
    ("O II", 4638.00), ("C III", 4640.03), ("N III", 4640.64), ("N III", 4641.85),
    ("C III", 4647.419), ("O II", 4649.1348), ("C III", 4650.246),
    ("O II", 4650.8384), ("C III", 4651.016), ("C III", 4651.473),
    ("C III", 4652.049), ("Si IV", 4654.00), ("C III", 4659.06), ("O II", 4661.00),
    ("O II", 4676.00),
    ("Fe II", 4922.1), ("TiO", 4584), ("TiO", 4623), ("TiO", 4759), ("TiO", 4804),
    ("TiO", 4954), ("Banda G", 4300), ("Li I", 6708), ("Mn I", 4030),
    ("Mn I", 4034), ("Fe II", 4416.8), ("Ca I", 4226), ("Fe I", 4383),
    ("Fe I", 4143.8),
]


def leer(ruta):
    d = np.genfromtxt(ruta, comments="#", invalid_raise=False)
    d = d[np.isfinite(d).all(axis=1)]
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1]


def poner_lineas(ax, a, b):
    """Senkrechte Linie bei jedem λ, Beschriftung darüber. Zu dicht liegende
    Beschriftungen werden etwas auseinandergeschoben und mit einem Strich
    mit ihrem λ verbunden. y in Achsen-Koordinaten (0 = unten, 1 = oben),
    damit es für jeden Flussbereich funktioniert."""
    sel = sorted([(n, l) for n, l in LINEAS if a < l < b], key=lambda t: t[1])
    if not sel:
        return
    t = ax.get_xaxis_transform()            # x in Å, y in Achsen-Anteilen
    sep = 0.013 * (b - a)
    pos = [l for _, l in sel]
    for _ in range(100):
        cambio = False
        for i in range(1, len(pos)):
            if pos[i] - pos[i - 1] < sep:
                d = (sep - (pos[i] - pos[i - 1])) / 2
                pos[i - 1] -= d; pos[i] += d
                cambio = True
        if not cambio:
            break
    for (nombre, l), p in zip(sel, pos):
        ax.plot([l, l], [0, 0.66], color="tab:blue", lw=0.5, ls=":", transform=t)
        ax.plot([l, p], [0.66, 0.70], color="tab:blue", lw=0.5, transform=t)
        ax.text(p, 0.71, f"{nombre} {l:.0f}", rotation=90, fontsize=6.5,
                ha="center", va="bottom", color="tab:blue", transform=t)


if len(sys.argv) != 3:
    sys.exit("Aufruf: python3 compare.py datei1.dat datei2.dat")

os.makedirs("figuras", exist_ok=True)

f1, f2 = sys.argv[1], sys.argv[2]
n1 = os.path.splitext(os.path.basename(f1))[0]
n2 = os.path.splitext(os.path.basename(f2))[0]
lam1, flujo1 = leer(f1)
lam2, flujo2 = leer(f2)
salida = f"figuras/compare_{n1}_vs_{n2}.pdf"

with PdfPages(salida) as pdf:
    for a, b in REGIONES:
        s1 = (lam1 >= a) & (lam1 <= b)
        s2 = (lam2 >= a) & (lam2 <= b)
        if s1.sum() == 0 and s2.sum() == 0:
            continue
        fig, ax = plt.subplots(figsize=(13, 6))
        ax.plot(lam1[s1], flujo1[s1], color="black", lw=0.8, label=n1)
        ax.plot(lam2[s2], flujo2[s2], color="tab:red", lw=0.8, alpha=0.8, label=n2)
        # gemeinsamer y-Bereich, oben Platz für die Beschriftung
        y = np.concatenate([flujo1[s1], flujo2[s2]])
        lo, hi = np.min(y), np.max(y)
        ax.set_ylim(lo - 0.05 * (hi - lo), hi + 0.6 * (hi - lo))
        ax.set_xlim(a, b)
        ax.set_xlabel("λ (Å)"); ax.set_ylabel("Fluss")
        ax.set_title(f"{a}–{b} Å")
        ax.legend(loc="lower left", fontsize=9)
        poner_lineas(ax, a, b)
        fig.tight_layout()
        pdf.savefig(fig); plt.close(fig)

print(salida)
