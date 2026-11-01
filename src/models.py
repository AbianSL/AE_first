from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path("data")
FIGURES_DIR = Path("figuras")

TARGET_STARS: Dict[Path, str] = {
    DATA_DIR / "EstrellaProblema1.dat": "polynomial",
    DATA_DIR / "EstrellaProblema2.dat": "polynomial",
}

NAMED_REGIONS: Dict[str, Tuple[float, float]] = {
    "Fe I 4046 + Hδ 4102": (4020.0, 4120.0),  # Mn I 4030/4034, Fe I 4046, Hδ 4102
    "Banda G + Hγ 4340": (4280.0, 4360.0),
}


SPECTRAL_REGIONS: List[Tuple[float, float]] = [
    (3900.0, 4100.0),
    (4100.0, 4300.0),
    (4300.0, 4500.0),
    (4500.0, 4700.0),
    (4700.0, 5000.0),
    (5000.0, 6000.0),
    (6000.0, 6800.0),
]

RAW_SPECTRAL_LINES: Dict[str, List[float]] = {
    # Regions
    "Banda G (CH)": [(4295.0, 4315.0)],
    "CN": [4215.0],
    "MgH": [4780.0, 5200.0],
    "TiO": [4584.0, 4623.0, 4759.0, 4804.0, 4954.0],
    # Lines
    "Hε": [3970.07],
    "Hδ": [4101.73],
    "Hγ": [4340.47],
    "Hβ": [4861.35],
    "He I": [4026.19, 4120.81, 4143.76, 4387.93, 4471.48, 4713.37, 4921.93],
    "He II": [4199.87, 4541.59, 4685.68],
    "Ca II K": [3933.663],
    "Ca II H": [3968.49],
    "Ca I": [4226.0],
    "N IV": [4057.759, 4513.3, 4607.30],
    "N III": [4516.12, 4519.41, 4530.84, 4534.57, 4634.12, 4640.64, 4641.85],
    "N II": [4237.07, 4241.55, 4242.424],
    "N V": [4603.73],
    "O II": [
        4069.636, 4072.164, 4075.868, 4132.00, 4185.00, 4189.00, 4277.4265,
        4317.139, 4319.631, 4366.00, 4414.90, 4416.97, 4452.00, 4638.00,
        4649.1348, 4650.8384, 4661.00, 4676.00
    ],
    "Si IV": [4088.863, 4116.104, 4212.00, 4654.00],
    "Si II": [4128.054, 4130.894],
    "Si III": [4539.00, 4552.654, 4554.00, 4567.872, 4574.777],
    "C III": [4153.685, 4155.80, 4186.900, 4640.03, 4647.419, 4650.246, 4651.016, 4651.473, 4652.049, 4659.06],
    "C II": [4267.01],
    "Mg II": [4481.13],
    "Fe II": [4416.8, 4922.1],
    "Fe I": [4383.0, 4046.0],
    "Li I": [6708.0],
    "Mn I": [4030.0, 4034.0],
}

SPECTRAL_BANDS: List[Tuple[str, Tuple[float, float]]] = []
raw_lines: List[Tuple[str, float]] = []

for name, values in RAW_SPECTRAL_LINES.items():
    for item in values:
        if isinstance(item, tuple):
            SPECTRAL_BANDS.append((name, item))
        else:
            raw_lines.append((name, float(item)))

SPECTRAL_LINES: List[Tuple[str, float]] = sorted(raw_lines, key=lambda x: x[1])

