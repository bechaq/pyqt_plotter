from DataFile import load_data_file
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

    def load_file(self, path):
        self.data_files[path] = load_data_file(path)
        # self.curves.clear()
        # self.curve_counter = 1
        
    def remove_file(self, file_name):
        if file_name in self.data_files:
            del self.data_files[file_name]
            # Also remove any curves associated with this file
            self.curves = [c for c in self.curves if c.file_name != file_name]
            self.update_plot()


    def add_curve(self, file_name, data_file, x_col, y_col, axis, color, palette_name="Plotly", marker=None, marker_size=None, linestyle="-", linewidth=1.0, x_data_file=None, y_data_file=None):
        name = f"Curve {self.curve_counter}"
        self.curve_counter += 1
        curve = Curve(file_name, data_file, x_col, y_col, axis, name=name, color=color, palette_name=palette_name, marker=marker, marker_size=marker_size, linestyle=linestyle, linewidth=linewidth, x_data_file=x_data_file, y_data_file=y_data_file, subplot_index=0)
        self.curves.append(curve)
        self.update_plot()
        return curve

    def remove_curve(self, idx):
        if 0 <= idx < len(self.curves):
            self.curves.pop(idx)
            self.curve_counter -= 1
            self.update_plot()

    def update_curve(self, idx, x_col, y_col, axis, color, palette_name="Plotly", Marker = None,marker_size=None, linestyle="-", linewidth=1.0, subplot_index=0):
        c = self.curves[idx]
        c.x_col = x_col
        c.y_col = y_col
        c.axis = axis
        c.color = color   
        c.marker = Marker
        c.marker_size = marker_size
        c.palette_name = palette_name
        c.linestyle = linestyle
        c.linewidth = linewidth
        c.subplot_index = subplot_index
        # self.update_plot()

    def update_plot(self):
        self.canvas.draw_curves(self.curves, self.config)
    
    def to_dict(self) -> dict:
        """Export the full editable plot state."""
        # data_files: store original paths; you need to keep them somewhere
        # Recommended: store DataFile.path when loading, and use that.
        data_files = {name: df.path for name, df in self.data_files.items()}

        config = {
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
            "palette_name": getattr(self.config, "palette_name", "Plotly"),
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
                "color": c.color,
                "palette_name": getattr(c, "palette_name", "Plotly"),
                "marker": c.marker,
                "marker_size": c.marker_size,
                "linestyle": c.linestyle,
                "linewidth": c.linewidth,
            })

        return {"version": 1, "data_files": data_files, "config": config, "curves": curves}

    def save_project(self, project_path: str):
        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load_project(self, project_path: str):
        """
        Load project and rebuild controller state.
        If some data files are missing, we skip curves that depend on them,
        and you can warn the user.
        """
        import json
        from DataFile import load_data_file

        with open(project_path, "r", encoding="utf-8") as f:
            obj = json.load(f)

        # Reset current state
        self.data_files.clear()
        self.curves.clear()

        # Reload data files
        missing = []
        for key, path in obj.get("data_files", {}).items():
            if not os.path.exists(path):
                missing.append((key, path))
                continue
            df = load_data_file(path)
            self.data_files[key] = df

        # Restore config
        cfg = obj.get("config", {})
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
        self.config.palette_name = cfg.get("palette_name", "Plotly")
        self.config.dirty = True

        # Restore curves (only if their referenced files exist)
        for c in obj.get("curves", []):
            x_key = c.get("x_file")
            y_key = c.get("y_file")
            if x_key not in self.data_files or y_key not in self.data_files:
                continue

            curve = self._make_curve_from_dict(c)
            self.curves.append(curve)

        self.update_plot()
        return missing

    def _find_file_key(self, data_file):
        for k, df in self.data_files.items():
            if df is data_file:
                return k
        return None

    def _make_curve_from_dict(self, d: dict):
        from Curves import Curve  # adjust to your actual import
        x_df = self.data_files[d["x_file"]]
        y_df = self.data_files[d["y_file"]]

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
            linestyle=d.get("linestyle", "-"),
            linewidth=d.get("linewidth", 2.0),
            x_data_file=x_df,
            y_data_file=y_df,
            name=d.get("name", "Curve"),
        )
        return curve
