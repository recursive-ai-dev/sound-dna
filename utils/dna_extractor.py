#!/usr/bin/env python3
"""
dna_extractor.py

Analyzes raw audio files using librosa and extracts features mapped to SonicDNA strings.
"""

import os
import sys
import numpy as np
import logging
from typing import List, Dict, Any, Tuple

try:
    import librosa
except ImportError:
    librosa = None
    logging.warning("librosa not found. Audio extraction requires librosa.")

# Add parent directory to path to allow importing utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.dna_calculator import DNACalculator

logger = logging.getLogger("DNA_Extractor")
logging.basicConfig(level=logging.INFO)

class AudioAnalyzer:
    """
    Extracts SonicDNA variables (Volume, Frequency, Timbre) from an audio file.
    """
    def __init__(self, sample_rate: int = 44100, hop_length: int = 4410):
        # hop_length 4410 at 44100Hz = 100ms frames
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.calculator = DNACalculator()

    def analyze_file(self, filepath: str) -> List[Dict[str, str]]:
        """
        Analyzes an audio file and returns a list of frames, where each frame
        is a dictionary mapping rule prefixes (e.g. 'VOL', 'FRE', 'TIM') to DNA strings.
        """
        if librosa is None:
            raise ImportError("librosa is required to analyze audio.")
            
        logger.info(f"Loading {filepath} ...")
        y, sr = librosa.load(filepath, sr=self.sample_rate, mono=True)
        
        # Calculate features over frames
        # 1. RMS Amplitude (Volume)
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        
        # 2. Fundamental Frequency (Pitch)
        # using pyin for better pitch tracking
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7'), 
            sr=self.sample_rate, 
            hop_length=self.hop_length,
            fill_na=0.0
        )
        
        # 3. Spectral Centroid (Timbre)
        centroid = librosa.feature.spectral_centroid(y=y, sr=self.sample_rate, hop_length=self.hop_length)[0]
        
        num_frames = min(len(rms), len(f0), len(centroid))
        dna_sequence = []
        
        # Guard against fully silent tracks causing divide by zero
        max_rms = np.max(rms)
        if max_rms < 1e-6 or np.isnan(max_rms):
            max_rms = 1.0
            
        # Clean NaNs from pyin output (occurs on silence)
        f0 = np.nan_to_num(f0, nan=0.0)
        centroid = np.nan_to_num(centroid, nan=20.0)
        rms = np.nan_to_num(rms, nan=0.0)
        
        for i in range(num_frames):
            frame_dna = {}
            
            # --- VOLUME ---
            # Map RMS to 0-1000 (0.1% resolution)
            amp_val = min(1000, max(0, int((rms[i] / max_rms) * 1000)))
            vol_dict = {
                'amp': amp_val,
                'lr': 50, # center
                'sur': 0, # mono
                'head': 12
            }
            try:
                frame_dna['VOL'] = self.calculator.serialize('Volume', vol_dict)
            except Exception as e:
                logger.error(f"Error serializing Volume: {e}")

            # --- FREQUENCY ---
            freq_val = f0[i]
            if freq_val > 0:
                hz = int(np.clip(freq_val, 20, (self.sample_rate / 2.0) * 0.95))
                # Band letter Z-A (simple heuristic based on log pitch)
                # Map 20Hz-20kHz to 26 letters roughly
                band_idx = int(np.clip((np.log2(hz / 20) / np.log2(20000 / 20)) * 25, 0, 25))
                band_char = chr(ord('Z') - band_idx)
                
                fre_dict = {
                    'root': {
                        'band': band_char,
                        'hz': hz
                    },
                    'micro': {
                        'sign': 'P',
                        'value': 0
                    },
                    'fm': {
                        'index': 0,
                        'rate': 'Z',
                        'links': 0
                    }
                }
                try:
                    frame_dna['FRE'] = self.calculator.serialize('Frequency', fre_dict)
                except Exception as e:
                    logger.error(f"Error serializing Frequency: {e}")

            # --- TIMBRE ---
            cent_val = int(np.clip(centroid[i], 20, (self.sample_rate / 2.0) * 0.95))
            tim_dict = {
                'centroid': cent_val,
                'inharm': 0,
                'texture': 'd',
                'blend': 1000
            }
            try:
                frame_dna['TIM'] = self.calculator.serialize('Timbre', tim_dict)
            except Exception as e:
                logger.error(f"Error serializing Timbre: {e}")
                
            dna_sequence.append(frame_dna)
            
        return dna_sequence

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        analyzer = AudioAnalyzer()
        try:
            seq = analyzer.analyze_file(filepath)
            for i, frame in enumerate(seq):
                print(f"Frame {i:04d}: {frame}")
        except Exception as e:
            print(f"Extraction failed: {e}")
    else:
        print("Usage: python dna_extractor.py <audio_file.wav>")
