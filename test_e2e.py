#!/usr/bin/env python3
"""
test_e2e.py

End-to-End Test for SonicDNA Extraction and Synthesis.
1. Generates a test audio tone (sine wave, fading out).
2. Extracts its SonicDNA using AudioAnalyzer.
3. Parses the extracted DNA strings.
4. Synthesizes a new audio file from the DNA sequence using GenerativeEngine.
"""

import os
import sys
import numpy as np
import soundfile as sf
import logging

from utils.dna_extractor import AudioAnalyzer
from utils.generative_engine import GenerativeEngine
from utils.dna_calculator import DNACalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("End2EndTest")

def generate_test_audio(filepath: str, sample_rate: int = 44100, duration: float = 2.0):
    """Generate a 440Hz sine wave fading out over the duration."""
    logger.info(f"Generating test audio at {filepath}")
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Generate 440 Hz sine wave
    wave = np.sin(2 * np.pi * 440.0 * t)
    
    # Linear fade out envelope
    envelope = np.linspace(1.0, 0.0, len(t))
    wave = wave * envelope
    
    # Save as wav
    sf.write(filepath, wave, sample_rate)

def main():
    # Setup paths
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    input_wav = os.path.join(data_dir, 'test_input.wav')
    output_wav = os.path.join(data_dir, 'test_output.wav')
    
    sr = 44100
    hop_length = 4410 # 100ms per frame
    
    # 1. Generate test audio
    generate_test_audio(input_wav, sr, 2.0)
    
    # 2. Extract DNA from audio
    logger.info("Extracting SonicDNA from test audio...")
    analyzer = AudioAnalyzer(sample_rate=sr, hop_length=hop_length)
    dna_strings_seq = analyzer.analyze_file(input_wav)
    
    logger.info(f"Extracted {len(dna_strings_seq)} frames.")
    if len(dna_strings_seq) > 0:
        logger.info(f"First frame: {dna_strings_seq[0]}")
        logger.info(f"Last frame: {dna_strings_seq[-1]}")
        
    # 3. Parse the DNA strings back to nested dicts
    logger.info("Parsing DNA strings...")
    calculator = DNACalculator()
    parsed_seq = []
    
    for frame_idx, frame_strings in enumerate(dna_strings_seq):
        parsed_frame = {}
        for prefix, raw_dna in frame_strings.items():
            try:
                parsed_frame[prefix] = calculator.parse(raw_dna)
            except Exception as e:
                logger.error(f"Failed to parse {raw_dna} in frame {frame_idx}: {e}")
        parsed_seq.append(parsed_frame)
        
    # 4. Generate audio from parsed DNA
    logger.info("Synthesizing audio from SonicDNA sequence...")
    engine = GenerativeEngine(sample_rate=sr, hop_length=hop_length)
    output_audio = engine.generate_from_sequence(parsed_seq)
    
    # Save the output
    logger.info(f"Saving synthesized audio to {output_wav}")
    sf.write(output_wav, output_audio, sr)
    
    logger.info("E2E Test complete!")

if __name__ == "__main__":
    main()
