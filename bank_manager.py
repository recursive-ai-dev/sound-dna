#!/usr/bin/env python3
"""
bank_manager.py

CLI tool for SonicDNA to:
1. Encode an audio file and save it to the SQLite bank.
2. Generate a novel, randomized DNA sequence that is not in the bank, and synthesize it.
"""

import os
import sys
import argparse
import logging
import soundfile as sf

from utils.dna_db import DNADatabase
from utils.dna_extractor import AudioAnalyzer
from utils.dna_calculator import DNACalculator
from utils.dna_randomizer import DNARandomizer
from utils.generative_engine import GenerativeEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("BankManager")

def encode_audio(args):
    """Encodes an audio file and saves its DNA to the bank."""
    input_wav = args.input
    name = args.name
    
    if not os.path.exists(input_wav):
        logger.error(f"Input file not found: {input_wav}")
        return

    logger.info(f"Extracting DNA from {input_wav}...")
    analyzer = AudioAnalyzer()
    
    try:
        dna_sequence = analyzer.analyze_file(input_wav)
    except Exception as e:
        logger.error(f"Failed to analyze audio: {e}")
        return
        
    db = DNADatabase()
    
    if db.save_sequence(name, dna_sequence):
        logger.info(f"Successfully saved '{name}' to bank. ({len(dna_sequence)} frames)")
    else:
        logger.info(f"Did not save '{name}'. The sequence already exists in the bank.")

def generate_novel(args):
    """Generates a novel DNA sequence, saves it, and synthesizes to wav."""
    output_wav = args.output
    name = args.name
    frames = args.frames
    
    db = DNADatabase()
    calc = DNACalculator()
    randomizer = DNARandomizer(calc)
    
    logger.info("Generating a completely novel DNA sequence...")
    try:
        novel_seq = randomizer.generate_novel_sequence(db, num_frames=frames)
    except Exception as e:
        logger.error(f"Failed to generate novel sequence: {e}")
        return
        
    logger.info(f"Generated novel sequence of {len(novel_seq)} frames.")
    
    # Save it to the bank so it's documented
    db.save_sequence(name, novel_seq)
    
    # Synthesize it
    logger.info("Parsing novel DNA and synthesizing audio...")
    parsed_seq = []
    for frame_idx, frame_strings in enumerate(novel_seq):
        parsed_frame = {}
        for prefix, raw_dna in frame_strings.items():
            try:
                parsed_frame[prefix] = calc.parse(raw_dna)
            except Exception as e:
                logger.error(f"Failed to parse {raw_dna}: {e}")
        parsed_seq.append(parsed_frame)
        
    engine = GenerativeEngine()
    audio_out = engine.generate_from_sequence(parsed_seq)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    sf.write(output_wav, audio_out, engine.sample_rate)
    
    logger.info(f"Synthesized novel audio saved to {output_wav}")

def main():
    parser = argparse.ArgumentParser(description="SonicDNA Database Bank Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Encode Subcommand
    parser_encode = subparsers.add_parser('encode', help="Encode audio and save to bank")
    parser_encode.add_argument("input", help="Path to input audio (.wav)")
    parser_encode.add_argument("name", help="Name for this sound in the bank")
    
    # Novel Subcommand
    parser_novel = subparsers.add_parser('novel', help="Generate a random novel sound not in bank")
    parser_novel.add_argument("output", help="Path to save output audio (.wav)")
    parser_novel.add_argument("--name", default="random_novel", help="Name to save in the bank")
    parser_novel.add_argument("--frames", type=int, default=20, help="Number of 100ms frames to generate")
    
    args = parser.parse_args()
    
    if args.command == 'encode':
        encode_audio(args)
    elif args.command == 'novel':
        generate_novel(args)

if __name__ == "__main__":
    main()
