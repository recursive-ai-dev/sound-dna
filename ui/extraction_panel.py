import json
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QTextEdit, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from utils.dna_extractor import AudioAnalyzer
from utils.dna_db import DNADatabase

logger = logging.getLogger("ExtractionPanel")

class ExtractorThread(QThread):
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.analyzer = AudioAnalyzer()

    def run(self):
        try:
            sequence = self.analyzer.analyze_file(self.filepath)
            self.finished_signal.emit(sequence)
        except Exception as e:
            self.error_signal.emit(str(e))


class ExtractionPanel(QWidget):
    """
    Panel for selecting a .wav file, extracting DNA sequences, and saving to the bank.
    """
    def __init__(self) -> None:
        super().__init__()
        self.current_sequence = None
        self.db = DNADatabase()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Audio Extractor")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #fff;")
        layout.addWidget(header)

        # File Selection Row
        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected.")
        self.file_label.setStyleSheet("color: #aaa;")
        
        self.select_btn = QPushButton("Select .wav File")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self.select_file)
        
        file_row.addWidget(self.select_btn)
        file_row.addWidget(self.file_label, 1)
        layout.addLayout(file_row)

        # Output Area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Extracted DNA sequence will appear here...")
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ffcc;
                font-family: 'Consolas', 'Courier New', monospace;
                padding: 10px;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.output_text, 1)

        # Save to Bank Row
        save_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter a name for the bank...")
        self.name_input.setMinimumHeight(40)
        
        self.save_btn = QPushButton("Save to Bank")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_to_bank)
        
        save_row.addWidget(self.name_input, 1)
        save_row.addWidget(self.save_btn)
        layout.addLayout(save_row)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "WAV Files (*.wav)")
        if path:
            self.file_label.setText(path)
            self.output_text.setText("Extracting DNA, please wait...\nThis might take a few moments for pitch tracking.")
            self.save_btn.setEnabled(False)
            self.select_btn.setEnabled(False)
            
            self.thread = ExtractorThread(path)
            self.thread.finished_signal.connect(self.on_extraction_finished)
            self.thread.error_signal.connect(self.on_extraction_error)
            self.thread.start()

    def on_extraction_finished(self, sequence):
        self.select_btn.setEnabled(True)
        self.current_sequence = sequence
        
        pretty_json = json.dumps(sequence, indent=2)
        self.output_text.setText(pretty_json)
        self.save_btn.setEnabled(True)
        QMessageBox.information(self, "Success", f"Extraction complete! Extracted {len(sequence)} frames.")
        self.thread.deleteLater()

    def on_extraction_error(self, error_msg):
        self.select_btn.setEnabled(True)
        self.output_text.setText(f"Error extracting DNA:\n{error_msg}")
        QMessageBox.critical(self, "Error", f"Failed to extract DNA:\n{error_msg}")
        self.thread.deleteLater()

    def save_to_bank(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name before saving.")
            return
            
        if self.current_sequence:
            success = self.db.save_sequence(name, self.current_sequence)
            if success:
                QMessageBox.information(self, "Saved", f"'{name}' was successfully saved to the bank.")
                self.name_input.clear()
            else:
                QMessageBox.warning(self, "Duplicate", f"A sequence identical to '{name}' already exists in the bank.")
