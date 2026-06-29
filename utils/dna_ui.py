#!/usr/bin/env python3
"""
dna_ui.py

Batch processor for SonicDNA strings. Reads from data/raw,
outputs JSON and CSV to data/output.
"""

import os
import json
import csv
import logging
from typing import List, Dict, Any, Set
from utils.dna_calculator import DNACalculator, RuleParseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("DNA_UI")

def ensure_folder(path: str) -> None:
    """Create the folder if it doesn’t exist."""
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def read_input_file(input_path: str) -> List[str]:
    """
    Reads a file; each line is one DNA string.
    Returns a list of DNA strings (stripped, non-empty).
    """
    dna_list: List[str] = []
    if not os.path.isfile(input_path):
        return dna_list
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s:
                    dna_list.append(s)
    except Exception as e:
        logger.error(f"Failed to read input file {input_path}: {e}")
    return dna_list

def flatten_parsed(rule_name: str, values_dict: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
    """
    Given nested values_dict, flatten into { 'rule.sub1.sub2': value, ... }.
    Useful for CSV.
    """
    items: Dict[str, Any] = {}
    for k, v in values_dict.items():
        new_key = f"{parent_key}.{k}" if parent_key else f"{rule_name}.{k}"
        if isinstance(v, dict):
            items.update(flatten_parsed(rule_name, v, new_key))
        else:
            items[new_key] = v
    return items

def main() -> None:
    """Main batch processing execution."""
    # Determine file paths relative to this script's location
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_folder = os.path.join(script_dir, 'data', 'raw')
    output_folder = os.path.join(script_dir, 'data', 'output')
    rules_folder = os.path.join(script_dir, 'rules')

    ensure_folder(output_folder)

    # 1. Check for work file (atomic snapshot) first, then falling back to standard input
    work_file = os.path.join(raw_folder, 'work', 'toSequence.txt')
    standard_input = os.path.join(raw_folder, 'toSequence.txt')

    input_file = work_file if os.path.isfile(work_file) else standard_input

    if not os.path.isfile(input_file):
        logger.debug(f"No input file found at {input_file}. Nothing to process.")
        return

    # Instantiate calculator
    try:
        calculator = DNACalculator(rules_folder=rules_folder)
    except Exception as e:
        logger.error(f"Could not load rules: {e}")
        return

    # Read DNA strings
    dna_list = read_input_file(input_file)
    if not dna_list:
        logger.info(f"Input file {input_file} is empty.")
        return

    # Prepare outputs
    parsed_json: List[Dict[str, Any]] = []
    csv_rows: List[Dict[str, Any]] = []
    all_flattened_keys: Set[str] = set()

    for dna_str in dna_list:
        try:
            result = calculator.parse(dna_str)
            entry = {
                'dna': dna_str,
                'rule': result['rule'],
                'parsed': result['values']
            }
            parsed_json.append(entry)

            # Flatten for CSV
            flat = flatten_parsed(result['rule'], result['values'])
            flat['dna'] = dna_str
            flat['rule'] = result['rule']
            csv_rows.append(flat)
            all_flattened_keys.update(flat.keys())

        except RuleParseError as e:
            logger.warning(f"Parse error for DNA '{dna_str}': {e}")
            # On parse error, record as error entry
            parsed_json.append({
                'dna': dna_str,
                'error': str(e)
            })
            # Also put a row in CSV listing error
            flat_err = {'dna': dna_str, 'error': str(e)}
            csv_rows.append(flat_err)
            all_flattened_keys.update(flat_err.keys())

    # 1) Write JSON output
    json_output_path = os.path.join(output_folder, 'toSequence_parsed.json')
    try:
        with open(json_output_path, 'w', encoding='utf-8') as jf:
            json.dump(parsed_json, jf, indent=2)
    except Exception as e:
        logger.error(f"Failed to write JSON output: {e}")

    # 2) Write CSV output
    csv_output_path = os.path.join(output_folder, 'toSequence_parsed.csv')
    fieldnames = sorted(list(all_flattened_keys))
    try:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            for row in csv_rows:
                # Ensure every field in fieldnames is present
                out = {k: row.get(k, '') for k in fieldnames}
                writer.writerow(out)
    except Exception as e:
        logger.error(f"Failed to write CSV output: {e}")

    logger.info(f"Successfully parsed {len(dna_list)} DNA strings from {input_file}.")

if __name__ == '__main__':
    main()
