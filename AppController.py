from Curves import Curve
from PlotConfig import PlotConfig
import json
import os
# =========================
# Controller
# =========================

class AppController:
    def __init__(self, canvas):
        self.canvas = canvas
        self.data_files = {}
        self.curves = []
        self.config = PlotConfig()
        self.curve_counter = 1

    # def load_file(self, path):
    #     self.data_files[path] = load_data_file(path)
    #     # self.curves.clear()
    #     # self.curve_counter = 1
        
    def remove_file(self, file_name):
        if file_name in self.data_files:
            removed_data_file = self.data_files.pop(file_name)
            # Remove curves that depend on the deleted data source on either axis.
            self.curves = [
                c for c in self.curves
                if c.x_data_file is not removed_data_file
                and c.y_data_file is not removed_data_file
                and c.z_data_file is not removed_data_file
            ]
            self.update_plot()


    def add_curve(
        self,
        file_name,
        data_file,
        x_col,
        y_col,
        axis,
        color,
        palette_name="Plotly",
        marker=None,
        marker_size=None,
        linestyle="-",
        linewidth=2.0,
        render_style="line",
        x_data_file=None,
        y_data_file=None,
        z_col=None,
        z_data_file=None,
        uses_colormap=False,
        show_colorbar=True,
        colorbar_label=None,
        opacity=1.0,
    ):
        name = f"Curve {self.curve_counter}"
        self.curve_counter += 1
        curve = Curve(
            file_name,
            data_file,
            x_col,
            y_col,
            axis,
            name=name,
            color=color,
            palette_name=palette_name,
            marker=marker,
            marker_size=marker_size,
            linestyle=linestyle,
            linewidth=linewidth,
            render_style=render_style,
            x_data_file=x_data_file,
            y_data_file=y_data_file,
            z_col=z_col,
            z_data_file=z_data_file,
            subplot_index=0,
            uses_colormap=uses_colormap,
            show_colorbar=show_colorbar,
            colorbar_label=colorbar_label,
            opacity=opacity,
        )
        self.curves.append(curve)
        self.update_plot()
        return curve

    def remove_curve(self, idx):
        if 0 <= idx < len(self.curves):
            self.curves.pop(idx)
            # self.curve_counter -= 1
            self.update_plot()

    def update_curve(
        self,
        idx,
        x_col,
        y_col,
        axis,
        color,
        palette_name="Plotly",
        subplot_index=0,
        z_col=None,
        render_style="line",
        uses_colormap=False,
        show_colorbar=True,
        colorbar_label=None,
        opacity=None,
    ):
        c = self.curves[idx]
        c.x_col = x_col
        c.y_col = y_col
        c.z_col = z_col
        c.axis = axis
        c.color = color   
        c.render_style = render_style
        c.uses_colormap = uses_colormap
        c.show_colorbar = show_colorbar
        c.colorbar_label = colorbar_label
        if opacity is not None:
            c.opacity = opacity
        # c.marker = Marker
        # c.marker_size = marker_size
        # c.palette_name = palette_name
        # c.linestyle = linestyle
        # c.linewidth = linewidth
        c.subplot_index = subplot_index
        # self.update_plot()

    def update_plot(self):
        self.canvas.draw_curves(self.curves, self.config)

    def normalize_curve_subplots(self):
        rows, cols = getattr(self.config, "subplot_layout", (1, 1))
        max_index = max(0, rows * cols - 1)
        for curve in self.curves:
            curve.subplot_index = max(0, min(int(curve.subplot_index), max_index))
    
    def to_dict(self, project_dir: str | None = None) -> dict:
        """Export the full editable plot state."""
        data_files = {
            name: self._serialize_path(df.path, project_dir)
            for name, df in self.data_files.items()
        }

        config = {
            "plot_mode": getattr(self.config, "plot_mode", "line2d"),
            "xlabel": self.config.xlabel,
            "ylabel": self.config.ylabel,
            "ratio": list(self.config.ratio),
            "xlimits": list(self.config.xlimits) if self.config.xlimits else [None, None],
            "ylimits": list(self.config.ylimits) if self.config.ylimits else [None, None],
            "grid": bool(self.config.grid),
            "minor_ticks": bool(getattr(self.config, "minor_ticks", False)),
            "minor_grid": bool(getattr(self.config, "minor_grid", False)),
            "legend": bool(self.config.legend),
            "xticksN": getattr(self.config, "xticksN", None),
            "yticksN": getattr(self.config, "yticksN", None),
            "zticksN": getattr(self.config, "zticksN", None),
            "palette_name": getattr(self.config, "palette_name", "Plotly"),
            "subplot_layout":getattr(self.config, "subplot_layout", (1,1)),
            "shared_x": getattr(self.config, "shared_x", False),
            "shared_y": getattr(self.config, "shared_y", False),
            "subplots_config": getattr(self.config, "subplots_config", {}),
        }

        curves = []
        for c in self.curves:
            curves.append({
                "name": c.name,
                "axis": c.axis,
                "x_file": self._find_file_key(c.x_data_file),
                "x_col": c.x_col,
                "y_file": self._find_file_key(c.y_data_file),
                "y_col": c.y_col,
                "z_file": self._find_file_key(c.z_data_file) if c.z_data_file is not None else None,
                "z_col": c.z_col,
                "color": c.color,
                "palette_name": getattr(c, "palette_name", "Plotly"),
                "marker": c.marker,
                "marker_size": c.marker_size,
                "marker_face_color": c.marker_face_color,
                "marker_edge_color": c.marker_edge_color,
                "linestyle": c.linestyle,
                "linewidth": c.linewidth,
                "render_style": getattr(c, "render_style", "line"),
                "subplot_index": c.subplot_index,
                "uses_colormap": getattr(c, "uses_colormap", False),
                "show_colorbar": getattr(c, "show_colorbar", True),
                "colorbar_label": getattr(c, "colorbar_label", None),
                "opacity": getattr(c, "opacity", 1.0),

            })

        return {"version": 1, "data_files": data_files, "config": config, "curves": curves}

    def save_project(self, project_path: str):
        project_dir = os.path.dirname(os.path.abspath(project_path))
        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(project_dir=project_dir), f, indent=2)

    def load_project(self, project_path: str):
        with open(project_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        project_dir = os.path.dirname(os.path.abspath(project_path))
        return self.load_state_obj(obj, base_dir=project_dir)

    def load_state_obj(self, obj: dict, base_dir: str | None = None):
        """
        Load a serialized controller state from an in-memory dict.
        If some data files are missing, we skip curves that depend on them.
        """
        from DataFile import load_data_file

        # Reset current state
        self.data_files.clear()
        self.curves.clear()

        # Reload data files
        missing = []
        for key, path in obj.get("data_files", {}).items():
            resolved = self._resolve_path(path, base_dir)
            if not os.path.exists(resolved):
                missing.append((key, resolved))
                continue
            df = load_data_file(resolved)
            self.data_files[key] = df

        # Restore config
        cfg = obj.get("config", {})
        self.config.plot_mode = cfg.get("plot_mode", "line2d")
        self.config.xlabel = cfg.get("xlabel", "")
        self.config.ylabel = cfg.get("ylabel", "")
        self.config.ratio = tuple(cfg.get("ratio", [4, 3]))
        self.config.xlimits = tuple(cfg.get("xlimits", [None, None]))
        self.config.ylimits = tuple(cfg.get("ylimits", [None, None]))
        self.config.grid = cfg.get("grid", True)
        self.config.legend = cfg.get("legend", True)
        self.config.minor_ticks = cfg.get("minor_ticks", False)
        self.config.minor_grid = cfg.get("minor_grid", False)
        self.config.xticksN = cfg.get("xticksN", None)
        self.config.yticksN = cfg.get("yticksN", None)
        self.config.zticksN = cfg.get("zticksN", self.config.yticksN)
        self.config.palette_name = cfg.get("palette_name", "Plotly")
        self.config.dirty = True
        self.config.subplot_layout = tuple(cfg.get("subplot_layout", (1, 1)))
        self.config.shared_x = cfg.get("shared_x", False)
        self.config.shared_y = cfg.get("shared_y", False)
        
        raw = cfg.get("subplots_config", {}) or {}
        fixed = {}
        for k, v in raw.items():
            try:
                fixed[int(k)] = v or {}
            except Exception:
                pass
        self.config.subplots_config = fixed
        # NOW redraw (after keys are correct)
        

        # Restore curves (only if their referenced files exist)
        requires_z = self.config.plot_mode in {"heatmap2d", "plot3d"}
        for c in obj.get("curves", []):
            x_key = c.get("x_file")
            y_key = c.get("y_file")
            if x_key not in self.data_files or y_key not in self.data_files:
                continue
            z_key = c.get("z_file")
            if requires_z and (not c.get("z_col") or z_key not in self.data_files):
                continue
            if not self._curve_columns_exist(c, requires_z):
                continue

            curve = self._make_curve_from_dict(c)
            self.curves.append(curve)
        self.curve_counter = len(self.curves) + 1
        self.normalize_curve_subplots()
        self.update_plot()

        # Finally, apply xlim/ylim per subplot if any
        for ax in self.canvas.axes:
            ov = self.config.subplots_config.get(self.canvas.axes.index(ax), {})
            ax.set_xlim(ov.get("xlim", self.config.xlimits) or self.config.xlimits)
            ax.set_ylim(ov.get("ylim", self.config.ylimits) or self.config.ylimits)
        return missing

    def _find_file_key(self, data_file):
        for k, df in self.data_files.items():
            if df is data_file:
                return k
        return None

    def _curve_columns_exist(self, curve_state: dict, requires_z: bool):
        x_key = curve_state.get("x_file")
        y_key = curve_state.get("y_file")
        if x_key not in self.data_files or y_key not in self.data_files:
            return False

        if curve_state.get("x_col") not in self.data_files[x_key].headers:
            return False
        if curve_state.get("y_col") not in self.data_files[y_key].headers:
            return False

        z_key = curve_state.get("z_file")
        z_col = curve_state.get("z_col")
        if requires_z:
            return z_key in self.data_files and z_col in self.data_files[z_key].headers
        if z_key and z_col:
            return z_key in self.data_files and z_col in self.data_files[z_key].headers
        return True

    def _make_curve_from_dict(self, d: dict):
        from Curves import Curve  # adjust to your actual import
        x_df = self.data_files[d["x_file"]]
        y_df = self.data_files[d["y_file"]]
        z_key = d.get("z_file")
        z_df = self.data_files.get(z_key) if z_key else None

        curve = Curve(
            file_name=d["x_file"],
            data_file=x_df,
            x_col=d["x_col"],
            y_col=d["y_col"],
            axis=d.get("axis", "primary"),
            color=d.get("color", "#000000"),
            palette_name=d.get("palette_name", "Plotly"),
            marker=d.get("marker", "None"),
            marker_size=d.get("marker_size", 5),
            marker_face_color=d.get("marker_face_color", None),
            marker_edge_color=d.get("marker_edge_color", None),
            linestyle=d.get("linestyle", "-"),
            linewidth=d.get("linewidth", 2.0),
            render_style=d.get("render_style", "line"),
            x_data_file=x_df,
            y_data_file=y_df,
            z_col=d.get("z_col"),
            z_data_file=z_df,
            name=d.get("name", "Curve"),
            subplot_index=d.get("subplot_index", 0),
            uses_colormap=d.get("uses_colormap", False),
            show_colorbar=d.get("show_colorbar", True),
            colorbar_label=d.get("colorbar_label"),
            opacity=d.get("opacity", 1.0),
        )
        return curve

    def _serialize_path(self, path: str, project_dir: str | None):
        if not project_dir:
            return path
        try:
            return os.path.relpath(path, project_dir)
        except ValueError:
            return path

    def _resolve_path(self, path: str, base_dir: str | None):
        if base_dir and not os.path.isabs(path):
            return os.path.abspath(os.path.join(base_dir, path))
        return path
