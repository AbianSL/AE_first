"""
Rectifica las estrellas problema y dibuja el espectro con las líneas de la hoja.
Uso:  python3 espectros_con_lineas.py
Resultado: figuras/EstrellaProblema1.pdf y figuras/EstrellaProblema2.pdf
           (una región del espectro por página)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from numpy.polynomial import legendre as L
from scipy.interpolate import PchipInterpolator

# Estrella -> método de rectificación ("polinomio" para la caliente,
# "envolvente" para la fría)
ESTRELLAS = {"EstrellaProblema1.dat": "polinomio",
             "EstrellaProblema2.dat": "envolvente"}

REGIONES = [(3900, 4100), (4100, 4300), (4300, 4500), (4500, 4700),
            (4700, 5000), (5000, 6000), (6000, 6800)]

# Líneas de la hoja (nombre, λ en Å)
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


# ----------------------------------------------------------------- rectificación
def leer(ruta):
    d = np.genfromtxt(ruta, comments="#", invalid_raise=False)
    d = d[np.isfinite(d).all(axis=1)]
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1]


def continuo_polinomio(lam, flujo, orden=6):
    """Polinomio ajustado iterativamente, descartando los puntos en líneas."""
    x = 2 * (lam - lam.min()) / (lam.max() - lam.min()) - 1
    usar = np.ones_like(lam, dtype=bool)
    for a, b in [(3925, 3985), (4060, 4145), (4300, 4380), (4820, 4900), (6520, 6600)]:
        usar &= ~((lam > a) & (lam < b))
    for _ in range(20):
        cont = L.legval(x, L.legfit(x[usar], flujo[usar], orden))
        r = flujo - cont
        s = np.std(r[usar])
        nuevo = usar & (r > -1.5 * s) & (r < 3 * s)
        if nuevo.sum() == usar.sum():
            break
        usar = nuevo
    return cont


def continuo_envolvente(lam, flujo, ancho=25.0, percentil=95):
    """Pseudo-continuo: nivel alto del flujo en tramos de 'ancho' Å."""
    xs, ys = [], []
    for a in np.arange(lam.min(), lam.max(), ancho):
        s = (lam >= a) & (lam < a + ancho)
        if s.sum() < 10:
            continue
        nivel = np.percentile(flujo[s], percentil)
        xs.append(np.mean(lam[s][flujo[s] >= nivel]))
        ys.append(nivel)
    return PchipInterpolator(xs, ys)(lam)


# ----------------------------------------------------------------- líneas
def poner_lineas(ax, a, b):
    """Línea vertical en cada λ y su etiqueta encima. Si dos etiquetas
    quedan muy juntas se separan un poco y una rayita las une a su λ."""
    sel = sorted([(n, l) for n, l in LINEAS if a < l < b], key=lambda t: t[1])
    if not sel:
        return
    sep = 0.013 * (b - a)                    # separación mínima entre etiquetas
    pos = [l for _, l in sel]
    for _ in range(100):                     # empuja las que se solapan
        cambio = False
        for i in range(1, len(pos)):
            if pos[i] - pos[i - 1] < sep:
                d = (sep - (pos[i] - pos[i - 1])) / 2
                pos[i - 1] -= d; pos[i] += d
                cambio = True
        if not cambio:
            break
    for (nombre, l), p in zip(sel, pos):
        ax.vlines(l, 0.2, 1.10, color="tab:blue", lw=0.5, ls=":")
        ax.plot([l, p], [1.10, 1.16], color="tab:blue", lw=0.5)
        ax.text(p, 1.17, f"{nombre} {l:.0f}", rotation=90, fontsize=6.5,
                ha="center", va="bottom", color="tab:blue")


# ----------------------------------------------------------------- principal
os.makedirs("figuras", exist_ok=True)

for fichero, metodo in ESTRELLAS.items():
    nombre = fichero.replace(".dat", "")
    lam, flujo = leer(fichero)
    cont = continuo_polinomio(lam, flujo) if metodo == "polinomio" \
        else continuo_envolvente(lam, flujo)
    fnorm = flujo / cont

    with PdfPages(f"figuras/{nombre}.pdf") as pdf:
        for a, b in REGIONES:
            fig, ax = plt.subplots(figsize=(13, 6))
            s = (lam >= a) & (lam <= b)
            ax.plot(lam[s], fnorm[s], "k", lw=0.7)
            ax.axhline(1, color="gray", lw=0.5, ls="--")
            ax.set_xlim(a, b); ax.set_ylim(0.2, 1.6)
            ax.set_xlabel("λ (Å)"); ax.set_ylabel("Flujo normalizado")
            ax.set_title(f"{nombre}   {a}–{b} Å")
            poner_lineas(ax, a, b)
            fig.tight_layout()
            pdf.savefig(fig); plt.close(fig)

    print(f"figuras/{nombre}.pdf")