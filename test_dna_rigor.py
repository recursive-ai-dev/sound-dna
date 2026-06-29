import os
import json
from utils.dna_calculator import DNACalculator

def test_rigor():
    calc = DNACalculator('rules')
    rules_dir = 'rules'

    for filename in os.listdir(rules_dir):
        if not filename.endswith('.json'):
            continue

        with open(os.path.join(rules_dir, filename), 'r') as f:
            rule_def = json.load(f)

        dna_example = rule_def.get('structure')
        if not dna_example:
            print(f"Skipping {filename} - no example structure")
            continue

        print(f"Testing {rule_def['variable']} ({dna_example})...")

        # Test Parse
        try:
            parsed = calc.parse(dna_example)
        except Exception as e:
            print(f"  [FAIL] Parse error: {e}")
            continue

        # Test Serialize
        try:
            serialized = calc.serialize(parsed['rule'], parsed['values'])
        except Exception as e:
            print(f"  [FAIL] Serialize error: {e}")
            continue

        if serialized == dna_example:
            print(f"  [PASS] Bijective integrity verified.")
        else:
            print(f"  [FAIL] Bijective mismatch!")
            print(f"    Original:   {dna_example}")
            print(f"    Serialized: {serialized}")
            print(f"    Parsed:     {parsed['values']}")

if __name__ == "__main__":
    test_rigor()
