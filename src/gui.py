"""Simple graphical interface: pick spectra, pick a region, view and save."""

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
from .spectra import METHODS, load_spectrum, rectify_spectrum

AUTO = "automatic"

# Only the "EstrellaProblema…" spectra come unrectified; the rest already are.
UNRECTIFIED_PREFIX = "EstrellaProblema"
TARGET_METHODS = {path.name: method for path, method in TARGET_STARS.items()}


def needs_rectification(path: Path) -> bool:
    return path.name in TARGET_METHODS or path.stem.startswith(UNRECTIFIED_PREFIX)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Spectrum comparer")
        self.geometry("1250x720")

        self.paths: List[Optional[Path]] = [None, None]
        self.method = tk.StringVar(value=AUTO)
        self.min_var = tk.StringVar()
        self.max_var = tk.StringVar()
        self.status = tk.StringVar(value="Pick a spectrum to start.")
        self.save_format = tk.StringVar(value="PDF")

        # Region list: named zoom windows first, then the general ones.
        self.regions: Dict[str, Tuple[float, float]] = dict(NAMED_REGIONS)
        for lo, hi in SPECTRAL_REGIONS:
            self.regions[f"{lo:.0f}–{hi:.0f} Å"] = (lo, hi)

        # Ranges added by the user in this session. They are not saved to disk:
        # after a restart only the regions defined in models.py remain.
        self.custom: set = set()

        self._raw: Dict[Path, tuple] = {}          # path -> (λ, flux)
        self._rectified: Dict[tuple, object] = {}  # (path, method) -> rectified flux

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

        # 1. Spectra
        box = ttk.LabelFrame(panel, text="1. Spectra", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        self.file_labels: List[ttk.Label] = []
        for i, title in enumerate(("Spectrum 1:", "Spectrum 2 (optional):")):
            ttk.Label(box, text=title).pack(anchor=tk.W)
            row = ttk.Frame(box)
            row.pack(fill=tk.X, pady=(0, 6))
            label = ttk.Label(row, text="(none)", width=24, foreground="gray")
            label.pack(side=tk.LEFT)
            ttk.Button(row, text="Choose…", command=lambda i=i: self._choose_file(i)).pack(side=tk.LEFT)
            if i == 1:
                ttk.Button(row, text="Remove", command=lambda i=i: self._set_path(i, None)).pack(side=tk.LEFT, padx=3)
            self.file_labels.append(label)

        # 2. Rectification
        box = ttk.LabelFrame(panel, text="2. Rectification", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(box, text="The «EstrellaProblema» files are rectified\nautomatically; the rest already are.",
                  foreground="dimgray").pack(anchor=tk.W)
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row, text="Method:").pack(side=tk.LEFT)
        combo = ttk.Combobox(row, textvariable=self.method, state="readonly",
                             values=(AUTO,) + tuple(METHODS), width=14)
        combo.pack(side=tk.LEFT, padx=5)
        combo.bind("<<ComboboxSelected>>", lambda _: self.redraw())

        # 3. Region
        box = ttk.LabelFrame(panel, text="3. Region to view", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        self.region_list = tk.Listbox(box, height=11, exportselection=False, width=30)
        self.region_list.pack(fill=tk.X)
        for name in self.regions:
            self.region_list.insert(tk.END, name)
        self.region_list.bind("<<ListboxSelect>>", lambda _: self._on_region_selected())

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(row, text="Custom range (Å):").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.min_var, width=7).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(row, text="–").pack(side=tk.LEFT)
        entry_max = ttk.Entry(row, textvariable=self.max_var, width=7)
        entry_max.pack(side=tk.LEFT, padx=2)
        entry_max.bind("<Return>", lambda _: self._on_custom_range())
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(row, text="View range", command=self._on_custom_range).pack(side=tk.LEFT)
        ttk.Button(row, text="Add to list", command=self._add_region).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Remove", command=self._remove_region).pack(side=tk.LEFT)

        # 4. Save
        box = ttk.LabelFrame(panel, text="4. Save", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row, text="Format:").pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.save_format, state="readonly", width=8,
                     values=[f.lstrip(".").upper() for f in SAVE_FORMATS]).pack(side=tk.LEFT, padx=5)
        ttk.Button(box, text="This view", command=self.save_current).pack(fill=tk.X)
        ttk.Button(box, text="All regions in the list",
                   command=self.save_all).pack(fill=tk.X, pady=(4, 0))
        ttk.Label(box, text="PDF: one file with one page per region.\n"
                            "PNG/JPG/SVG: one file per region, in the folder you choose.",
                  foreground="dimgray").pack(anchor=tk.W, pady=(4, 0))

        ttk.Label(panel, textvariable=self.status, wraplength=290, foreground="dimgray").pack(anchor=tk.W)
        ttk.Button(panel, text="Close", command=self.close).pack(side=tk.BOTTOM, fill=tk.X)

    def _build_plot(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(9, 6))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        NavigationToolbar2Tk(self.canvas, frame)  # zoom, pan, save image
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close_key(self, event: tk.Event) -> None:
        """Esc, Ctrl+C or Ctrl+D: asks and, if confirmed, closes."""
        # In a text field, Ctrl+C still means "copy".
        if event.keysym.lower() == "c" and isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        if messagebox.askyesno("Close", "Do you want to close the program?", parent=self):
            self.close()

    def close(self) -> None:
        """Closes the window and ends the program."""
        self.quit()
        self.destroy()

    # ---------------------------------------------------------------- Files
    def _preload_targets(self) -> None:
        """If the TARGET_STARS files exist, loads them right away."""
        existing = [p for p in TARGET_STARS if p.exists()]  # (see models.py)
        for i, path in enumerate(existing[:2]):
            self._set_path(i, path, redraw=False)

    def _choose_file(self, slot: int) -> None:
        path = filedialog.askopenfilename(
            title="Choose spectrum",
            initialdir=DATA_DIR if DATA_DIR.exists() else Path.cwd(),
            filetypes=[("Spectra", "*.dat *.txt *.csv"), ("All files", "*.*")],
        )
        if path:
            self._set_path(slot, Path(path))

    def _set_path(self, slot: int, path: Optional[Path], redraw: bool = True) -> None:
        self.paths[slot] = path
        label = self.file_labels[slot]
        label.config(text=path.name if path else "(none)",
                     foreground="black" if path else "gray")
        if redraw:
            self.redraw()

    # ---------------------------------------------------------------- Data
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
            if needs_rectification(path):
                key = (path, self._method_for(path))
                if key not in self._rectified:
                    self.status.set(f"Rectifying {path.stem}…")
                    self.update_idletasks()
                    self._rectified[key] = rectify_spectrum(wavelength, flux, key[1])[1]
                flux = self._rectified[key]
            spectra.append((path.stem, wavelength, flux))
        return spectra

    def _flux_label(self) -> str:
        return "Rectified flux"

    # --------------------------------------------------------------- Region
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
        self.status.set(f"«{name}» added to the list (this session only).")

    def _remove_region(self) -> None:
        selection = self.region_list.curselection()
        if not selection:
            self.status.set("Select in the list the range you want to remove.")
            return
        name = self.region_list.get(selection[0])
        if name not in self.custom:
            self.status.set("Only ranges you added yourself can be removed.")
            return
        self.region_list.delete(selection[0])
        del self.regions[name]
        self.custom.discard(name)
        self.status.set(f"«{name}» removed from the list.")

    def _current_window(self) -> Optional[Tuple[float, float]]:
        try:
            lo, hi = float(self.min_var.get()), float(self.max_var.get())
        except ValueError:
            self.status.set("The range must be two numbers, e.g. 4030 and 4120.")
            return None
        if lo >= hi:
            self.status.set("The minimum must be smaller than the maximum.")
            return None
        return lo, hi

    # --------------------------------------------------------------- Drawing
    def redraw(self) -> None:
        self.ax.clear()
        window = self._current_window()
        try:
            spectra = self._spectra()
        except Exception as error:  # unreadable file, failed rectification…
            messagebox.showerror("Error", f"Could not process the spectrum:\n{error}")
            self.status.set("Error while processing the spectrum.")
            return

        if window is None:
            pass
        elif not spectra:
            self.ax.text(0.5, 0.5, "Pick a spectrum (\"Choose…\" button)",
                         ha="center", va="center", transform=self.ax.transAxes, color="gray")
            self.status.set("Pick a spectrum to start.")
        elif draw_window(self.ax, spectra, *window, SPECTRAL_LINES, SPECTRAL_BANDS, self._flux_label()):
            self.status.set("Ready. Use the toolbar below to zoom.")
        else:
            self.ax.text(0.5, 0.5, "No data in this region", ha="center", va="center",
                         transform=self.ax.transAxes, color="gray")
            self.status.set("The spectra have no data in that region.")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    # ------------------------------------------------------------------ Save
    def _base_name(self) -> str:
        names = [p.stem for p in self.paths if p]
        return "_vs_".join(names) if names else "spectrum"

    def _write(self, windows: List[Tuple[float, float]], tag: str, many: bool) -> None:
        try:
            spectra = self._spectra()
        except Exception as error:
            messagebox.showerror("Error", f"Could not process the spectrum:\n{error}")
            return
        if not spectra:
            messagebox.showinfo("Save", "Pick a spectrum first.")
            return

        ext = f".{self.save_format.get().lower()}"
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        if many and ext != ".pdf":
            # Many images: pick a folder; one file per region goes inside.
            folder = filedialog.askdirectory(title="Choose the folder to save the images in",
                                             initialdir=FIGURES_DIR, mustexist=False)
            if not folder:
                return
            path = Path(folder) / f"{self._base_name()}{ext}"
        else:
            chosen = filedialog.asksaveasfilename(
                title=f"Save as {ext[1:].upper()}", defaultextension=ext,
                filetypes=[(ext[1:].upper(), f"*{ext}")],
                initialdir=FIGURES_DIR, initialfile=f"{self._base_name()}{tag}",
            )
            if not chosen:
                return
            path = Path(chosen)
            if path.suffix.lower() != ext:      # the format selector decides
                path = path.with_name(path.name + ext)

        written = export_file(spectra, windows, path, SPECTRAL_LINES, SPECTRAL_BANDS, self._flux_label())
        if not written:
            self.status.set("Nothing saved: there is no data in those regions.")
        elif len(written) == 1:
            self.status.set(f"Saved: {written[0].name}")
        else:
            self.status.set(f"Saved {len(written)} files in {written[0].parent}")

    def save_current(self) -> None:
        window = self._current_window()
        if window:
            self._write([window], f"_{window[0]:.0f}-{window[1]:.0f}", many=False)

    def save_all(self) -> None:
        self._write(list(self.regions.values()), "", many=True)


def run() -> None:
    App().mainloop()
