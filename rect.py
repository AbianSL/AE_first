"""
Rektifiziert die beiden Problemspektren und speichert sie als .dat.
Aufruf:  python3 rect.py
Ergebnis: EstrellaProblema1_rect.dat und EstrellaProblema2_rect.dat
          (zwei Spalten: Wellenlänge in Å, normierter Fluss)
"""

import numpy as np
from numpy.polynomial import legendre as L
from scipy.interpolate import PchipInterpolator

# Stern -> Methode ("polinomio" für den heißen, "envolvente" für den kühlen)
ESTRELLAS = {"EstrellaProblema1.dat": "polinomio",
             "EstrellaProblema2.dat": "envolvente"}


def leer(ruta):
    d = np.genfromtxt(ruta, comments="#", invalid_raise=False)
    d = d[np.isfinite(d).all(axis=1)]
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1]


def continuo_polinomio(lam, flujo, orden=6):
    """Legendre-Polynom, iterativ angepasst; Punkte in Linien werden verworfen."""
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
    """Pseudo-Kontinuum: hohes Perzentil des Flusses in Abschnitten von 'ancho' Å."""
    xs, ys = [], []
    for a in np.arange(lam.min(), lam.max(), ancho):
        s = (lam >= a) & (lam < a + ancho)
        if s.sum() < 10:
            continue
        nivel = np.percentile(flujo[s], percentil)
        xs.append(np.mean(lam[s][flujo[s] >= nivel]))
        ys.append(nivel)
    return PchipInterpolator(xs, ys)(lam)


for fichero, metodo in ESTRELLAS.items():
    lam, flujo = leer(fichero)
    cont = continuo_polinomio(lam, flujo) if metodo == "polinomio" \
        else continuo_envolvente(lam, flujo)
    salida = fichero.replace(".dat", "_rect.dat")
    np.savetxt(salida, np.column_stack([lam, flujo / cont]), fmt="%.4f",
               header="lambda(A)  flujo_normalizado")
    print(salida)
