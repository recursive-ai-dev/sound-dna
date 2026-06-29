import random
import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.dna_calculator import DNACalculator, Rule
from utils.dna_db import DNADatabase
import logging

logger = logging.getLogger("DNARandomizer")

class DNARandomizer:
    """
    Generates random valid SonicDNA structures by reading the JSON rulesets.
    """
    def __init__(self, calculator: DNACalculator):
        self.calculator = calculator

    def generate_random_dict(self, rule_name: str) -> Dict[str, Any]:
        """
        Given a rule name (e.g. 'Volume'), generate a valid random dictionary
        that can be passed to DNACalculator.serialize().
        """
        target_rule = None
        for rule in self.calculator.rules.values():
            if rule.variable == rule_name:
                target_rule = rule
                break
                
        if not target_rule:
            raise ValueError(f"Rule {rule_name} not found.")

        result = {}
        for subvar_name, subvar_schema in target_rule.plan:
            result[subvar_name] = self._randomize_subvar(target_rule, subvar_schema)
            
        return result

    def _randomize_subvar(self, rule: Rule, schema: Dict[str, Any]) -> Any:
        if 'description' in schema:
            return self._randomize_leaf(rule, schema)
            
        # Group
        group_res = {}
        for child_name, child_schema in schema.items():
            if isinstance(child_schema, dict):
                group_res[child_name] = self._randomize_subvar(rule, child_schema)
        return group_res

    def _randomize_leaf(self, rule: Rule, schema: Dict[str, Any]) -> Any:
        fields = rule._identify_fields(schema)
        results = {}
        
        for ftype, fkey, config in fields:
            if ftype == 'numeric':
                # Try to find min/max
                min_val = schema.get(f"{fkey}_min", schema.get("min", 0))
                # For some fields like frequency, max is huge, but we might want sensible defaults if max is missing
                # If padding is 4, max default could be 9999
                max_default = (10 ** int(config)) - 1
                max_val = schema.get(f"{fkey}_max", schema.get("max", max_default))
                
                # Sanitize types
                min_val = int(min_val)
                max_val = int(max_val)
                
                results[fkey] = random.randint(min_val, max_val)
                
            elif ftype == 'class':
                if isinstance(config, str) and ('-' in config or '–' in config):
                    delimiter = '–' if '–' in config else '-'
                    parts = config.split(delimiter)
                    if len(parts) == 2:
                        start, end = parts
                        start_code, end_code = ord(start), ord(end)
                        if start_code > end_code:
                            start_code, end_code = end_code, start_code
                        results[fkey] = chr(random.randint(start_code, end_code))
                    else:
                        results[fkey] = config
                else:
                    results[fkey] = str(config)
                    
            elif ftype == 'sign':
                if isinstance(config, str) and '/' in config:
                    options = config.split('/')
                else:
                    options = ['P', 'N']
                results[fkey] = random.choice(options)
                
        if len(results) == 1:
            return list(results.values())[0]
        return results

    def generate_novel_sequence(self, db: DNADatabase, num_frames: int = 20) -> List[Dict[str, str]]:
        """
        Generates a sequence of random frames that is guaranteed to be novel 
        (not in the database). Since the random space is massive, it's almost
        certainly novel on the first try.
        """
        # We focus on the core rules for playback: Volume, Frequency, Timbre
        core_rules = ["Volume", "Frequency", "Timbre"]
        
        for _ in range(10): # 10 attempts to find novel
            sequence = []
            
            # To make it sound somewhat musical, we can pick a base random state and slightly jitter it,
            # or just generate purely random for every frame. Pure random sounds like noise,
            # so let's do a random walk.
            
            # Init state
            state = {r: self.generate_random_dict(r) for r in core_rules}
            
            for _ in range(num_frames):
                frame_strs = {}
                for r in core_rules:
                    # Occasional jumps or drifts could be implemented here. 
                    # For now, we'll just re-randomize every frame to prove capability, 
                    # yielding a highly chaotic novel sound.
                    state[r] = self.generate_random_dict(r)
                    frame_strs[self.calculator.rules[[p for p, rl in self.calculator.rules.items() if rl.variable == r][0]].prefix] = self.calculator.serialize(r, state[r])
                sequence.append(frame_strs)
                
            if db.is_novel(sequence):
                return sequence
                
        raise RuntimeError("Failed to generate a novel sequence after 10 attempts.")

