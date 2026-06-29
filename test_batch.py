import os
import json
from utils.dna_ui import main as run_batch

def test_batch():
    os.makedirs('data/raw', exist_ok=True)
    with open('data/raw/toSequence.txt', 'w') as f:
        f.write("VOL08900750712\n")
        f.write("FREZ18750P0250120Z0045\n")

    run_batch()

    out_path = 'data/output/toSequence_parsed.json'
    if os.path.exists(out_path):
        with open(out_path, 'r') as f:
            data = json.load(f)
            print(f"Parsed {len(data)} entries.")
            for entry in data:
                print(f"DNA: {entry['dna']} -> Rule: {entry['rule']}")
    else:
        print("Output file not found!")

if __name__ == "__main__":
    test_batch()
