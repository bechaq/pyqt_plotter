# Clean PyQt Plotter

A desktop plotting app built with `PyQt5` and `matplotlib`. It supports 2D line plots, 2D heatmaps, and 3D visualizations including lines, surfaces, and density-style volume views.

## Run locally

1. Install Python 3.11+.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Launch the app:

```powershell
python pyqt_plotter_main.py
```

On Windows, you can also double-click:

- `pyqt_plotter_main.pyw`
- `Launch PyQt Plotter.vbs`
- `Launch PyQt Plotter.cmd`

## What is included

- Startup landing screen with plot-type selection
- 2D line, heatmap, and 3D plotting modes
- Undo/redo
- Autosave and recent projects
- PNG/SVG/PDF export
- Example 3D datasets in the repo root

## Packaging

A PyInstaller build script is included:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_exe.ps1
```

In this repository, the source and launcher files are the reliable path. Depending on the local Windows setup, PyInstaller may still need a clean machine/path setup to finish the standalone `.exe` build.
