import os
import numpy as np
from utils.dna_calculator import DNACalculator
from utils.generative_engine import GenerativeEngine
from scipy.io.wavfile import write as write_wav

def test_generation():
    calc = DNACalculator('rules')
    engine = GenerativeEngine()

    # Test Volume DNA
    dna_vol = "VOL08900750712"
    parsed_vol = calc.parse(dna_vol)
    audio_vol = engine.generate(parsed_vol)
    assert len(audio_vol) > 0
    write_wav("test_vol.wav", 44100, (audio_vol * 32767).astype(np.int16))
    print(f"Generated test_vol.wav from {dna_vol}")

    # Test Frequency DNA
    dna_fre = "FREZ00440P0000000Z0000"
    parsed_fre = calc.parse(dna_fre)
    audio_fre = engine.generate(parsed_fre)
    assert len(audio_fre) > 0
    write_wav("test_fre.wav", 44100, (audio_fre * 32767).astype(np.int16))
    print(f"Generated test_fre.wav from {dna_fre}")

if __name__ == "__main__":
    test_generation()
