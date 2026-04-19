PLOT_MODE_OPTIONS = [
    ("line2d", "2D line plot", "Classic X/Y line plots with optional secondary axes."),
    ("heatmap2d", "2D heatmap", "Color-mapped X/Y/Z plots from scattered point data."),
    ("plot3d", "3D plot", "Three-dimensional line plots using X/Y/Z columns."),
]

PLOT_MODE_LABELS = {mode: label for mode, label, _ in PLOT_MODE_OPTIONS}
PLOT3D_STYLE_OPTIONS = [
    ("line", "Line", "Connected X/Y/Z line curves."),
    ("surface", "Surface", "Triangulated or gridded 3D surfaces."),
    ("volume", "Volume", "Voxel-density volumes derived from 3D point clouds."),
]

PLOT3D_STYLE_LABELS = {style: label for style, label, _ in PLOT3D_STYLE_OPTIONS}


def friendly_3d_style(style: str) -> str:
    return PLOT3D_STYLE_LABELS.get(style, PLOT3D_STYLE_LABELS["line"])


def plot3d_style_supports_direct_color(style: str) -> bool:
    return style == "line"


def plot3d_style_uses_colormap(style: str) -> bool:
    return style in {"surface", "volume"}


def plot_mode_supports_render_style(mode: str) -> bool:
    return mode == "plot3d"


def render_style_uses_colormap(mode: str, style: str | None) -> bool:
    if mode == "heatmap2d":
        return True
    if mode != "plot3d":
        return False
    return style in {"surface", "volume"}


def plot_mode_supports_z_ticks(mode: str) -> bool:
    return mode == "plot3d"


def friendly_plot_mode(mode: str) -> str:
    return PLOT_MODE_LABELS.get(mode, PLOT_MODE_LABELS["line2d"])


def plot_mode_requires_z(mode: str) -> bool:
    return mode in {"heatmap2d", "plot3d"}


def plot_mode_supports_secondary_axis(mode: str) -> bool:
    return mode == "line2d"


def plot_mode_supports_direct_color(mode: str) -> bool:
    return mode != "heatmap2d"
