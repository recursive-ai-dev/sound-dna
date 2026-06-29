# SonicDNA

A project for developing a structured data driven approach to audio representation and generative synthesis.

## Project Status: Rule Definition Phase

June 2025 Update:
- All primary variable rules and serialization formats (rules_*.json) are now specified.
- Work on agent scripts audio encoding and the generative engine will continue next.

## Overview

SonicDNA is an experiment in:
- Efficient structured encoding of sound properties
- Data driven generative audio with an emphasis on clear modular rules
- Flexible tools (GUI CLI batch) for analysis and experimentation

## Current State

- [x] Modular folder structure
- [x] Basic PySide6 GUI skeleton
- [x] Audio DNA variable rulesets (rules_*.json)
- [ ] Audio DNA extraction agents planned
- [ ] DNA to audio generative engine planned
- [ ] Rule based validation and dataset building planned
- [ ] Audio compression experiments planned

## Audio DNA Rulesets

All major audio variables are defined in JSON rulesets:
- Volume
- Frequency
- Clarity
- Timbre
- Envelope
- Dynamics
- Emotion
- Macro Intensity
- Perceived Pitch
- Noise Texture
- Wavelength
- Texture Complexity
- Harmonicity
- Transients
- Phase Spatial
- Resonance Damping
- Glide Slur
- Effect Artifact
- Formant Structure

Each JSON file:
- Specifies encoding and decoding structure for a core property
- Documents sub variables ranges padding and serialization
- Will be used by agents for extraction validation and synthesis

## Getting Involved

If you have ideas or feedback please reach out:
- Email: birchstagstudios@gmail.com
- You are welcome to watch fork or experiment with your own designs

## License

MIT or other as specified

## Changelog

2025-06-02
- Refactored imports so that dna_ui and dna_calculator live under utils
- Modified dna_ui to compute project_root using the repository root
- Updated main.py import to point at utils.dna_ui
- Added __init__.py in utils and ui to treat them as packages
- Added py_modules in setup.py so that the console script entry point loads main.py
- Overhauled README.md for clarity and simplicity

Thank you for your interest in this project.
