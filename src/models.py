from pathlib import Path

DATA_DIR = Path("data")
FIGURES_DIR = Path("figuras")

# Map of stellar spectrum files to their normalization strategy:
# 'polynomial' for hotter stars, 'envelope' for cooler stars
TARGET_STARS: dict[Path, str] = {
    DATA_DIR / "EstrellaProblema1.dat": "polynomial",
    DATA_DIR / "EstrellaProblema2.dat": "envelope",
}

SPECTRAL_REGIONS: list[tuple[float, float]] = [
    (3900.0, 4100.0),
    (4100.0, 4300.0),
    (4300.0, 4500.0),
    (4500.0, 4700.0),
    (4700.0, 5000.0),
    (5000.0, 6000.0),
    (6000.0, 6800.0),
]

SPECTRAL_LINES: list[tuple[str, float]] = [
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
    ("Fe II", 4922.1), ("TiO", 4584.0), ("TiO", 4623.0), ("TiO", 4759.0), ("TiO", 4804.0),
    ("TiO", 4954.0), ("Banda G", 4300.0), ("Li I", 6708.0), ("Mn I", 4030.0),
    ("Mn I", 4034.0), ("Fe II", 4416.8), ("Ca I", 4226.0), ("Fe I", 4383.0),
    ("Fe I", 4143.8),
]
