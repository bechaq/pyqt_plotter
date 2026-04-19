from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class StartupLandingPage(QWidget):
    modeActivated = pyqtSignal(str)

    def __init__(self, mode_cards, parent=None):
        super().__init__(parent)
        self.mode_cards = mode_cards
        self._selected_mode = None
        self._preview_pixmap = None
        self._mode_buttons = {}
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(24)

        left_panel = QFrame()
        left_panel.setObjectName("landingLeftPanel")
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(28, 28, 28, 28)
        left_layout.setSpacing(18)

        eyebrow = QLabel("Clean PyQt Plotter")
        eyebrow.setObjectName("landingEyebrow")
        title = QLabel("Choose the kind of plot you want to build")
        title.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel(
            "Start with a 2D line plot, a heatmap, or a 3D visualization. "
            "Pick one on the left and the preview on the right will update."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("landingSubtitle")

        left_layout.addWidget(eyebrow)
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        left_layout.addSpacing(10)

        for mode, card in self.mode_cards.items():
            button = QPushButton(card["button_label"])
            button.setCheckable(True)
            button.setMinimumHeight(82)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("landingModeButton")
            button.clicked.connect(lambda checked=False, m=mode: self.select_mode(m))
            self._mode_buttons[mode] = button
            left_layout.addWidget(button)

        left_layout.addStretch(1)

        self.continue_btn = QPushButton("Open workspace")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setMinimumHeight(54)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setObjectName("landingContinueButton")
        self.continue_btn.clicked.connect(self._emit_active_mode)
        left_layout.addWidget(self.continue_btn)

        right_panel = QFrame()
        right_panel.setObjectName("landingRightPanel")
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(28, 28, 28, 28)
        right_layout.setSpacing(14)

        self.preview_title = QLabel("")
        preview_title_font = QFont()
        preview_title_font.setPointSize(18)
        preview_title_font.setBold(True)
        self.preview_title.setFont(preview_title_font)

        self.preview_description = QLabel("")
        self.preview_description.setWordWrap(True)
        self.preview_description.setObjectName("landingDescription")

        self.preview_image = QLabel("Preview unavailable")
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setMinimumSize(520, 360)
        self.preview_image.setObjectName("landingPreview")

        right_layout.addWidget(self.preview_title)
        right_layout.addWidget(self.preview_description)
        right_layout.addWidget(self.preview_image, 1)

        root.addWidget(left_panel, 1)
        root.addWidget(right_panel, 1)

        self.setStyleSheet(
            """
            #landingLeftPanel, #landingRightPanel {
                background: #f7f7f4;
                border: 1px solid #dad6cd;
                border-radius: 22px;
            }
            #landingEyebrow {
                color: #7b6042;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }
            #landingSubtitle, #landingDescription {
                color: #4b4b43;
                font-size: 14px;
                line-height: 1.4em;
            }
            QPushButton#landingModeButton {
                text-align: left;
                padding: 18px 22px;
                font-size: 18px;
                font-weight: 600;
                color: #292922;
                background: #fffdf8;
                border: 2px solid #d7d1c5;
                border-radius: 18px;
            }
            QPushButton#landingModeButton:hover {
                border-color: #8c6f45;
                background: #fff8ea;
            }
            QPushButton#landingModeButton:checked {
                border-color: #8c6f45;
                background: #f2e7d4;
            }
            QPushButton#landingContinueButton {
                padding: 14px 18px;
                font-size: 16px;
                font-weight: 700;
                color: white;
                background: #8c6f45;
                border: none;
                border-radius: 16px;
            }
            QPushButton#landingContinueButton:disabled {
                background: #b9ae9c;
                color: #f5f2ec;
            }
            #landingPreview {
                background: white;
                border: 1px solid #dad6cd;
                border-radius: 18px;
                color: #777;
            }
            """
        )

    def select_mode(self, mode):
        if mode not in self.mode_cards:
            return
        self._selected_mode = mode
        for button_mode, button in self._mode_buttons.items():
            button.blockSignals(True)
            button.setChecked(button_mode == mode)
            button.blockSignals(False)

        card = self.mode_cards[mode]
        self.preview_title.setText(card["title"])
        self.preview_description.setText(card["description"])
        self.continue_btn.setEnabled(True)
        self.continue_btn.setText(f"Open {card['button_label'].lower()} workspace")
        self._load_preview(card.get("image"))

    def _load_preview(self, image_path):
        self._preview_pixmap = None
        if image_path:
            path = Path(image_path)
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self._preview_pixmap = pixmap

        if self._preview_pixmap is None:
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText("Preview unavailable")
            return

        self.preview_image.setText("")
        self._refresh_preview_pixmap()

    def _refresh_preview_pixmap(self):
        if self._preview_pixmap is None:
            return
        scaled = self._preview_pixmap.scaled(
            self.preview_image.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_image.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_preview_pixmap()

    def _emit_active_mode(self):
        if self._selected_mode:
            self.modeActivated.emit(self._selected_mode)
