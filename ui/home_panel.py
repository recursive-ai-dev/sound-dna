from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt

class HomePanel(QWidget):
    """
    Home and Documentation Panel.
    Provides an introduction and a user guide for SonicDNA Studio.
    """
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 14px;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        # HTML Content
        html_content = """
        <h1>Welcome to SonicDNA Studio</h1>
        <p>SonicDNA is a framework that extracts, serializes, and synthesizes audio into deterministic, hex-like <b>DNA</b> structures. Instead of storing complex wave arrays, we can define entire soundscapes through 19 core variables.</p>
        <hr>
        <h2>How to use this Studio</h2>
        <ul>
            <li><b>Extraction</b>: Encode existing <code>.wav</code> audio files into standard SonicDNA strings. The app will track the pitch, volume envelope, and timbre of the file and save the resulting frames into your Bank.</li>
            <li><b>Synthesis</b>: The ultimate control station. Paste SonicDNA strings, edit them manually, or use the <i>Novel Generator</i> to randomize completely unique sounds, and hear them instantly synthesized by the Generative Engine.</li>
            <li><b>Bank</b>: A SQLite database that stores your encoded and generated sounds. Keep track of sequences here, export them, or discard them.</li>
        </ul>
        <hr>
        <h2>The Core Rules</h2>
        <p>SonicDNA frames are built out of JSON rules. Here are the three most important rules in the engine right now:</p>
        <ol>
            <li><b>Volume (VOL)</b>: Controls the absolute amplitude and left/right panning of the sound.</li>
            <li><b>Frequency (FRE)</b>: Controls the fundamental pitch (e.g., 440Hz), FM modulation rate, and phase shifting.</li>
            <li><b>Timbre (TIM)</b>: The spectral centroid (brightness) of the sound, dictating the cutoff frequency of lowpass filters.</li>
        </ol>
        <p>You can view and modify these rules in the <code>rules/</code> directory. The engine will dynamically adapt to any schema changes you make!</p>
        """
        
        self.browser.setHtml(html_content)
        layout.addWidget(self.browser)
