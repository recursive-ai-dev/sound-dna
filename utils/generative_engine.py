#!/usr/bin/env python3
"""
generative_engine.py

Translates parsed SonicDNA structures into audio waveforms.
The engine acts as a stateful software synthesizer that can be modulated
over time by a sequence of DNA frames.
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional
import scipy.signal

# Configure logging
logger = logging.getLogger("GenerativeEngine")

class SynthVoice:
    """
    A stateful synthesizer voice with DAW-like variables (knobs).
    """
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.fm_phase = 0.0
        
        # DAW Knobs (State Variables)
        self.freq = 440.0
        self.amp = 0.0
        self.centroid = 500.0
        self.inharm = 0.0
        self.fm_depth = 0.0
        self.fm_rate = 0.0
        
    def update_parameters(self, dna_data: Dict[str, Any]):
        """
        Update the internal knobs based on parsed DNA variables.
        dna_data is a dictionary like: {'rule': 'Volume', 'values': {...}}
        We expect to receive flattened or parsed DNA.
        """
        rule_name = dna_data.get('rule')
        values = dna_data.get('values', {})
        
        if rule_name == 'Volume':
            self.amp = values.get('amp', 0) / 1000.0
        elif rule_name == 'Frequency':
            # Base freq
            root = values.get('root', {})
            hz = root.get('hz', 440)
            
            micro = values.get('micro', {})
            cents = micro.get('value', 0)
            if micro.get('sign') == 'N':
                cents = -cents
                
            raw_freq = hz * (2.0 ** (cents / 1200.0))
            # Protect against Nyquist aliasing
            self.freq = np.clip(raw_freq, 1.0, (self.sample_rate / 2.0) * 0.95)
            
            # FM
            fm = values.get('fm', {})
            self.fm_depth = fm.get('index', 0) / 100.0
            
            rate_char = fm.get('rate', 'Z')
            # 'Z' is slowest, 'A' is fastest.
            # Map Z-A to 1Hz - 200Hz for example
            rate_idx = max(0, ord('Z') - ord(rate_char))
            self.fm_rate = 1.0 + (rate_idx * 5.0)
            
        elif rule_name == 'Timbre':
            self.centroid = values.get('centroid', 500)
            self.inharm = values.get('inharm', 0) / 10.0

    def render_block(self, block_size: int) -> np.ndarray:
        """
        Render a block of audio of length block_size with the current parameters.
        """
        t = np.arange(block_size) / self.sample_rate
        
        # FM modulation
        modulator = self.fm_depth * np.sin(2 * np.pi * self.fm_rate * t + self.fm_phase)
        self.fm_phase += 2 * np.pi * self.fm_rate * (block_size / self.sample_rate)
        self.fm_phase = self.fm_phase % (2 * np.pi)
        
        # Carrier (Complex Timbre)
        wave = np.zeros(block_size)
        n_harmonics = 10
        for i in range(1, n_harmonics + 1):
            # Harmonics shifted by inharmonicity
            h_freq = self.freq * i * (1 + i * self.inharm * 0.01)
            
            if h_freq > self.sample_rate / 2:
                break
                
            # Spectral envelope shaping based on centroid (very simplistic)
            weight = max(0, 1.0 - abs(np.log2(h_freq / max(20, self.centroid))) * 0.3)
            wave += (weight / i) * np.sin(2 * np.pi * h_freq * t + modulator + self.phase * i)
            
        self.phase += 2 * np.pi * self.freq * (block_size / self.sample_rate)
        self.phase = self.phase % (2 * np.pi)
        
        # Apply amplitude envelope smoothing in a real synth, but here we step it
        wave = wave * self.amp
        return wave


class GenerativeEngine:
    """
    Core synthesis engine that maps a sequence of SonicDNA to audio.
    """
    def __init__(self, sample_rate: int = 44100, hop_length: int = 4410):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.voice = SynthVoice(sample_rate)

    def generate_from_sequence(self, parsed_dna_sequence: List[Dict[str, Any]]) -> np.ndarray:
        """
        Produce an audio buffer from a sequence of parsed DNA frames.
        """
        audio_blocks = []
        
        for frame in parsed_dna_sequence:
            for dna_prefix, dna_parsed in frame.items():
                if isinstance(dna_parsed, dict) and 'rule' in dna_parsed:
                    self.voice.update_parameters(dna_parsed)
            
            block = self.voice.render_block(self.hop_length)
            audio_blocks.append(block)
            
        if not audio_blocks:
            return np.zeros(0)
            
        audio_out = np.concatenate(audio_blocks)
        
        # Protect against inf/nan
        audio_out = np.nan_to_num(audio_out, nan=0.0, posinf=1.0, neginf=-1.0)
        
        # Apply a simple low-pass filter to smooth out block boundaries (zipper noise)
        b, a = scipy.signal.butter(1, 0.1)
        audio_out = scipy.signal.filtfilt(b, a, audio_out)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(audio_out))
        if max_val > 1e-6:
            audio_out = audio_out / max_val * 0.8
        else:
            audio_out = np.zeros_like(audio_out)
            
        return audio_out
