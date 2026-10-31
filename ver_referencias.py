"""
Atlas de los espectros de referencia (Melchiors/HERMES, R~8000).
Dibuja todas las referencias ordenadas por tipo espectral, enanas y
supergigantes por separado, en varias regiones del espectro.

Uso:  python3 ver_referencias.py
"""

import os
import re
import glob
import numpy as np
import matplotlib.pyplot as plt

DIR_REF = "EstrellasEjemplo/EstrellasEjemplo"
DIR_FIG = "figuras/atlas"
SEPARACION = 0.6    # desplazamiento vertical entre espectros

REGIONES = [(3900, 4500), (4500, 5000), (5000, 6000), (6000, 6800)]

LINEAS = {
    "Ca II K": 3933.7, "Hε+Ca II H": 3970.1, "He I 4026": 4026.2,
    "Hδ": 4101.7, "Si II": 4129.5, "He II 4200": 4199.8, "Ca I 4227": 4226.7,
    "G": 4300.0, "Hγ": 4340.5, "He I 4471": 4471.5, "Mg II 4481": 4481.1,
    "He II 4542": 4541.6, "Si III": 4552.6, "He II 4686": 4685.7,
    "Hβ": 4861.3, "He I 4922": 4921.9, "TiO": 4954.6, "Mg I b": 5183.6,
    "He II 5412": 5411.5, "He I 5876": 5875.6, "Na I D": 5892.9,
    "TiO ": 6158.7, "Hα": 6562.8, "He I 6678": 6678.2,
}


def leer(ruta):
    d = np.genfromtxt(ruta, comments="#", invalid_raise=False)
    d = d[np.isfinite(d).all(axis=1)]
    return d[:, 0], d[:, 1]


def tipo_espectral(fichero):
    """Saca p.ej. ('B5', 'I') de 'HD58350_B5I_Melchiors608540.txt'."""
    m = re.search(r"_([OBAFGKM]\d(?:\.\d)?)(Iab|Ia|Ib|III|II|IV|V|I)?_",
                  os.path.basename(fichero))
    return (m.group(1), m.group(2) or "") if m else (None, None)


def clave_orden(tipo):
    return ("OBAFGKM".index(tipo[0]), float(tipo[1:]))


# --- Leer y clasificar las referencias ---------------------------------------
refs = []
for f in glob.glob(os.path.join(DIR_REF, "*")):
    tipo, lum = tipo_espectral(f)
    if tipo is None:          # p.ej. el PDF que venía en el zip
        continue
    lam, flujo = leer(f)
    refs.append({"tipo": tipo, "lum": lum, "lam": lam, "flujo": flujo,
                 "etiqueta": os.path.basename(f).split("_Melchiors")[0]})

enanas = sorted([r for r in refs if r["lum"] in ("V", "IV")],
                key=lambda r: clave_orden(r["tipo"]))
supergig = sorted([r for r in refs if r["lum"] not in ("V", "IV")],
                  key=lambda r: clave_orden(r["tipo"]))
print(f"{len(enanas)} enanas y {len(supergig)} supergigantes/gigantes")

# --- Figuras -------------------------------------------------------------------
os.makedirs(DIR_FIG, exist_ok=True)

for grupo, lista in [("enanas", enanas), ("supergigantes", supergig)]:
    if not lista:
        continue
    for a, b in REGIONES:
        fig, ax = plt.subplots(figsize=(12, 1.5 + 0.55 * len(lista)))
        for i, r in enumerate(lista):
            s = (r["lam"] >= a) & (r["lam"] <= b)
            off = -SEPARACION * i
            ax.plot(r["lam"][s], r["flujo"][s] + off, "k", lw=0.5)
            ax.text(b + 5, 1 + off, r["etiqueta"], fontsize=7, va="center")
        for nombre, l0 in LINEAS.items():
            if a < l0 < b:
                ax.axvline(l0, color="tab:blue", lw=0.5, ls=":", alpha=0.6)
                ax.text(l0, 1.15, nombre.strip(), rotation=90, fontsize=7,
                        ha="center", va="bottom", color="tab:blue")
        ax.set_xlim(a, b + 0.22 * (b - a))
        ax.set_yticks([])
        ax.set_xlabel("λ (Å)")
        ax.set_title(f"Referencias – {grupo} – {a}–{b} Å", pad=40)
        fig.tight_layout()
        fig.savefig(os.path.join(DIR_FIG, f"atlas_{grupo}_{a}-{b}.pdf"))
        plt.close(fig)

print(f"Atlas guardado en ./{DIR_FIG}/")
