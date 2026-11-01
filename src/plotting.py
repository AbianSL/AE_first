"""Plots: line/band annotation and export to PDF, PNG, JPG and SVG."""

from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")  # files are written without opening a window
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
    """1D repulsive relaxation so adjacent labels do not overlap."""
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
    Shades the bands in gray and marks the lines with their labels.
    The y coordinate is an axes fraction (0 = bottom, 1 = top), so it works
    the same for normalized and raw flux.
    """
    transform = ax.get_xaxis_transform()  # x in Å, y as axes fraction

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


Spectrum = Tuple[str, np.ndarray, np.ndarray]  # (name, wavelength, flux)

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
    flux_label: str = "Flux",
) -> bool:
    """
    Draws one or two spectra in a window, with reference lines and bands.
    The y axis fits the data in the window, with headroom on top for the
    labels. Returns False if there is no data in the window.
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
    ax.set_ylim(lo - 0.05 * span, hi + 0.6 * span)
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
    flux_label: str = "Flux",
) -> int:
    """PDF with one window per page. Returns the number of pages written."""
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
    flux_label: str = "Flux",
    dpi: int = 200,
) -> List[Path]:
    """
    Saves according to the extension of `output_path` (.pdf, .png, .jpg or .svg).
    PDF: a single file with one page per window. Images: one file per window
    (if there is more than one, "_MIN-MAX" is added to the file name).
    Returns the paths written.
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
