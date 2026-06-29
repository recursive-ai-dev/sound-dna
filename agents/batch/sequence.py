#!/usr/bin/env python3
"""
sequence.py

Agent for monitoring WAV files and performing automated DNA extraction/validation.
Integrates with LM Studio for AI-driven analysis.
"""

import time
import os
import requests
import logging
import numpy as np
from scipy.io import wavfile
from typing import Optional, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.lmstudio_tool import LMStudioTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("SequenceAgent")

# Configuration from environment or defaults
RAW_DIR = os.getenv("SONICDNA_RAW_DIR", os.path.abspath("data/raw"))
LM_STUDIO_API_URL = os.getenv("LM_STUDIO_API_URL", "http://localhost:1234")
MODEL_ID = os.getenv("LM_STUDIO_MODEL", "deepseek-r1-0528-qwen3-8b@q3_k_l")

def is_lm_studio_running() -> bool:
    """Check if the LM Studio local server is accessible."""
    try:
        r = requests.get(f"{LM_STUDIO_API_URL}/v1/models", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def load_model(model_id: str = MODEL_ID) -> bool:
    """Load the specified model in LM Studio via API."""
    try:
        logger.info(f"Loading model: {model_id}")
        resp = requests.post(
            f"{LM_STUDIO_API_URL}/v1/models/load",
            json={"model": model_id},
            timeout=30
        )
        if resp.status_code == 200:
            logger.info("Model loaded successfully!")
            return True
        else:
            logger.error(f"Error loading model: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while loading model: {e}")
        return False

class SequenceHandler(FileSystemEventHandler):
    """Handles file system events for new/modified audio files."""
    def __init__(self, lm_tool: Optional[LMStudioTool] = None):
        super().__init__()
        self.lm_tool = lm_tool

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".wav"):
            logger.info(f"New WAV detected: {event.src_path}")
            self.process_with_delay(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".wav"):
            logger.info(f"WAV modified: {event.src_path}")
            self.process_with_delay(event.src_path)

    def process_with_delay(self, file_path: str, delay: float = 1.5) -> None:
        """Wait for file stability before processing to avoid race conditions."""
        logger.info(f"Waiting {delay}s for file stability: {file_path}")
        time.sleep(delay)

        # Simple stability check: ensure file size is constant
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(0.5)
            size2 = os.path.getsize(file_path)
            if size1 == size2 and size1 > 0:
                self.process(file_path)
            else:
                logger.warning(f"File {file_path} is still being written. Skipping this event.")
        except OSError as e:
            logger.error(f"Could not access file {file_path}: {e}")

    def _analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """Extract basic acoustic features from WAV file."""
        try:
            fs, data = wavfile.read(file_path)
            if data.ndim > 1:
                data = data.mean(axis=1) # Mono

            # Normalize
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0

            # Features
            rms = np.sqrt(np.mean(data**2))

            # Spectral Centroid (simple approximation)
            fft = np.fft.rfft(data)
            freqs = np.fft.rfftfreq(len(data), 1.0/fs)
            magnitude = np.abs(fft)
            centroid = np.sum(magnitude * freqs) / np.sum(magnitude) if np.sum(magnitude) > 0 else 0

            return {
                "rms_amplitude": float(rms),
                "spectral_centroid_hz": float(centroid),
                "duration_sec": float(len(data) / fs)
            }
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return {}

    def process(self, file_path: str) -> None:
        """
        Analyze the audio file and extract SonicDNA using AI.
        """
        logger.info(f"Processing {file_path} for DNA extraction...")

        features = self._analyze_audio(file_path)
        if not features:
            return

        if not self.lm_tool:
            logger.warning("LM Studio tool not available. Using fallback DNA.")
            extracted_dna = "VOL05000500005"
        else:
            prompt = (
                f"Analyze these audio features: {features}. "
                "Generate a SonicDNA string for 'Volume' (VOL) and 'Frequency' (FRE). "
                "Volume format: VOL + amp(4) + lr(3) + sur(2) + head(2). "
                "Frequency format: FRE + root(letter+5) + micro(sign+3) + fm(4+letter+4). "
                "Provide ONLY the DNA strings, one per line."
            )
            try:
                response = self.lm_tool.ask(prompt)
                lines = response.splitlines()
                extracted_dna = ""
                for line in lines:
                    line = line.strip()
                    if line.startswith(("VOL", "FRE", "TIM")):
                        extracted_dna = line
                        break
                if not extracted_dna:
                     extracted_dna = "VOL05000500005" # Fallback
            except Exception as e:
                logger.error(f"AI Extraction failed: {e}")
                extracted_dna = "VOL05000500005"

        logger.info(f"Extracted DNA: {extracted_dna}")

        output_path = os.path.join(os.path.dirname(file_path), "toSequence.txt")
        try:
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(extracted_dna + "\n")
            logger.info(f"Appended DNA to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write extracted DNA: {e}")

def main() -> None:
    """Main agent execution loop."""
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR, exist_ok=True)

    logger.info(f"Watching directory: {RAW_DIR}")

    lm_tool = None
    if is_lm_studio_running():
        load_model()
        lm_tool = LMStudioTool(model=MODEL_ID)
    else:
        logger.warning(f"LM Studio not found at {LM_STUDIO_API_URL}. AI features will be limited.")

    event_handler = SequenceHandler(lm_tool=lm_tool)
    observer = Observer()
    observer.schedule(event_handler, path=RAW_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping observer...")
        observer.stop()
    except Exception as e:
        logger.error(f"Agent error: {e}")
        observer.stop()

    observer.join()
    logger.info("Agent exited.")

if __name__ == "__main__":
    main()
