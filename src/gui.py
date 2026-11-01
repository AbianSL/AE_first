"""Interfaz gráfica sencilla: elegir espectros, elegir región, ver y guardar PDF."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .models import (
    DATA_DIR,
    FIGURES_DIR,
    NAMED_REGIONS,
    SPECTRAL_BANDS,
    SPECTRAL_LINES,
    SPECTRAL_REGIONS,
    TARGET_STARS,
)
from .plotting import SAVE_FORMATS, Spectrum, draw_window, export_file
from .spectra import METHODS, load_spectrum, normalize_spectrum

AUTO = "automático"

# Solo los espectros "EstrellaProblema…" vienen sin normalizar; el resto ya lo está.
UNNORMALIZED_PREFIX = "EstrellaProblema"
TARGET_METHODS = {path.name: method for path, method in TARGET_STARS.items()}


def needs_normalization(path: Path) -> bool:
    return path.name in TARGET_METHODS or path.stem.startswith(UNNORMALIZED_PREFIX)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Comparador de espectros")
        self.geometry("1250x720")

        self.paths: List[Optional[Path]] = [None, None]
        self.method = tk.StringVar(value=AUTO)
        self.min_var = tk.StringVar()
        self.max_var = tk.StringVar()
        self.status = tk.StringVar(value="Elige un espectro para empezar.")
        self.save_format = tk.StringVar(value="PDF")

        # Lista de regiones: primero las de zoom con nombre, luego las generales.
        self.regions: Dict[str, Tuple[float, float]] = dict(NAMED_REGIONS)
        for lo, hi in SPECTRAL_REGIONS:
            self.regions[f"{lo:.0f}–{hi:.0f} Å"] = (lo, hi)

        # Rangos añadidos por el usuario en esta sesión. No se guardan en disco:
        # al reiniciar solo quedan las regiones definidas en models.py.
        self.custom: set = set()

        self._raw: Dict[Path, tuple] = {}          # path -> (λ, flujo)
        self._normalized: Dict[tuple, object] = {}  # (path, método) -> flujo normalizado

        self._build_controls()
        self._build_plot()
        for key in ("<Escape>", "<Control-c>", "<Control-C>", "<Control-d>", "<Control-D>"):
            self.bind_all(key, self._on_close_key)
        self._preload_targets()
        self.region_list.selection_set(0)
        self._on_region_selected()

    # ------------------------------------------------------------------ UI
    def _build_controls(self) -> None:
        panel = ttk.Frame(self, padding=10)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        # 1. Espectros
        box = ttk.LabelFrame(panel, text="1. Espectros", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        self.file_labels: List[ttk.Label] = []
        for i, title in enumerate(("Espectro 1:", "Espectro 2 (opcional):")):
            ttk.Label(box, text=title).pack(anchor=tk.W)
            row = ttk.Frame(box)
            row.pack(fill=tk.X, pady=(0, 6))
            label = ttk.Label(row, text="(ninguno)", width=24, foreground="gray")
            label.pack(side=tk.LEFT)
            ttk.Button(row, text="Elegir…", command=lambda i=i: self._choose_file(i)).pack(side=tk.LEFT)
            if i == 1:
                ttk.Button(row, text="Quitar", command=lambda i=i: self._set_path(i, None)).pack(side=tk.LEFT, padx=3)
            self.file_labels.append(label)

        # 2. Normalización
        box = ttk.LabelFrame(panel, text="2. Normalización", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(box, text="Las «EstrellaProblema» se normalizan solas;\nel resto ya está normalizado.",
                  foreground="dimgray").pack(anchor=tk.W)
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row, text="Método:").pack(side=tk.LEFT)
        combo = ttk.Combobox(row, textvariable=self.method, state="readonly",
                             values=(AUTO,) + tuple(METHODS), width=14)
        combo.pack(side=tk.LEFT, padx=5)
        combo.bind("<<ComboboxSelected>>", lambda _: self.redraw())

        # 3. Región
        box = ttk.LabelFrame(panel, text="3. Región a ver", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        self.region_list = tk.Listbox(box, height=11, exportselection=False, width=30)
        self.region_list.pack(fill=tk.X)
        for name in self.regions:
            self.region_list.insert(tk.END, name)
        self.region_list.bind("<<ListboxSelect>>", lambda _: self._on_region_selected())

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(row, text="Rango propio (Å):").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.min_var, width=7).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(row, text="–").pack(side=tk.LEFT)
        entry_max = ttk.Entry(row, textvariable=self.max_var, width=7)
        entry_max.pack(side=tk.LEFT, padx=2)
        entry_max.bind("<Return>", lambda _: self._on_custom_range())
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(row, text="Ver rango", command=self._on_custom_range).pack(side=tk.LEFT)
        ttk.Button(row, text="Añadir a la lista", command=self._add_region).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Quitar", command=self._remove_region).pack(side=tk.LEFT)

        # 4. Guardar
        box = ttk.LabelFrame(panel, text="4. Guardar", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row, text="Formato:").pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.save_format, state="readonly", width=8,
                     values=[f.lstrip(".").upper() for f in SAVE_FORMATS]).pack(side=tk.LEFT, padx=5)
        ttk.Button(box, text="Esta vista", command=self.save_current).pack(fill=tk.X)
        ttk.Button(box, text="Todas las regiones de la lista",
                   command=self.save_all).pack(fill=tk.X, pady=(4, 0))
        ttk.Label(box, text="PDF: un archivo con una página por región.\n"
                            "PNG/JPG/SVG: un archivo por región, en la carpeta que elijas.",
                  foreground="dimgray").pack(anchor=tk.W, pady=(4, 0))

        ttk.Label(panel, textvariable=self.status, wraplength=290, foreground="dimgray").pack(anchor=tk.W)
        ttk.Button(panel, text="Cerrar", command=self.close).pack(side=tk.BOTTOM, fill=tk.X)

    def _build_plot(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(9, 6))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        NavigationToolbar2Tk(self.canvas, frame)  # zoom, desplazar, guardar imagen
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close_key(self, event: tk.Event) -> None:
        """Esc, Ctrl+C o Ctrl+D: pregunta y, si se confirma, cierra."""
        # En un campo de texto, Ctrl+C sigue siendo «copiar».
        if event.keysym.lower() == "c" and isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        if messagebox.askyesno("Cerrar", "¿Quieres cerrar el programa?", parent=self):
            self.close()

    def close(self) -> None:
        """Cierra la ventana y termina el programa (también libera la figura)."""
        self.quit()
        self.destroy()

    # -------------------------------------------------------------- Ficheros
    def _preload_targets(self) -> None:
        """Si existen los archivos de TARGET_STARS, los deja ya cargados."""
        existing = [p for p in TARGET_STARS if p.exists()]  # (ver models.py)
        for i, path in enumerate(existing[:2]):
            self._set_path(i, path, redraw=False)

    def _choose_file(self, slot: int) -> None:
        path = filedialog.askopenfilename(
            title="Elegir espectro",
            initialdir=DATA_DIR if DATA_DIR.exists() else Path.cwd(),
            filetypes=[("Espectros", "*.dat *.txt *.csv"), ("Todos", "*.*")],
        )
        if path:
            self._set_path(slot, Path(path))

    def _set_path(self, slot: int, path: Optional[Path], redraw: bool = True) -> None:
        self.paths[slot] = path
        label = self.file_labels[slot]
        label.config(text=path.name if path else "(ninguno)",
                     foreground="black" if path else "gray")
        if redraw:
            self.redraw()

    # ---------------------------------------------------------------- Datos
    def _method_for(self, path: Path) -> str:
        chosen = self.method.get()
        return TARGET_METHODS.get(path.name, "polynomial") if chosen == AUTO else chosen

    def _spectra(self) -> List[Spectrum]:
        spectra: List[Spectrum] = []
        for path in self.paths:
            if path is None:
                continue
            if path not in self._raw:
                self._raw[path] = load_spectrum(path)
            wavelength, flux = self._raw[path]
            if needs_normalization(path):
                key = (path, self._method_for(path))
                if key not in self._normalized:
                    self.status.set(f"Normalizando {path.stem}…")
                    self.update_idletasks()
                    self._normalized[key] = normalize_spectrum(wavelength, flux, key[1])[1]
                flux = self._normalized[key]
            spectra.append((path.stem, wavelength, flux))
        return spectra

    def _flux_label(self) -> str:
        return "Flujo normalizado"

    # --------------------------------------------------------------- Región
    def _on_region_selected(self) -> None:
        selection = self.region_list.curselection()
        if not selection:
            return
        lo, hi = self.regions[self.region_list.get(selection[0])]
        self.min_var.set(f"{lo:.0f}")
        self.max_var.set(f"{hi:.0f}")
        self.redraw()

    def _on_custom_range(self) -> None:
        self.region_list.selection_clear(0, tk.END)
        self.redraw()

    def _add_region(self) -> None:
        window = self._current_window()
        if window is None:
            return
        name = f"{window[0]:.0f}–{window[1]:.0f} Å"
        if name not in self.regions:
            self.regions[name] = window
            self.custom.add(name)
            self.region_list.insert(tk.END, name)
        index = list(self.regions).index(name)
        self.region_list.selection_clear(0, tk.END)
        self.region_list.selection_set(index)
        self.region_list.see(index)
        self.redraw()
        self.status.set(f"«{name}» añadida a la lista (solo en esta sesión).")

    def _remove_region(self) -> None:
        selection = self.region_list.curselection()
        if not selection:
            self.status.set("Selecciona en la lista el rango que quieres quitar.")
            return
        name = self.region_list.get(selection[0])
        if name not in self.custom:
            self.status.set("Solo se pueden quitar los rangos que has añadido tú.")
            return
        self.region_list.delete(selection[0])
        del self.regions[name]
        self.custom.discard(name)
        self.status.set(f"«{name}» quitada de la lista.")

    def _current_window(self) -> Optional[Tuple[float, float]]:
        try:
            lo, hi = float(self.min_var.get()), float(self.max_var.get())
        except ValueError:
            self.status.set("El rango debe ser dos números, p. ej. 4030 y 4120.")
            return None
        if lo >= hi:
            self.status.set("El mínimo debe ser menor que el máximo.")
            return None
        return lo, hi

    # --------------------------------------------------------------- Dibujo
    def redraw(self) -> None:
        self.ax.clear()
        window = self._current_window()
        try:
            spectra = self._spectra()
        except Exception as error:  # archivo ilegible, normalización fallida…
            messagebox.showerror("Error", f"No se pudo procesar el espectro:\n{error}")
            self.status.set("Error al procesar el espectro.")
            return

        if window is None:
            pass
        elif not spectra:
            self.ax.text(0.5, 0.5, "Elige un espectro (botón «Elegir…»)",
                         ha="center", va="center", transform=self.ax.transAxes, color="gray")
            self.status.set("Elige un espectro para empezar.")
        elif draw_window(self.ax, spectra, *window, SPECTRAL_LINES, SPECTRAL_BANDS, self._flux_label()):
            self.status.set("Listo. Usa la barra de abajo para hacer zoom.")
        else:
            self.ax.text(0.5, 0.5, "Sin datos en esta región", ha="center", va="center",
                         transform=self.ax.transAxes, color="gray")
            self.status.set("Los espectros no tienen datos en esa región.")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    # --------------------------------------------------------------- Guardar
    def _base_name(self) -> str:
        names = [p.stem for p in self.paths if p]
        return "_vs_".join(names) if names else "espectro"

    def _write(self, windows: List[Tuple[float, float]], tag: str, many: bool) -> None:
        try:
            spectra = self._spectra()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo procesar el espectro:\n{error}")
            return
        if not spectra:
            messagebox.showinfo("Guardar", "Primero elige un espectro.")
            return

        ext = f".{self.save_format.get().lower()}"
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        if many and ext != ".pdf":
            # Muchas imágenes: se elige una carpeta y dentro va un archivo por región.
            folder = filedialog.askdirectory(title="Elige la carpeta donde guardar las imágenes",
                                             initialdir=FIGURES_DIR, mustexist=False)
            if not folder:
                return
            path = Path(folder) / f"{self._base_name()}{ext}"
        else:
            chosen = filedialog.asksaveasfilename(
                title=f"Guardar como {ext[1:].upper()}", defaultextension=ext,
                filetypes=[(ext[1:].upper(), f"*{ext}")],
                initialdir=FIGURES_DIR, initialfile=f"{self._base_name()}{tag}",
            )
            if not chosen:
                return
            path = Path(chosen)
            if path.suffix.lower() != ext:      # el formato lo manda el selector
                path = path.with_name(path.name + ext)

        written = export_file(spectra, windows, path, SPECTRAL_LINES, SPECTRAL_BANDS, self._flux_label())
        if not written:
            self.status.set("No se guardó nada: no hay datos en esas regiones.")
        elif len(written) == 1:
            self.status.set(f"Guardado: {written[0].name}")
        else:
            self.status.set(f"Guardados {len(written)} archivos en {written[0].parent}")

    def save_current(self) -> None:
        window = self._current_window()
        if window:
            self._write([window], f"_{window[0]:.0f}-{window[1]:.0f}", many=False)

    def save_all(self) -> None:
        self._write(list(self.regions.values()), "", many=True)


def run() -> None:
    App().mainloop()
