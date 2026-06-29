"""
music_panel.py

GUI panel for audio generation and visualization.
Includes a library of basic waveforms and noise types.
"""

import logging
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from scipy.signal import butter, lfilter
from typing import Optional, List, Any
from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QComboBox
)
from PySide6.QtGui import QPainter, QPen, QColor, QPaintEvent

# Configure logging
logger = logging.getLogger("MusicPanel")

SAMPLE_RATE = 44100
DURATION = 2.0
DEFAULT_FREQ = 440.0

BASE_SOUNDS = [
    "Sine Wave",
    "Square Wave",
    "Triangle Wave",
    "Sawtooth Wave",
    "Pulse Wave",
    "Supersaw",
    "Organ (Additive)",
    "Ring Modulated",
    "Impulse",
    "Click",
    "Burst",
    "DC Offset",
    "Silence",
    "Sample & Hold",
    "Stepped Random",
    "Linear Chirp",
    "White Noise",
    "Pink Noise",
    "Brown Noise",
    "Blue Noise",
    "Violet Noise",
    "Grey Noise"
]

def gen_wave(wave_type: str, frequency: float = DEFAULT_FREQ, volume: float = 0.8) -> np.ndarray:
    """
    Generate audio buffer based on wave type.
    Includes mathematically accurate noise generation.
    """
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)

    if wave_type == "Sine Wave":
        return volume * np.sin(2 * np.pi * frequency * t)

    elif wave_type == "Square Wave":
        return volume * np.sign(np.sin(2 * np.pi * frequency * t))

    elif wave_type == "Triangle Wave":
        return volume * (2 * np.abs(2 * ((t * frequency) % 1) - 1) - 1)

    elif wave_type == "Sawtooth Wave":
        return volume * (2 * ((t * frequency) % 1) - 1)

    elif wave_type == "Pulse Wave":
        pulse_width = 0.2
        return volume * np.where((t * frequency) % 1 < pulse_width, 1, -1)

    elif wave_type == "Supersaw":
        detune_factors = [0.98, 0.99, 1.0, 1.01, 1.02]
        sum_saws = sum(np.sin(2 * np.pi * frequency * d * t) for d in detune_factors)
        return volume * (sum_saws / len(detune_factors))

    elif wave_type == "Organ (Additive)":
        harmonics = [1, 2, 3, 4, 5]
        amps = [1.0, 0.5, 0.25, 0.13, 0.06]
        organ = sum(a * np.sin(2 * np.pi * frequency * h * t) for a, h in zip(amps, harmonics))
        return volume * (organ / sum(amps))

    elif wave_type == "Ring Modulated":
        mod_freq = 55.0
        return volume * np.sin(2 * np.pi * frequency * t) * np.sin(2 * np.pi * mod_freq * t)

    elif wave_type == "Impulse":
        data = np.zeros_like(t)
        data[0] = 1.0
        return volume * data

    elif wave_type == "Click":
        data = np.zeros_like(t)
        data[:int(0.002 * SAMPLE_RATE)] = 1.0
        return volume * data

    elif wave_type == "Burst":
        data = np.zeros_like(t)
        burst_len = int(0.1 * SAMPLE_RATE)
        data[:burst_len] = np.sin(2 * np.pi * frequency * t[:burst_len])
        return volume * data

    elif wave_type == "DC Offset":
        return volume * np.ones_like(t)

    elif wave_type == "Silence":
        return np.zeros_like(t)

    elif wave_type == "Sample & Hold":
        steps = 32
        step_len = len(t) // steps
        vals = np.random.uniform(-1, 1, steps)
        data = np.repeat(vals, step_len)
        if len(data) < len(t):
            data = np.pad(data, (0, len(t) - len(data)))
        return volume * data[:len(t)]

    elif wave_type == "Stepped Random":
        steps = 16
        idx = np.floor(np.linspace(0, steps, len(t), endpoint=False)).astype(int)
        vals = np.random.uniform(-1, 1, steps + 1)
        return volume * vals[idx]

    elif wave_type == "Linear Chirp":
        f0, f1 = 220.0, 1760.0
        phase = 2 * np.pi * (f0 * t + 0.5 * (f1 - f0) * t**2 / DURATION)
        return volume * np.sin(phase)

    elif wave_type == "White Noise":
        return volume * np.random.uniform(-1, 1, len(t))

    elif wave_type == "Pink Noise":
        num_rows = 16
        array = np.random.randn(num_rows, len(t))
        for i in range(1, num_rows):
            step = 2**i
            for j in range(0, len(t), step):
                array[i, j:j+step] = array[i, j]
        pink = np.sum(array, axis=0)
        return volume * (pink / np.max(np.abs(pink)))

    elif wave_type == "Brown Noise":
        wn = np.random.uniform(-1, 1, len(t))
        brown = np.cumsum(wn)
        return volume * (brown / np.max(np.abs(brown)))

    elif wave_type == "Blue Noise":
        white = np.random.normal(0, 1, len(t))
        blue = np.diff(white, prepend=0)
        return volume * (blue / np.max(np.abs(blue)))

    elif wave_type == "Violet Noise":
        white = np.random.normal(0, 1, len(t))
        violet = np.diff(white, n=2, prepend=[0, 0])
        return volume * (violet / np.max(np.abs(violet)))

    elif wave_type == "Grey Noise":
        # Approximating Grey Noise using A-weighting curve filter on White Noise
        white = np.random.normal(0, 1, len(t))
        # Simple Butterworth bandpass to simulate human hearing sensitivity
        b, a_coeff = butter(2, [1000 / (SAMPLE_RATE/2), 8000 / (SAMPLE_RATE/2)], btype='band')
        grey = lfilter(b, a_coeff, white)
        return volume * (grey / np.max(np.abs(grey)))

    else:
        return np.zeros_like(t)

