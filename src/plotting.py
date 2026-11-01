"""Gráficas: anotación de líneas/bandas y exportación a PDF."""

from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")  # solo se escriben PDFs; no hace falta ventana
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

Region = Tuple[float, float]
Line = Tuple[str, float]
Band = Tuple[str, Tuple[float, float]]


def resolve_label_overlaps(
    wavelengths: List[float],
    min_separation: float,
    max_iter: int = 100,
) -> List[float]:
    """Relajación repulsiva 1D para que las etiquetas contiguas no se solapen."""
    positions = list(wavelengths)
    for _ in range(max_iter):
        shifted = False
        for i in range(1, len(positions)):
            gap = positions[i] - positions[i - 1]
            if gap < min_separation:
                overlap = (min_separation - gap) / 2.0
                positions[i - 1] -= overlap
                positions[i] += overlap
                shifted = True
        if not shifted:
            break
    return positions


def annotate_spectral_lines(
    ax: plt.Axes,
    min_wave: float,
    max_wave: float,
    lines: List[Line],
    bands: Optional[List[Band]] = None,
) -> None:
    """
    Sombrea las bandas en gris y marca las líneas con su etiqueta.
    La coordenada y va en fracción del eje (0 = abajo, 1 = arriba), así que
    funciona igual con flujo normalizado que con flujo bruto.
    """
    transform = ax.get_xaxis_transform()  # x en Å, y en fracción del eje

    if bands:
        for name, (band_min, band_max) in bands:
            if not (max_wave < band_min or min_wave > band_max):
                ax.axvspan(
                    max(min_wave, band_min),
                    min(max_wave, band_max),
                    color="gray",
                    alpha=0.25,
                    zorder=0,
                )
                mid = (band_min + band_max) / 2.0
                if min_wave <= mid <= max_wave:
                    ax.text(
                        mid, 0.71, name,
                        fontsize=7.0, ha="center", va="bottom",
                        color="dimgray", fontweight="bold", transform=transform,
                    )

    visible_lines = [(n, w) for n, w in lines if min_wave < w < max_wave]
    if not visible_lines:
        return

    min_separation = 0.013 * (max_wave - min_wave)
    label_positions = resolve_label_overlaps([w for _, w in visible_lines], min_separation)

    for (name, line_wave), label_wave in zip(visible_lines, label_positions):
        ax.plot([line_wave, line_wave], [0, 0.66], color="tab:blue", lw=0.5, ls=":", transform=transform)
        ax.plot([line_wave, label_wave], [0.66, 0.70], color="tab:blue", lw=0.5, transform=transform)
        ax.text(
            label_wave, 0.71, f"{name} {line_wave:.0f}",
            rotation=90, fontsize=6.5, ha="center", va="bottom",
            color="tab:blue", transform=transform,
        )


Spectrum = Tuple[str, np.ndarray, np.ndarray]  # (nombre, longitud de onda, flujo)

SPECTRUM_STYLES = [
    {"color": "black", "lw": 0.8},
    {"color": "tab:red", "lw": 0.8, "alpha": 0.8},
]


def draw_window(
    ax: plt.Axes,
    spectra: List[Spectrum],
    min_wave: float,
    max_wave: float,
    reference_lines: List[Line],
    reference_bands: Optional[List[Band]] = None,
    flux_label: str = "Flujo",
) -> bool:
    """
    Dibuja uno o dos espectros en una ventana, con líneas y bandas de referencia.
    El eje y se ajusta a los datos de la ventana, con margen arriba para las
    etiquetas. Devuelve False si no hay datos en la ventana.
    """
    pieces = []
    for (name, wavelength, flux), style in zip(spectra, SPECTRUM_STYLES):
        mask = (wavelength >= min_wave) & (wavelength <= max_wave)
        if mask.any():
            ax.plot(wavelength[mask], flux[mask], label=name, **style)
            pieces.append(flux[mask])
    if not pieces:
        return False

    y = np.concatenate(pieces)
    lo, hi = float(np.min(y)), float(np.max(y))
    span = (hi - lo) or 1.0
    ax.set_ylim(0, 1.5)
    ax.set_xlim(min_wave, max_wave)
    ax.set_xlabel("λ (Å)")
    ax.set_ylabel(flux_label)
    ax.set_title(f"{min_wave:.0f}–{max_wave:.0f} Å")
    ax.legend(loc="lower left", fontsize=9)
    annotate_spectral_lines(ax, min_wave, max_wave, reference_lines, reference_bands)
    return True


def export_pdf(
    spectra: List[Spectrum],
    windows: List[Region],
    output_pdf_path: Path,
    reference_lines: List[Line],
    reference_bands: Optional[List[Band]] = None,
    flux_label: str = "Flujo",
) -> int:
    """PDF con una ventana por página. Devuelve el número de páginas escritas."""
    pages = 0
    with PdfPages(output_pdf_path) as pdf:
        for min_wave, max_wave in windows:
            fig, ax = plt.subplots(figsize=(13, 6))
            if draw_window(ax, spectra, min_wave, max_wave,
                           reference_lines, reference_bands, flux_label):
                fig.tight_layout()
                pdf.savefig(fig)
                pages += 1
            plt.close(fig)
    return pages


SAVE_FORMATS = (".pdf", ".png", ".jpg", ".svg")


def export_file(
    spectra: List[Spectrum],
    windows: List[Region],
    output_path: Path,
    reference_lines: List[Line],
    reference_bands: Optional[List[Band]] = None,
    flux_label: str = "Flujo",
    dpi: int = 200,
) -> List[Path]:
    """
    Guarda según la extensión de `output_path` (.pdf, .png, .jpg o .svg).
    PDF: un solo archivo con una página por ventana. Imágenes: un archivo por
    ventana (si hay más de una, se añade «_MIN-MAX» al nombre).
    Devuelve las rutas escritas.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() == ".pdf":
        pages = export_pdf(spectra, windows, output_path, reference_lines, reference_bands, flux_label)
        return [output_path] if pages else []

    written: List[Path] = []
    for min_wave, max_wave in windows:
        if len(windows) == 1:
            path = output_path
        else:
            path = output_path.with_name(
                f"{output_path.stem}_{min_wave:.0f}-{max_wave:.0f}{output_path.suffix}")
        fig, ax = plt.subplots(figsize=(13, 6))
        if draw_window(ax, spectra, min_wave, max_wave, reference_lines, reference_bands, flux_label):
            fig.tight_layout()
            fig.savefig(path, dpi=dpi)
            written.append(path)
        plt.close(fig)
    return written
