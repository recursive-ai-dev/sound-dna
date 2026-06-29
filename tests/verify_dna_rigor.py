import os
import json
import unittest
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.dna_calculator import DNACalculator

class TestDNARigor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We assume we are in the tests/ directory
        cls.rules_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rules'))
        cls.calc = DNACalculator(cls.rules_dir)

    def test_bijective_integrity(self):
        """
        Tests that every rule's example structure can be parsed and then
        serialized back to the exact same string. This ensures the parser
        and serializer are perfect inverses (bijective).
        """
        for filename in os.listdir(self.rules_dir):
            if not filename.endswith('.json'):
                continue

            with self.subTest(filename=filename):
                filepath = os.path.join(self.rules_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    rule_def = json.load(f)

                variable = rule_def.get('variable')
                dna_example = rule_def.get('structure')

                if not dna_example:
                    self.skipTest(f"Rule {variable} has no example structure.")

                # Step 1: Parse
                try:
                    parsed_result = self.calc.parse(dna_example)
                except Exception as e:
                    self.fail(f"Failed to parse example for {variable}: {e}")

                # Step 2: Serialize
                try:
                    serialized = self.calc.serialize(parsed_result['rule'], parsed_result['values'])
                except Exception as e:
                    self.fail(f"Failed to serialize parsed result for {variable}: {e}")

                # Step 3: Compare
                self.assertEqual(dna_example, serialized,
                                 f"Bijective failure for {variable}. "
                                 f"Expected '{dna_example}', got '{serialized}'.")

if __name__ == "__main__":
    unittest.main(verbosity=2)
