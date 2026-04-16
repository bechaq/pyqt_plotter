from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUTPUT = Path("output/pdf/pyqt_plotter_app_summary.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


sections = [
    (
        "What It Is",
        [
            "A PyQt5 desktop plotting app that loads local numeric data files and renders interactive Matplotlib plots.",
            "The codebase centers on a MainWindow UI, an AppController state layer, and a PlotCanvas that draws configured curves and subplots."
        ],
    ),
    (
        "Who It's For",
        [
            "Primary persona: a desktop user who needs to inspect or compare tabular numeric data by building custom 2D plots without writing plotting code."
        ],
    ),
    (
        "What It Does",
        [
            "Loads local text-like data files and auto-detects delimiter/header structure before parsing numeric columns.",
            "Lets users add multiple curves, choose X/Y columns, rename curves, and assign them to primary or secondary Y axes.",
            "Supports subplot layouts, subplot assignment, and shared X/Y axis behavior.",
            "Applies plot styling controls including aspect ratio, color palettes, curve colors, tick density, legends, major grid, minor ticks, and minor grid.",
            "Persists full plot state as a JSON-based project file with data-file paths, plot config, and curve definitions.",
            "Reopens saved plot projects and skips curves whose referenced source files are missing.",
            "Includes Matplotlib navigation/customize tooling and syncs edited labels or line styling back into app state."
        ],
    ),
    (
        "How It Works",
        [
            "Entry point: pyqt_plotter_main.py creates QApplication and MainWindow.",
            "UI layer: MainWindow builds the control panel, file/curve/project actions, subplot controls, and Matplotlib toolbar.",
            "Controller layer: AppController stores loaded DataFile objects, Curve definitions, and PlotConfig, then calls PlotCanvas.draw_curves().",
            "Data layer: DataFile.load_data_file() reads local files, removes comments, detects delimiter, finds the first fully numeric row, and returns NumPy-backed columns.",
            "Rendering layer: PlotCanvas creates/reuses Matplotlib subplots, draws each curve, applies per-subplot/global config, and renders inside Qt.",
            "Persistence: save_project/load_project serialize app state to JSON (.pproj example found); external storage/services: Not found in repo."
        ],
    ),
    (
        "How To Run",
        [
            "1. Use Python with the imported runtime libraries available: PyQt5, matplotlib, and numpy. Exact install command: Not found in repo.",
            "2. From the repo root, run: python pyqt_plotter_main.py",
            "3. In the app, add a data file, configure curves/settings, and optionally save a plot project."
        ],
    ),
]


fig = plt.figure(figsize=(8.27, 11.69))
fig.patch.set_facecolor("#f7f3ea")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()

# Header band
ax.add_patch(plt.Rectangle((0.06, 0.92), 0.88, 0.055, color="#1f3a5f", transform=ax.transAxes))
ax.text(
    0.08,
    0.947,
    "PyQt Plotter",
    fontsize=24,
    fontweight="bold",
    color="white",
    va="center",
    ha="left",
    transform=ax.transAxes,
)
ax.text(
    0.94,
    0.947,
    "Repo Summary",
    fontsize=11,
    color="#d8e2f0",
    va="center",
    ha="right",
    transform=ax.transAxes,
)

y = 0.885
section_gap = 0.012
line_gap = 0.022
bullet_gap = 0.026

for title, items in sections:
    ax.text(
        0.08,
        y,
        title.upper(),
        fontsize=10,
        fontweight="bold",
        color="#1f3a5f",
        va="top",
        ha="left",
        transform=ax.transAxes,
    )
    y -= line_gap
    for item in items:
        if item[:2].isdigit() and item[1] == ".":
            text = item
        else:
            text = f"- {item}"
        ax.text(
            0.10,
            y,
            text,
            fontsize=10,
            color="#1f1f1f",
            va="top",
            ha="left",
            wrap=True,
            transform=ax.transAxes,
        )
        y -= bullet_gap
    y -= section_gap

ax.text(
    0.08,
    0.04,
    "Evidence basis: entrypoint, UI, controller, canvas, data parser, config, curve model, and sample .pproj files in repo.",
    fontsize=8.5,
    color="#4c4c4c",
    va="bottom",
    ha="left",
    transform=ax.transAxes,
)

fig.savefig(OUTPUT, format="pdf")
print(OUTPUT.resolve())