class WaveformWidget(QWidget):
    """Visualizes the current audio buffer."""
    def __init__(self) -> None:
        super().__init__()
        self.data: np.ndarray = np.zeros(512)
        self.setMinimumHeight(200)

    def set_wave(self, data: np.ndarray) -> None:
        """Update the visualization data."""
        if len(data) > 512:
            self.data = data[:512]
        else:
            self.data = np.pad(data, (0, max(0, 512 - len(data))))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(event.rect(), Qt.black)

        w, h = self.width(), self.height()
        mid_y = h // 2

        qp.setPen(QPen(QColor(40, 40, 40), 1, Qt.DashLine))
        qp.drawLine(0, mid_y, w, mid_y)

        pen = QPen(QColor(0, 255, 200), 2)
        qp.setPen(pen)

        n_samples = len(self.data)
        if n_samples < 2:
            return

        points = []
        for i in range(n_samples):
            x = i * w / (n_samples - 1)
            y = mid_y - self.data[i] * (h // 2 - 20)
            points.append((x, y))

        for i in range(len(points) - 1):
            qp.drawLine(int(points[i][0]), int(points[i][1]),
                        int(points[i+1][0]), int(points[i+1][1]))

class MusicPanel(QWidget):
    """Interactive panel for audio experimentation."""
    def __init__(self) -> None:
        super().__init__()
        self.current_wave: Optional[np.ndarray] = None
        self.is_playing: bool = False

        layout = QVBoxLayout(self)

        controls_layout = QHBoxLayout()
        self.sound_selector = QComboBox()
        self.sound_selector.addItems(BASE_SOUNDS)

        controls_layout.addWidget(QLabel("Base Waveform:"))
        controls_layout.addWidget(self.sound_selector)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        self.waveform_vis = WaveformWidget()
        layout.addWidget(self.waveform_vis)

        btns_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.setMinimumHeight(40)

        self.download_btn = QPushButton("Export WAV")
        self.download_btn.setMinimumHeight(40)

        btns_layout.addWidget(self.play_btn)
        btns_layout.addWidget(self.download_btn)
        layout.addLayout(btns_layout)

        self.sound_selector.currentTextChanged.connect(self.update_waveform)
        self.play_btn.clicked.connect(self.toggle_play)
        self.download_btn.clicked.connect(self.export_wav)

        self.update_waveform()

    def update_waveform(self) -> None:
        """Regenerate waveform when selection changes."""
        wave_type = self.sound_selector.currentText()
        try:
            self.current_wave = gen_wave(wave_type)
            self.waveform_vis.set_wave(self.current_wave)
        except Exception as e:
            logger.error(f"Error generating waveform '{wave_type}': {e}")

        if self.is_playing:
            self.stop_audio()

    def toggle_play(self) -> None:
        """Start or stop audio playback."""
        if self.is_playing:
            self.stop_audio()
        else:
            self.start_audio()

    def start_audio(self) -> None:
        if self.current_wave is None:
            return
        try:
            self.is_playing = True
            self.play_btn.setText("Stop")
            sd.play(self.current_wave, samplerate=SAMPLE_RATE)
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self.is_playing = False
            self.play_btn.setText("Play")

    def stop_audio(self) -> None:
        self.is_playing = False
        self.play_btn.setText("Play")
        sd.stop()

    def export_wav(self) -> None:
        """Save the current waveform to a file."""
        if self.current_wave is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Waveform", "sonic_dna_sample.wav", "WAV Files (*.wav)"
        )
        if path:
            try:
                audio_int16 = (self.current_wave * 32767).astype(np.int16)
                write_wav(path, SAMPLE_RATE, audio_int16)
                logger.info(f"Exported WAV to {path}")
            except Exception as e:
                logger.error(f"Failed to export WAV: {e}")
