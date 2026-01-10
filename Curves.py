
class Curve:
    def __init__(self, file_name, data_file, x_col, y_col, axis="primary", name=None, color = None, palette_name="Plotly", marker=None, marker_size=None, marker_face_color=None, marker_edge_color=None, linestyle="-", linewidth=2.0, x_data_file=None, y_data_file=None, subplot_index=0):
        
        self.file_name = file_name 
        self.data_file = data_file
        # Support multi-file curves: store data_file for each column
        self.x_data_file = x_data_file or data_file
        self.y_data_file = y_data_file or data_file
        self.x_col = x_col
        self.y_col = y_col
        self.axis = axis
        self.name = name or "Curve"
        self.color = color
        self.subplot_index = subplot_index
        self.palette_name = palette_name
        self.marker = marker
        self.linestyle = linestyle
        self.linewidth = linewidth
        self.marker_size = marker_size
        self.marker_face_color = marker_face_color
        self.marker_edge_color = marker_edge_color
        self._mpl_line = None  # Matplotlib Line2D object after plotting

    @property
    def label(self):
        # what appears in legend
        return self.name

    def display_name(self):
        # what appears in the curves list
        ax = "Primary" if self.axis == "primary" else "Secondary"
        return f"{self.name} ({ax})"

    def xy(self):
        return (
            self.x_data_file.get_column(self.x_col),
            self.y_data_file.get_column(self.y_col)
        )