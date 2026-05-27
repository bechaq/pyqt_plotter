
from plot_modes import friendly_3d_style


class Curve:
    def __init__(
        self,
        file_name,
        data_file,
        x_col,
        y_col,
        axis="primary",
        name=None,
        color=None,
        palette_name="Plotly",
        marker=None,
        marker_size=None,
        marker_face_color=None,
        marker_edge_color=None,
        linestyle="-",
        linewidth=2.0,
        render_style="line",
        x_data_file=None,
        y_data_file=None,
        z_col=None,
        z_data_file=None,
        subplot_index=0,
        uses_colormap=False,
        show_colorbar=True,
        colorbar_label=None,
        opacity=1.0,
    ):
        
        self.file_name = file_name 
        self.data_file = data_file
        # Support multi-file curves: store data_file for each column
        self.x_data_file = x_data_file or data_file
        self.y_data_file = y_data_file or data_file
        self.z_data_file = z_data_file
        self.x_col = x_col
        self.y_col = y_col
        self.z_col = z_col
        self.axis = axis
        self.name = name or "Curve"
        self.color = color
        self.subplot_index = subplot_index
        self.palette_name = palette_name
        self.marker = marker
        self.linestyle = linestyle
        self.linewidth = linewidth
        self.render_style = render_style
        self.marker_size = marker_size
        self.marker_face_color = marker_face_color
        self.marker_edge_color = marker_edge_color
        self.uses_colormap = uses_colormap
        self.show_colorbar = show_colorbar
        self.colorbar_label = colorbar_label
        self.opacity = opacity
        self._mpl_line = None  # Matplotlib Line2D object after plotting

    @property
    def label(self):
        # what appears in legend
        return self.name

    def display_name(self, plot_mode="line2d"):
        # what appears in the curves list
        if plot_mode == "plot3d":
            return f"{self.name} ({friendly_3d_style(self.render_style)})"
        if plot_mode != "line2d":
            return self.name
        ax = "Primary" if self.axis == "primary" else "Secondary"
        return f"{self.name} ({ax})"

    def xy(self):
        return (
            self.x_data_file.get_column(self.x_col),
            self.y_data_file.get_column(self.y_col)
        )

    def xyz(self):
        z = None
        if self.z_data_file is not None and self.z_col is not None:
            z = self.z_data_file.get_column(self.z_col)
        x, y = self.xy()
        return x, y, z
