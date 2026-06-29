import json
import logging
import sounddevice as sd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from utils.dna_db import DNADatabase
from ui.synthesis_panel import SynthesizerThread

logger = logging.getLogger("BankPanel")

class BankPanel(QWidget):
    """
    Panel for exploring saved DNA sequences in the SQLite Database.
    """
    def __init__(self) -> None:
        super().__init__()
        self.db = DNADatabase()
        self.current_thread = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Left Column: List of sounds
        left_col = QVBoxLayout()
        header = QLabel("Sound Bank")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #fff;")
        left_col.addWidget(header)
        
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.setMinimumHeight(30)
        self.refresh_btn.clicked.connect(self.load_bank)
        left_col.addWidget(self.refresh_btn)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: #ddd;
                border: 1px solid #444;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        self.list_widget.itemSelectionChanged.connect(self.on_item_selected)
        left_col.addWidget(self.list_widget)

        # Right Column: Details & Actions
        right_col = QVBoxLayout()
        self.details_label = QLabel("Select a sound to view DNA.")
        self.details_label.setStyleSheet("color: #aaa;")
        right_col.addWidget(self.details_label)

        self.sequence_viewer = QTextEdit()
        self.sequence_viewer.setReadOnly(True)
        self.sequence_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ffcc;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        right_col.addWidget(self.sequence_viewer)

        actions_row = QHBoxLayout()
        self.play_btn = QPushButton("Play DNA")
        self.play_btn.setMinimumHeight(40)
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_selected)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMinimumHeight(40)
        self.delete_btn.setStyleSheet("background-color: #cc0000; color: white;")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)

        actions_row.addWidget(self.play_btn)
        actions_row.addWidget(self.delete_btn)
        right_col.addLayout(actions_row)

        # Assemble layout
        layout.addLayout(left_col, 1)
        layout.addLayout(right_col, 2)

    def load_bank(self):
        """Loads items from SQLite and populates the list widget."""
        self.list_widget.clear()
        self.sequence_viewer.clear()
        self.details_label.setText("Select a sound to view DNA.")
        self.play_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        try:
            sequences = self.db.get_all_sequences()
            for seq in sequences:
                item = QListWidgetItem(f"{seq['name']} (ID: {seq['id']})")
                item.setData(Qt.UserRole, seq)
                self.list_widget.addItem(item)
        except Exception as e:
            logger.error(f"Failed to load bank: {e}")

    def on_item_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.play_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
            
        item = items[0]
        seq_data = item.data(Qt.UserRole)
        
        self.details_label.setText(f"Name: {seq_data['name']} | Created: {seq_data['created_at']}")
        self.sequence_viewer.setText(json.dumps(seq_data['sequence'], indent=2))
        
        self.play_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def play_selected(self):
        items = self.list_widget.selectedItems()
        if not items: return
        
        seq_data = items[0].data(Qt.UserRole)
        seq_json_str = json.dumps(seq_data['sequence'])
        
        self.play_btn.setEnabled(False)
        self.play_btn.setText("Synthesizing...")
        
        self.current_thread = SynthesizerThread(seq_json_str)
        self.current_thread.finished_signal.connect(self.on_synth_finished)
        self.current_thread.error_signal.connect(self.on_synth_error)
        self.current_thread.start()

    def on_synth_finished(self, audio_data):
        self.play_btn.setEnabled(True)
        self.play_btn.setText("Play DNA")
        try:
            sd.play(audio_data, samplerate=44100)
        except Exception as e:
            logger.error(f"Playback failed: {e}")
        self.current_thread.deleteLater()

    def on_synth_error(self, error_msg):
        self.play_btn.setEnabled(True)
        self.play_btn.setText("Play DNA")
        QMessageBox.critical(self, "Synthesis Error", error_msg)
        self.current_thread.deleteLater()

    def delete_selected(self):
        items = self.list_widget.selectedItems()
        if not items: return
        
        seq_data = items[0].data(Qt.UserRole)
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     f"Are you sure you want to delete '{seq_data['name']}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.db.delete_sequence(seq_data['id']):
                self.load_bank()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete from database.")

    def showEvent(self, event):
        """Refresh list automatically when the panel is shown."""
        super().showEvent(event)
        self.load_bank()
