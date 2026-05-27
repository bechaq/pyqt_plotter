from Color_modules import PLOTLY_PALETTES
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator, LinearLocator
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np


MAX_RENDERED_LINE_POINTS = 50_000


def _stride_indices(length, max_points):
    if max_points <= 1:
        return np.array([0], dtype=int)
    return np.linspace(0, length - 1, max_points, dtype=int)


def _line_downsample_indices(y, max_points):
    length = len(y)
    if length <= max_points:
        return None
    if max_points < 3:
        return _stride_indices(length, max_points)

    bin_count = max(1, (max_points - 2) // 2)
    edges = np.linspace(1, length - 1, bin_count + 1, dtype=int)
    indices = [0]

    for start, end in zip(edges[:-1], edges[1:]):
        if end <= start:
            continue

        segment = y[start:end]
        finite_positions = np.flatnonzero(np.isfinite(segment))
        if finite_positions.size == 0:
            chosen = [start]
        else:
            finite_values = segment[finite_positions]
            min_index = start + finite_positions[int(np.argmin(finite_values))]
            max_index = start + finite_positions[int(np.argmax(finite_values))]
            chosen = sorted((min_index, max_index))

        for index in chosen:
            if index != indices[-1]:
                indices.append(index)

    if indices[-1] != length - 1:
        indices.append(length - 1)

    if len(indices) > max_points:
        return _stride_indices(length, max_points)
    return np.asarray(indices, dtype=int)


def downsample_line_points(x, y, max_points=MAX_RENDERED_LINE_POINTS):
    x = np.asarray(x)
    y = np.asarray(y)
    indices = _line_downsample_indices(y, max_points)
    if indices is None:
        return x, y
    return x[indices], y[indices]


def _same_length(*arrays):
    lengths = [len(array) for array in arrays if array is not None]
    return len(set(lengths)) <= 1


def _apply_major_locator(axis, tick_count):
    if tick_count is None:
        return
    axis.set_major_locator(LinearLocator(numticks=max(1, int(tick_count))))


def _curve_zorder(curve_count, curve_index):
    return max(1, curve_count - curve_index)


def _curve_opacity(curve):
    try:
        value = float(getattr(curve, "opacity", 1.0))
    except (TypeError, ValueError):
        return 1.0
    return max(0.0, min(1.0, value))


def _scaled_alpha(curve, base_alpha=1.0):
    return max(0.0, min(1.0, base_alpha * _curve_opacity(curve)))


class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.axes = []
        self.ax2 = {}          # secondary axes per subplot
        self._colorbars = []
        self._last_layout = None
        self._last_shared_x = None
        self._last_shared_y = None
        self._last_plot_mode = None
        super().__init__(self.fig)
        
    def clear(self, layout, config):
        need_rebuild = (
            self._last_layout != layout
            or self._last_shared_x != config.shared_x
            or self._last_shared_y != config.shared_y
            or self._last_plot_mode != getattr(config, "plot_mode", "line2d")
        )

        self._remove_colorbars()
        self._create_subplots(layout, config.shared_x, config.shared_y, config)
        if need_rebuild:
            self._last_layout = layout
            self._last_shared_x = config.shared_x
            self._last_shared_y = config.shared_y
            self._last_plot_mode = getattr(config, "plot_mode", "line2d")


    def ratio_to_inches(self, ratio):
        Max_x = self.width()/self.fig.get_dpi() 
        Max_y = self.height()/self.fig.get_dpi() 
       

        if ratio[0] > ratio[1]:
            base_size = min(Max_x, ratio[0] * Max_y / ratio[1])
            return base_size, base_size * ratio[1] / ratio[0]
        else:
            base_size = min(Max_y, ratio[1] * Max_x / ratio[0])
            return base_size * ratio[0] / ratio[1], base_size
        

    def draw_curves(self, curves, config):
        self.clear(config.subplot_layout, config)

        plot_mode = getattr(config, "plot_mode", "line2d")
        if plot_mode == "heatmap2d":
            self._draw_heatmaps(curves, config)
        elif plot_mode == "plot3d":
            self._draw_3d(curves, config)
        else:
            self._draw_lines(curves, config)

        rows, _ = config.subplot_layout
        w, h = self.ratio_to_inches(config.ratio)
        self.fig.set_size_inches(w, h)

        if config.dirty:
            if plot_mode == "line2d" and config.shared_x and rows > 1:
                self.fig.subplots_adjust(hspace=0)
            else:
                self.fig.tight_layout()
            config.dirty = False

        self.draw_idle()


    # def _get_axis(self, axis):

    #     if axis == "primary":
    #         return self.ax
    #     elif axis == "secondary":
    #         if self.ax2 is None:
    #             self.ax2 = self.ax.twinx()
    #         return self.ax2
    #     else:
    #         raise ValueError("Unknown axis")
    
    def _draw_lines(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        curve_count = len(curves)
        for curve_index, curve in enumerate(curves):
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]

            if curve.axis == "secondary":
                secondary_ax = self.ax2.get(i)
                if secondary_ax is None:
                    secondary_ax = ax.twinx()
                    self.ax2[i] = secondary_ax
                ax = secondary_ax

            x_raw, y_raw = curve.xy()
            if not _same_length(x_raw, y_raw):
                curve._mpl_line = None
                continue

            x, y = downsample_line_points(x_raw, y_raw)
            (line,) = ax.plot(
                x,
                y,
                label=curve.label,
                color=curve.color,
                marker=curve.marker,
                markersize=curve.marker_size,
                markerfacecolor=curve.marker_face_color,
                markeredgecolor=curve.marker_edge_color,
                linestyle=curve.linestyle,
                linewidth=curve.linewidth,
                zorder=_curve_zorder(curve_count, curve_index),
                alpha=_curve_opacity(curve),
            )
            curve._mpl_line = line

        for secondary_ax in self.ax2.values():
            secondary_ax.relim()
            secondary_ax.autoscale_view(scalex=False, scaley=True)

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            rows, cols = config.subplot_layout
            r, _ = divmod(i, cols)
            ax2 = self.ax2.get(i)

            if config.shared_x:
                if r == rows - 1:
                    ax.set_xlabel(ov.get("xlabel", config.xlabel))
                else:
                    ax.set_xlabel("")
                    ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel(ov.get("xlabel", config.xlabel))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN

            ax.set_ylabel(ov.get("ylabel", config.ylabel))
            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            _apply_major_locator(ax.xaxis, xticks)
            _apply_major_locator(ax.yaxis, yticks)

            if rows > 1 and config.shared_x and r > 0:
                yticks_labels = ax.get_yticklabels()
                if yticks_labels:
                    yticks_labels[-1].set_visible(False)

            self._apply_minor_ticks(ax, config.minor_ticks)
            ax.grid(config.grid, which="major")
            if config.minor_grid:
                ax.grid(True, which="minor", linestyle=":", linewidth=0.5)
            else:
                ax.grid(False, which="minor")

            if ax2 is not None:
                ax2.yaxis.set_ticks_position("right")
                ax2.yaxis.set_label_position("right")
                ax2.tick_params(
                    axis="y",
                    which="both",
                    left=False,
                    labelleft=False,
                    right=True,
                    labelright=True,
                )
                _apply_major_locator(ax2.yaxis, yticks)
                self._apply_minor_ticks(ax2, config.minor_ticks, include_x=False)
                ax2.grid(False, which="both")

            if config.legend:
                handles, labels = ax.get_legend_handles_labels()
                if ax2 is not None:
                    handles2, labels2 = ax2.get_legend_handles_labels()
                    handles += handles2
                    labels += labels2
                if handles:
                    legend = ax.legend(handles, labels)
                    legend.set_draggable(True)

    def _draw_heatmaps(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        subplot_artists = {}
        subplot_labels = {}

        curve_count = len(curves)
        for curve_index, curve in enumerate(curves):
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]
            x, y, z = curve.xyz()
            if z is None or not _same_length(x, y, z):
                continue

            cmap = self._colormap_for_curve(curve)
            zorder = _curve_zorder(curve_count, curve_index)
            try:
                if getattr(curve, "uses_colormap", True):
                    if len(x) >= 3:
                        artist = ax.tripcolor(x, y, z, shading="auto", cmap=cmap, zorder=zorder, alpha=_curve_opacity(curve))
                    else:
                        artist = ax.scatter(x, y, c=z, cmap=cmap, zorder=zorder, alpha=_curve_opacity(curve))
                else:
                    if len(x) >= 3:
                        artist = ax.tripcolor(x, y, z, shading="flat", color=curve.color, zorder=zorder, alpha=_curve_opacity(curve))
                    else:
                        artist = ax.scatter(x, y, c=curve.color, s=36, zorder=zorder, alpha=_curve_opacity(curve))
            except Exception:
                artist = ax.scatter(x, y, c=z, cmap=cmap, zorder=zorder, alpha=_curve_opacity(curve)) if getattr(curve, "uses_colormap", True) else ax.scatter(x, y, c=curve.color, s=36, zorder=zorder, alpha=_curve_opacity(curve))

            setattr(artist, "_plotter_curve", curve)
            subplot_artists[i] = artist
            subplot_labels[i] = self._colorbar_label(curve, curve.z_col or curve.name or "Value")

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            rows, cols = config.subplot_layout
            r, _ = divmod(i, cols)

            if config.shared_x:
                if r == rows - 1:
                    ax.set_xlabel(ov.get("xlabel", config.xlabel))
                else:
                    ax.set_xlabel("")
                    ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel(ov.get("xlabel", config.xlabel))

            ax.set_ylabel(ov.get("ylabel", config.ylabel))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN

            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            _apply_major_locator(ax.xaxis, xticks)
            _apply_major_locator(ax.yaxis, yticks)

            self._apply_minor_ticks(ax, config.minor_ticks)
            ax.grid(config.grid, which="major")
            if config.minor_grid:
                ax.grid(True, which="minor", linestyle=":", linewidth=0.5)
            else:
                ax.grid(False, which="minor")

            artist = subplot_artists.get(i)
            if artist is not None and self._should_show_colorbar(curves, i):
                colorbar = self.fig.colorbar(artist, ax=ax, **self._colorbar_kwargs(ax))
                colorbar.set_label(subplot_labels.get(i, "Value"))
                self._colorbars.append(colorbar)

    def _draw_3d(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        subplot_zlabels = {}
        subplot_handles = {}

        curve_count = len(curves)
        for curve_index, curve in enumerate(curves):
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]
            x, y, z = curve.xyz()
            if z is None or not _same_length(x, y, z):
                continue
            style = self._curve_render_style(curve)
            subplot_zlabels.setdefault(i, curve.z_col or "Z")
            zorder = _curve_zorder(curve_count, curve_index)

            if style == "surface":
                artist, colorbar_label = self._plot_surface_3d(ax, x, y, z, curve)
                if artist is not None:
                    artist.set_zorder(zorder)
                    artist.set_label("_nolegend_")
                    setattr(artist, "_plotter_curve", curve)
                    self._add_colorbar(ax, artist, self._colorbar_label(curve, colorbar_label or curve.z_col or curve.label))
                    curve._mpl_line = artist
                    facecolor = self._representative_rgba(curve)
                    subplot_handles.setdefault(i, []).append((Patch(facecolor=facecolor, edgecolor="none"), curve.label))
                continue

            if style == "volume":
                mappable, colorbar_label = self._plot_volume_3d(ax, x, y, z, curve)
                if mappable is not None:
                    if hasattr(mappable, "set_zorder"):
                        mappable.set_zorder(zorder)
                    setattr(mappable, "_plotter_curve", curve)
                    self._add_colorbar(ax, mappable, self._colorbar_label(curve, colorbar_label or "Point density"))
                    subplot_handles.setdefault(i, []).append(
                        (Patch(facecolor=self._representative_rgba(curve), edgecolor="none", alpha=_scaled_alpha(curve, 0.45)), curve.label)
                    )
                curve._mpl_line = mappable
                continue

            (line,) = ax.plot(
                x,
                y,
                z,
                label=curve.label,
                color=curve.color,
                marker=curve.marker,
                markersize=curve.marker_size,
                markerfacecolor=curve.marker_face_color,
                markeredgecolor=curve.marker_edge_color,
                linestyle=curve.linestyle,
                linewidth=curve.linewidth,
                zorder=zorder,
                alpha=_curve_opacity(curve),
            )
            curve._mpl_line = line
            subplot_handles.setdefault(i, []).append((line, curve.label))

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN
            zticks = ov.get("zticksN", getattr(config, "zticksN", None)) or getattr(config, "zticksN", None)

            ax.set_xlabel(ov.get("xlabel", config.xlabel))
            ax.set_ylabel(ov.get("ylabel", config.ylabel))
            ax.set_zlabel(subplot_zlabels.get(i, "Z"))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            _apply_major_locator(ax.xaxis, xticks)
            _apply_major_locator(ax.yaxis, yticks)
            _apply_major_locator(ax.zaxis, zticks)

            ax.grid(config.grid)
            if config.legend and subplot_handles.get(i):
                handles, labels = zip(*subplot_handles[i])
                legend = ax.legend(handles, labels)
                if legend is not None:
                    legend.set_draggable(True)

    def _apply_minor_ticks(self, axis, enabled, include_x=True):
        if enabled:
            axis.minorticks_on()
            if include_x:
                axis.xaxis.set_minor_locator(AutoMinorLocator())
            axis.yaxis.set_minor_locator(AutoMinorLocator())
            return
        axis.minorticks_off()

    def _curve_render_style(self, curve):
        return getattr(curve, "render_style", "line") or "line"

    def _plot_surface_3d(self, ax, x, y, z, curve):
        cmap = self._colormap_for_curve(curve)
        use_colormap = getattr(curve, "uses_colormap", True)
        grid = self._grid_from_xyz(x, y, z)
        try:
            if grid is not None:
                xg, yg, zg = grid
                kwargs = {
                    "linewidth": 0,
                    "antialiased": True,
                    "shade": True,
                    "alpha": _scaled_alpha(curve, 0.95),
                }
                if use_colormap:
                    kwargs["cmap"] = cmap
                else:
                    kwargs["color"] = curve.color
                artist = ax.plot_surface(xg, yg, zg, **kwargs)
            else:
                kwargs = {
                    "linewidth": 0.2,
                    "antialiased": True,
                    "shade": True,
                    "alpha": _scaled_alpha(curve, 0.95),
                }
                if use_colormap:
                    kwargs["cmap"] = cmap
                else:
                    kwargs["color"] = curve.color
                artist = ax.plot_trisurf(x, y, z, **kwargs)
            return artist, curve.z_col or curve.label
        except Exception:
            if use_colormap:
                line = ax.scatter(x, y, z, c=z, cmap=cmap, s=15, alpha=_scaled_alpha(curve, 0.7))
            else:
                line = ax.scatter(x, y, z, c=curve.color, s=15, alpha=_scaled_alpha(curve, 0.7))
            return line, curve.z_col or curve.label

    def _plot_volume_3d(self, ax, x, y, z, curve):
        if len(x) < 2:
            return None, None

        points = np.column_stack([x, y, z])
        finite = np.isfinite(points).all(axis=1)
        points = points[finite]
        if len(points) < 2:
            return None, None

        bins = max(4, min(18, int(round(len(points) ** (1 / 3))) + 1))
        counts, edges = np.histogramdd(points, bins=bins)
        filled = counts > 0
        if not filled.any():
            return None, None

        x_edges, y_edges, z_edges = edges
        xg, yg, zg = np.meshgrid(x_edges, y_edges, z_edges, indexing="ij")
        cmap = self._colormap_for_curve(curve)
        use_colormap = getattr(curve, "uses_colormap", True)
        values = counts[filled]
        if use_colormap and values.size:
            vmin, vmax = float(values.min()), float(values.max())
            if vmin == vmax:
                vmax = vmin + 1.0
            mapper = Normalize(vmin=vmin, vmax=vmax)
            facecolors = cmap(mapper(counts))
            facecolors[..., -1] *= _curve_opacity(curve)
            facecolors[~filled, -1] = 0.0
            mappable = ScalarMappable(norm=mapper, cmap=cmap)
            mappable.set_array(counts)
        elif use_colormap:
            facecolors = cmap(np.zeros_like(counts, dtype=float))
            facecolors[..., -1] *= _curve_opacity(curve)
            mappable = ScalarMappable(cmap=cmap)
            mappable.set_array(counts)
        else:
            facecolors = np.zeros(counts.shape + (4,), dtype=float)
            facecolors[...] = to_rgba(curve.color, alpha=_scaled_alpha(curve, 0.4))
            facecolors[~filled, -1] = 0.0
            mappable = None

        try:
            ax.voxels(xg, yg, zg, filled, facecolors=facecolors, edgecolors="none", shade=True)
        except Exception:
            if use_colormap:
                scatter = ax.scatter(
                    points[:, 0],
                    points[:, 1],
                    points[:, 2],
                    c=points[:, 2],
                    cmap=cmap,
                    s=12,
                    alpha=_scaled_alpha(curve, 0.2),
                )
            else:
                scatter = ax.scatter(
                    points[:, 0],
                    points[:, 1],
                    points[:, 2],
                    c=curve.color,
                    s=12,
                    alpha=_scaled_alpha(curve, 0.2),
                )
            return scatter, curve.z_col or "Z"

        ax.set_xlim(float(x_edges[0]), float(x_edges[-1]))
        ax.set_ylim(float(y_edges[0]), float(y_edges[-1]))
        ax.set_zlim(float(z_edges[0]), float(z_edges[-1]))
        return mappable, "Point density"

    def _grid_from_xyz(self, x, y, z):
        try:
            x = np.asarray(x)
            y = np.asarray(y)
            z = np.asarray(z)
        except Exception:
            return None

        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        x = x[finite]
        y = y[finite]
        z = z[finite]
        if len(x) < 4:
            return None

        x_vals = np.unique(x)
        y_vals = np.unique(y)
        if len(x_vals) * len(y_vals) != len(x):
            return None

        grid = np.full((len(y_vals), len(x_vals)), np.nan, dtype=float)
        x_index = {value: idx for idx, value in enumerate(x_vals)}
        y_index = {value: idx for idx, value in enumerate(y_vals)}
        for xv, yv, zv in zip(x, y, z):
            grid[y_index[yv], x_index[xv]] = zv

        if np.isnan(grid).any():
            return None

        xg, yg = np.meshgrid(x_vals, y_vals)
        return xg, yg, grid

    def _add_colorbar(self, ax, artist, label):
        if artist is None:
            return
        curve = getattr(artist, "_plotter_curve", None)
        if curve is not None and not getattr(curve, "show_colorbar", True):
            return
        try:
            colorbar = self.fig.colorbar(artist, ax=ax, **self._colorbar_kwargs(ax))
            colorbar.set_label(label)
            self._colorbars.append(colorbar)
        except Exception:
            pass

    def _colorbar_kwargs(self, ax):
        if getattr(ax, "name", "") == "3d":
            return {
                "fraction": 0.045,
                "pad": 0.04,
                "shrink": 0.78,
                "aspect": 28,
            }
        return {
            "fraction": 0.05,
            "pad": 0.035,
            "shrink": 0.9,
            "aspect": 26,
        }

    def _representative_rgba(self, curve):
        if getattr(curve, "uses_colormap", False):
            rgba = self._colormap_for_curve(curve)(0.65)
            return rgba[:3] + (rgba[3] * _curve_opacity(curve),)
        return to_rgba(curve.color, alpha=_curve_opacity(curve))

    def _colorbar_label(self, curve, fallback):
        return getattr(curve, "colorbar_label", None) or fallback

    def _should_show_colorbar(self, curves, subplot_index):
        for curve in curves:
            if self._normalized_subplot_index(curve, max(0, len(self.axes) - 1)) != subplot_index:
                continue
            if getattr(curve, "uses_colormap", False) and getattr(curve, "show_colorbar", True):
                return True
        return False

    def _normalized_subplot_index(self, curve, max_index):
        i = max(0, min(int(curve.subplot_index), max_index))
        if curve.subplot_index != i:
            curve.subplot_index = i
        return i

    def _colormap_for_curve(self, curve):
        colors = PLOTLY_PALETTES.get(curve.palette_name, PLOTLY_PALETTES["Matplotlib default"])
        return LinearSegmentedColormap.from_list(
            f"plotter_{curve.palette_name}_{id(curve)}",
            colors,
        )

    def _remove_colorbars(self):
        for colorbar in self._colorbars:
            try:
                colorbar.remove()
            except Exception:
                pass
        self._colorbars.clear()

    def _create_subplots(self, layout, shared_x=False, shared_y=False, config=None):
        rows, cols = layout
        plot_mode = getattr(config, "plot_mode", "line2d") if config is not None else "line2d"

        self.fig.clear()
        self.axes = []
        self.ax2.clear()
        self._colorbars.clear()

        if plot_mode == "plot3d":
            for index in range(rows * cols):
                self.axes.append(self.fig.add_subplot(rows, cols, index + 1, projection="3d"))
            return

        sharex = "col" if shared_x else False
        sharey = "row" if shared_y else False
        axs = self.fig.subplots(rows, cols, sharex=sharex, sharey=sharey)

        if shared_x and plot_mode == "line2d":
            self.fig.subplots_adjust(hspace=0)
        # 
        # flatten → axs[0], axs[1], ...
        self.axes = list(axs.flat) if hasattr(axs, "flat") else [axs]

    def refresh_legends(self, config):
        """Rebuild legends from the *current* artists without replotting curves."""
        for i, ax in enumerate(self.axes):
            # Remove existing legend if any
            old = ax.get_legend()
            if old is not None:
                old.remove()

            if not config.legend:
                continue

            h, l = ax.get_legend_handles_labels()

            ax2 = self.ax2.get(i)
            if ax2 is not None:
                h2, l2 = ax2.get_legend_handles_labels()
                h += h2
                l += l2

            if h:
                leg = ax.legend(h, l)
                leg.set_draggable(True)

