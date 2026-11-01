"""Lectura de espectros y normalización del continuo."""

from pathlib import Path
from typing import List, Tuple

import numpy as np
from numpy.polynomial import Legendre
from scipy.interpolate import PchipInterpolator

# Parámetros de normalización (antes iban como un `11` posicional).
POLYNOMIAL_DEGREE = 11
ENVELOPE_BIN_WIDTH = 11.0  # Å

METHODS = ("polynomial", "envelope")


def load_spectrum(filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Carga un .dat de dos columnas (λ en Å, flujo); devuelve (λ, flujo) ordenados."""
    raw_data = np.genfromtxt(filepath, comments="#", invalid_raise=False)
    valid_mask = np.isfinite(raw_data).all(axis=1)
    clean_data = raw_data[valid_mask]

    sorted_data = clean_data[np.argsort(clean_data[:, 0])]
    return sorted_data[:, 0], sorted_data[:, 1]


def fit_polynomial_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    degree: int = 6,
    max_iter: int = 20,
) -> np.ndarray:
    """Ajusta iterativamente un polinomio de Legendre rechazando líneas de absorción."""
    rejection_intervals = [(3925, 3985), (4060, 4145), (4300, 4380), (4820, 4900), (6520, 6600)]

    mask = ~np.bitwise_or.reduce([(wavelength > lo) & (wavelength < hi) for lo, hi in rejection_intervals])

    for _ in range(max_iter):
        poly = Legendre.fit(wavelength[mask], flux[mask], deg=degree)
        residuals = flux - poly(wavelength)
        std = np.std(residuals[mask])

        new_mask = mask & (residuals > -1.5 * std) & (residuals < 3.0 * std)
        if np.array_equal(new_mask, mask):
            break
        mask = new_mask

    return poly(wavelength)


def fit_envelope_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    bin_width: float = 25.0,
    percentile: float = 95.0,
) -> np.ndarray:
    """Pseudo-continuo para espectros fríos/saturados: percentil alto por bin + interpolación."""
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
    """Devuelve (continuo, flujo_normalizado) según el método elegido."""
    if method == "polynomial":
        continuum = fit_polynomial_continuum(wavelength, flux, degree=POLYNOMIAL_DEGREE)
    elif method == "envelope":
        continuum = fit_envelope_continuum(wavelength, flux, bin_width=ENVELOPE_BIN_WIDTH)
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    return continuum, flux / continuum
