"""
main_window.py

Main window for the SonicDNA Studio GUI.
Responsive layout supporting Desktop (sidebar) and Mobile (topbar).
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, QSize
from ui.home_panel import HomePanel
from ui.extraction_panel import ExtractionPanel
from ui.synthesis_panel import SynthesisPanel
from ui.bank_panel import BankPanel
from ui.music_panel import MusicPanel

logger = logging.getLogger("MainWindow")

class MainWindow(QMainWindow):
    """
    Main application window with a responsive sidebar/topbar and a content area.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SonicDNA Studio")
        self.resize(1000, 700)
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")

        # --- Central widget & root layout ---
        self.central = QWidget(self)
        self.root_layout = QVBoxLayout(self.central)
        self.central.setLayout(self.root_layout)

        # Container for navigation and content
        self.container_widget = QWidget()
        self.container_layout = QHBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        # --- Navigation Bar ---
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(10, 10, 10, 10)
        self.nav_layout.setSpacing(10)

        self.btn_home = QPushButton("Home / Docs")
        self.btn_extract = QPushButton("Extractor")
        self.btn_synth = QPushButton("Synthesizer")
        self.btn_bank = QPushButton("Sound Bank")
        self.btn_wave = QPushButton("Waveform Generator")

        self.nav_buttons = [self.btn_home, self.btn_extract, self.btn_synth, self.btn_bank, self.btn_wave]
        
        # Style navigation buttons
        for btn in self.nav_buttons:
            btn.setMinimumHeight(45)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #222;
                    border: none;
                    border-radius: 5px;
                    text-align: left;
                    padding-left: 15px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #333;
                }
                QPushButton:checked {
                    background-color: #0078d7;
                }
            """)
            btn.setCheckable(True)
            self.nav_layout.addWidget(btn)

        self.nav_stretch = self.nav_layout.addStretch()

        # Divider line
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setStyleSheet("color: #333;")

        self.container_layout.addWidget(self.nav_widget)
        self.container_layout.addWidget(self.divider)

        # --- Main area with stacked widget ---
        self.stacked = QStackedWidget()
        
        self.home_panel = HomePanel()
        self.extraction_panel = ExtractionPanel()
        self.synthesis_panel = SynthesisPanel()
        self.bank_panel = BankPanel()
        self.music_panel = MusicPanel()

        self.stacked.addWidget(self.home_panel)
        self.stacked.addWidget(self.extraction_panel)
        self.stacked.addWidget(self.synthesis_panel)
        self.stacked.addWidget(self.bank_panel)
        self.stacked.addWidget(self.music_panel)

        self.container_layout.addWidget(self.stacked, 1)

        self.root_layout.addWidget(self.container_widget)
        self.setCentralWidget(self.central)

        # --- Signals ---
        self.btn_home.clicked.connect(lambda: self.switch_page(0))
        self.btn_extract.clicked.connect(lambda: self.switch_page(1))
        self.btn_synth.clicked.connect(lambda: self.switch_page(2))
        self.btn_bank.clicked.connect(lambda: self.switch_page(3))
        self.btn_wave.clicked.connect(lambda: self.switch_page(4))

        # Initialize state
        self.switch_page(0)
        self._update_layout()

        logger.info("MainWindow initialized")

    def switch_page(self, index: int):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            
    def resizeEvent(self, event):
        """Handle responsive layout changes based on window width."""
        super().resizeEvent(event)
        self._update_layout()
        
    def _update_layout(self):
        """Switches between Sidebar (Desktop) and Topbar (Mobile) based on width."""
        is_mobile = self.width() < 700
        
        # Remove nav layout items to rebuild it
        for i in reversed(range(self.nav_layout.count())): 
            item = self.nav_layout.itemAt(i)
            if item.widget():
                self.nav_layout.removeWidget(item.widget())
            elif item.spacerItem():
                self.nav_layout.removeItem(item.spacerItem())

        if is_mobile:
            # Change to vertical stacking: Nav on top, content below
            self.container_layout.setDirection(QBoxLayout.TopToBottom)
            self.nav_layout.setDirection(QBoxLayout.LeftToRight)
            self.divider.setFrameShape(QFrame.HLine)
            
            # Re-add buttons horizontally
            for btn in self.nav_buttons:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #222;
                        border: none;
                        border-radius: 5px;
                        text-align: center;
                        font-size: 13px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #333;
                    }
                    QPushButton:checked {
                        background-color: #0078d7;
                    }
                """)
                self.nav_layout.addWidget(btn)
        else:
            # Change to horizontal stacking: Nav on left, content on right
            self.container_layout.setDirection(QBoxLayout.LeftToRight)
            self.nav_layout.setDirection(QBoxLayout.TopToBottom)
            self.divider.setFrameShape(QFrame.VLine)
            
            # Re-add buttons vertically
            for btn in self.nav_buttons:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #222;
                        border: none;
                        border-radius: 5px;
                        text-align: left;
                        padding-left: 15px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #333;
                    }
                    QPushButton:checked {
                        background-color: #0078d7;
                    }
                """)
                self.nav_layout.addWidget(btn)
            self.nav_layout.addStretch()

# Provide QBoxLayout for direction enum in update_layout
from PySide6.QtWidgets import QBoxLayout
