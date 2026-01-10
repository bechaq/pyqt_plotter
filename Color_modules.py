from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 
from PyQt5.QtCore import * 
 ## Plotly colors
PLOTLY_PALETTES = {
     # -----------------
    # Matplotlib
    # -----------------
    "Matplotlib default": [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ],
    # -----------------
    # Plotly palettes
    # -----------------
    "Plotly": [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
        "#FF97FF", "#FECB52"
    ],
    "Plotly Dark": [
        "#1f77b4", "#ff7f0e", "#2ca02c",
        "#d62728", "#9467bd", "#8c564b"
    ],

    # -----------------
    # Seaborn
    # -----------------
    "Seaborn (deep)": [
        "#4c72b0", "#dd8452", "#55a868", "#c44e52",
        "#8172b3", "#937860", "#da8bc3", "#8c8c8c",
        "#ccb974", "#64b5cd"
    ],

    "Seaborn (pastel)": [
        "#a1c9f4", "#ffb482", "#8de5a1", "#ff9f9b",
        "#d0bbff", "#debb9b", "#fab0e4", "#cfcfcf",
        "#fffea3", "#b9f2f0"
    ],

    # -----------------
    # Scientific
    # -----------------
    "Viridis": [
        "#440154", "#482878", "#3E4989", "#31688E",
        "#26828E", "#1F9E89", "#35B779", "#6DCD59",
        "#B4DE2C", "#FDE725"
    ]
}

def make_color_swatch_icon(hex_color: str, w=28, h=14) -> QIcon:
    pm = QPixmap(w, h)
    pm.fill(QColor(hex_color))
    return QIcon(pm)

def populate_color_combo(combo: QComboBox, colors):
    combo.clear()
    combo.setIconSize(QSize(28, 14))  # or QSize(32,16) if you prefer

    for c in colors:
        icon = make_color_swatch_icon(c)
        combo.addItem(icon, " ")          # blank label (space avoids weird height issues)
        combo.setItemData(combo.count()-1, c, Qt.UserRole)  # store the hex code as data
    # If current color not in the palette, add it


def selected_color(combo: QComboBox) -> str:
    return combo.currentData(Qt.UserRole)  # returns "#RRGGBB"

def set_color_combo_to_hex(combo: QComboBox, hex_color: str):
    for i in range(combo.count()):
        if combo.itemData(i, Qt.UserRole) == hex_color:
            combo.setCurrentIndex(i)
            return

def ensure_color_in_combo(combo: QComboBox, hex_color: str):
    """Make sure hex_color exists in combo (UserRole). If not, insert it at top."""
    if not hex_color:
        return
    for i in range(combo.count()):
        if combo.itemData(i, Qt.UserRole) == hex_color:
            combo.setCurrentIndex(i)
            return
    # not found: insert custom swatch at top
    combo.insertItem(0, make_color_swatch_icon(hex_color), " ")
    combo.setItemData(0, hex_color, Qt.UserRole)
    combo.setCurrentIndex(0)
