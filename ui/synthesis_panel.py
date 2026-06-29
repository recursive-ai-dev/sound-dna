import json
import logging
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QFileDialog, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal
from utils.generative_engine import GenerativeEngine
from utils.dna_calculator import DNACalculator
from utils.dna_randomizer import DNARandomizer
from utils.dna_db import DNADatabase

logger = logging.getLogger("SynthesisPanel")

class SynthesizerThread(QThread):
    finished_signal = Signal(np.ndarray)
    error_signal = Signal(str)

    def __init__(self, json_sequence_str: str):
        super().__init__()
        self.json_sequence_str = json_sequence_str
        self.engine = GenerativeEngine()
        self.calc = DNACalculator()

    def run(self):
        try:
            seq_list = json.loads(self.json_sequence_str)
            if not isinstance(seq_list, list):
                raise ValueError("DNA Sequence must be a JSON array of frames.")
                
            parsed_seq = []
            for frame in seq_list:
                parsed_frame = {}
                for prefix, dna_str in frame.items():
                    parsed_frame[prefix] = self.calc.parse(dna_str)
                parsed_seq.append(parsed_frame)
                
            audio_out = self.engine.generate_from_sequence(parsed_seq)
            self.finished_signal.emit(audio_out)
        except json.JSONDecodeError as e:
            self.error_signal.emit(f"Invalid JSON format. Please ensure you provided a valid JSON array.\nDetails: {e}")
        except Exception as e:
            self.error_signal.emit(str(e))


class SynthesisPanel(QWidget):
    """
    Panel for manual DNA editing, novel generation, and synthesis.
    """
    def __init__(self) -> None:
        super().__init__()
        self.current_audio = None
        self.db = DNADatabase()
        self.calc = DNACalculator()
        self.randomizer = DNARandomizer(self.calc)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("DNA Synthesizer")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #fff;")
        layout.addWidget(header)

        # Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Paste a JSON array of DNA frames here, or click 'Generate Novel'...")
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ff9900;
                font-family: 'Consolas', 'Courier New', monospace;
                padding: 10px;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.editor, 1)

        # Controls
        controls_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("Generate Novel Sequence")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self.generate_novel)
        
        frames_label = QLabel("Frames:")
        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(1, 100)
        self.frames_spin.setValue(20)
        self.frames_spin.setMinimumHeight(40)

        self.synth_play_btn = QPushButton("Synthesize & Play")
        self.synth_play_btn.setMinimumHeight(40)
        self.synth_play_btn.clicked.connect(self.synthesize)
        
        self.export_btn = QPushButton("Export WAV")
        self.export_btn.setMinimumHeight(40)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_wav)

        controls_layout.addWidget(self.generate_btn)
        controls_layout.addWidget(frames_label)
        controls_layout.addWidget(self.frames_spin)
        controls_layout.addStretch()
        controls_layout.addWidget(self.synth_play_btn)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)
        
    def generate_novel(self):
        try:
            novel_seq = self.randomizer.generate_novel_sequence(self.db, num_frames=self.frames_spin.value())
            self.editor.setText(json.dumps(novel_seq, indent=2))
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def synthesize(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
            
        self.synth_play_btn.setEnabled(False)
        self.synth_play_btn.setText("Synthesizing...")
        
        self.thread = SynthesizerThread(text)
        self.thread.finished_signal.connect(self.on_synth_finished)
        self.thread.error_signal.connect(self.on_synth_error)
        self.thread.start()

    def on_synth_finished(self, audio_data):
        self.current_audio = audio_data
        self.synth_play_btn.setEnabled(True)
        self.synth_play_btn.setText("Synthesize & Play")
        self.export_btn.setEnabled(True)
        
        # Play the audio
        try:
            sd.play(audio_data, samplerate=44100)
        except Exception as e:
            logger.error(f"Playback failed: {e}")
        self.thread.deleteLater()

    def on_synth_error(self, error_msg):
        self.synth_play_btn.setEnabled(True)
        self.synth_play_btn.setText("Synthesize & Play")
        QMessageBox.critical(self, "Synthesis Error", error_msg)
        self.thread.deleteLater()

    def export_wav(self):
        if self.current_audio is None:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export WAV", "synthesized_dna.wav", "WAV Files (*.wav)")
        if path:
            try:
                audio_int16 = (self.current_audio * 32767).astype(np.int16)
                write_wav(path, 44100, audio_int16)
                QMessageBox.information(self, "Exported", f"Successfully exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save WAV: {e}")
