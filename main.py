"""
Normalizes target stellar spectra and plots the spectra alongside known spectral lines.
Output: Saved PDF files organized by regions in the output directory.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from numpy.polynomial import legendre as leg
from scipy.interpolate import PchipInterpolator
from src.models import DATA_DIR, FIGURES_DIR, TARGET_STARS, SPECTRAL_REGIONS, SPECTRAL_LINES

# -----------------------------------------------------------------------------
# Data Ingestion
# -----------------------------------------------------------------------------

def load_spectrum(filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Loads and cleans spectral data from a two-column ASCII file.
    
    Returns:
        Tuple of sorted (wavelengths, flux).
    """
    raw_data = np.genfromtxt(filepath, comments="#", invalid_raise=False)
    valid_mask = np.isfinite(raw_data).all(axis=1)
    clean_data = raw_data[valid_mask]
    
    sorted_data = clean_data[np.argsort(clean_data[:, 0])]
    return sorted_data[:, 0], sorted_data[:, 1]


# -----------------------------------------------------------------------------
# Continuum Estimation & Normalization
# -----------------------------------------------------------------------------

def fit_polynomial_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    degree: int = 6,
    max_iter: int = 20,
) -> np.ndarray:
    """
    Iteratively fits a Legendre polynomial continuum while rejecting strong absorption lines.
    """
    # Normalize domain to [-1, 1] for Legendre stability
    scaled_wave = 2.0 * (wavelength - wavelength.min()) / (wavelength.max() - wavelength.min()) - 1.0
    
    # Initial mask excluding prominent broad line cores
    rejection_intervals = [
        (3925, 3985), (4060, 4145), (4300, 4380), (4820, 4900), (6520, 6600)
    ]
    fit_mask = np.ones_like(wavelength, dtype=bool)
    for lower, upper in rejection_intervals:
        fit_mask &= ~((wavelength > lower) & (wavelength < upper))

    continuum = np.empty_like(flux)
    for _ in range(max_iter):
        coeffs = leg.legfit(scaled_wave[fit_mask], flux[fit_mask], degree)
        continuum = leg.legval(scaled_wave, coeffs)
        
        residuals = flux - continuum
        std_residuals = np.std(residuals[fit_mask])
        
        # Asymmetric rejection to avoid absorption troughs while keeping stellar continuum
        updated_mask = fit_mask & (residuals > -1.5 * std_residuals) & (residuals < 3.0 * std_residuals)
        if updated_mask.sum() == fit_mask.sum():
            break
        fit_mask = updated_mask

    return continuum


def fit_envelope_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    bin_width: float = 25.0,
    percentile: float = 95.0,
) -> np.ndarray:
    """
    Estimates pseudo-continuum for crowded/cool spectra via local upper-percentile interpolation.
    """
    anchor_wavelengths: List[float] = []
    anchor_fluxes: List[float] = []

    for bin_start in np.arange(wavelength.min(), wavelength.max(), bin_width):
        bin_mask = (wavelength >= bin_start) & (wavelength < bin_start + bin_width)
        if bin_mask.sum() < 10:
            continue

        threshold = np.percentile(flux[bin_mask], percentile)
        top_flux_mask = bin_mask & (flux >= threshold)
        
        anchor_wavelengths.append(float(np.mean(wavelength[top_flux_mask])))
        anchor_fluxes.append(float(threshold))

    interpolator = PchipInterpolator(anchor_wavelengths, anchor_fluxes)
    return interpolator(wavelength)


def normalize_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    method: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Dispatches continuum fitting method and returns (continuum, normalized_flux).
    """
    if method == "polynomial":
        continuum = fit_polynomial_continuum(wavelength, flux)
    elif method == "envelope":
        continuum = fit_envelope_continuum(wavelength, flux)
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    normalized_flux = flux / continuum
    return continuum, normalized_flux


# -----------------------------------------------------------------------------
# Visualization
# -----------------------------------------------------------------------------

def resolve_label_overlaps(
    wavelengths: List[float],
    min_separation: float,
    max_iter: int = 100,
) -> List[float]:
    """
    Applies iterative 1D repulsive relaxation to prevent adjacent label collisions.
    """
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
    lines: List[Tuple[str, float]],
) -> None:
    """
    Draws vertical markers and collision-free labels for lines in the current region.
    """
    visible_lines = sorted(
        [(name, wave) for name, wave in lines if min_wave < wave < max_wave],
        key=lambda item: item[1]
    )
    if not visible_lines:
        return

    min_separation = 0.013 * (max_wave - min_wave)
    original_waves = [wave for _, wave in visible_lines]
    label_positions = resolve_label_overlaps(original_waves, min_separation)

    for (name, line_wave), label_wave in zip(visible_lines, label_positions):
        # Line marker at the actual line wavelength
        ax.vlines(line_wave, 0.2, 1.10, color="tab:blue", lw=0.5, ls=":")
        # Angled segment guiding to displaced label position
        ax.plot([line_wave, label_wave], [1.10, 1.16], color="tab:blue", lw=0.5)
        # Rotated text annotation
        ax.text(
            label_wave,
            1.17,
            f"{name} {line_wave:.0f}",
            rotation=90,
            fontsize=6.5,
            ha="center",
            va="bottom",
            color="tab:blue",
        )


def export_spectrum_pdf(
    wavelength: np.ndarray,
    normalized_flux: np.ndarray,
    target_name: str,
    output_pdf_path: Path,
    regions: List[Tuple[float, float]],
    reference_lines: List[Tuple[str, float]],
) -> None:
    """
    Generates a multi-page PDF plotting each specified spectral window.
    """
    with PdfPages(output_pdf_path) as pdf:
        for min_wave, max_wave in regions:
            fig, ax = plt.subplots(figsize=(13, 6))
            
            region_mask = (wavelength >= min_wave) & (wavelength <= max_wave)
            ax.plot(wavelength[region_mask], normalized_flux[region_mask], "k", lw=0.7)
            ax.axhline(1.0, color="gray", lw=0.5, ls="--")

            ax.set_xlim(min_wave, max_wave)
            ax.set_ylim(0.2, 1.6)
            ax.set_xlabel("λ (Å)")
            ax.set_ylabel("Normalized Flux")
            ax.set_title(f"{target_name} — {min_wave:.0f}–{max_wave:.0f} Å")

            annotate_spectral_lines(ax, min_wave, max_wave, reference_lines)

            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    for file_path, norm_method in TARGET_STARS.items():
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            continue

        target_name = file_path.stem
        wavelength, raw_flux = load_spectrum(file_path)
        
        _, normalized_flux = normalize_spectrum(wavelength, raw_flux, method=norm_method)

        output_pdf = FIGURES_DIR / f"{target_name}.pdf"
        export_spectrum_pdf(
            wavelength=wavelength,
            normalized_flux=normalized_flux,
            target_name=target_name,
            output_pdf_path=output_pdf,
            regions=SPECTRAL_REGIONS,
            reference_lines=SPECTRAL_LINES,
        )

        print(f"Generated: {output_pdf}")


if __name__ == "__main__":
    main()
