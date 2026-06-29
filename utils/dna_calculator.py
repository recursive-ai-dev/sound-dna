#!/usr/bin/env python3
"""
dna_calculator.py

Core engine for parsing and serializing SonicDNA strings based on JSON rulesets.
Provides type safety, robust error handling, and bijective integrity.
"""

import os
import sys
import json
import logging
from typing import Any, Dict, List, Tuple, Optional, Union

def get_resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("DNACalculator")


class RuleParseError(Exception):
    """Raised when DNA string does not match the rule definition."""
    pass


class Rule:
    """
    Represents a single SonicDNA rule (e.g., Volume, Frequency).
    Handles the recursive parsing and serialization of sub-variables.
    """

    def __init__(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.raw: Dict[str, Any] = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise RuleParseError(f"Failed to load rule file {filepath}: {e}")

        # Required keys
        self.variable: str = self.raw.get('variable', '')
        self.prefix: str = self.raw.get('prefix', '')
        self.subvars: Dict[str, Any] = self.raw.get('subvars', {})

        if not self.variable or not self.prefix or not self.subvars:
            raise RuleParseError(f"Invalid rule file (missing core keys): {filepath}")

        # Precompute a parsing plan (list of (name, schema)) in insertion order
        self.plan: List[Tuple[str, Dict[str, Any]]] = []
        for subvar_name, subvar_schema in self.subvars.items():
            self.plan.append((subvar_name, subvar_schema))

    def parse(self, dna_string: str) -> Dict[str, Any]:
        """
        Given a DNA string (complete, including prefix), return a nested dict:
        { subvar_name: value or {child: ...}, ... }.
        """
        if not dna_string.startswith(self.prefix):
            raise RuleParseError(
                f"DNA '{dna_string}' does not start with expected prefix '{self.prefix}' for rule '{self.variable}'"
            )

        idx = len(self.prefix)
        values: Dict[str, Any] = {}
        for subvar_name, subvar_schema in self.plan:
            val, idx = self._parse_subvar(subvar_schema, dna_string, idx)
            values[subvar_name] = val

        # If idx != len(dna_string), leftover characters
        if idx != len(dna_string):
            raise RuleParseError(
                f"Extra characters after parsing rule '{self.variable}': "
                f"parsed up to index {idx}, string length {len(dna_string)} in '{dna_string}'"
            )
        return values

    def serialize(self, values_dict: Dict[str, Any]) -> str:
        """
        Given a nested dict of values matching this rule’s subvars, rebuild the DNA string.
        """
        dna: List[str] = [self.prefix]
        for subvar_name, subvar_schema in self.plan:
            if subvar_name not in values_dict:
                raise RuleParseError(f"Missing subvar '{subvar_name}' for rule '{self.variable}'")
            dna_part = self._serialize_subvar(subvar_schema, values_dict[subvar_name])
            dna.append(dna_part)
        return ''.join(dna)

    def _parse_subvar(self, schema: Dict[str, Any], dna: str, idx: int) -> Tuple[Any, int]:
        """
        Recursively parse one subvar. Returns (parsed_value, new_idx).
        """
        # Leaf case detection
        if 'description' in schema:
            return self._parse_leaf(schema, dna, idx)
        else:
            # Group (nested subfields)
            result: Dict[str, Any] = {}
            for child_name, child_schema in schema.items():
                if not isinstance(child_schema, dict):
                    continue
                val, idx = self._parse_subvar(child_schema, dna, idx)
                result[child_name] = val
            return result, idx

    def _parse_leaf(self, schema: Dict[str, Any], dna: str, idx: int) -> Tuple[Any, int]:
        """
        Dynamically identify fields in the leaf schema and parse them.
        Fields can be numeric, signed, or class-based.
        """
        fields = self._identify_fields(schema)
        if not fields:
            raise RuleParseError(f"Unrecognized leaf schema at idx {idx}: {schema}")

        results: Dict[str, Any] = {}
        for field_type, field_key, config in fields:
            if idx >= len(dna):
                raise RuleParseError(
                    f"Unexpected end of DNA string while parsing '{field_key}' at idx {idx} in '{dna}'"
                )

            if field_type == 'class':
                # Class code length: determined by the config string length
                # config is e.g. "ZZ-AA" or "Z-A"
                delimiter = '–' if '–' in config else '-'
                if delimiter in config:
                    first_part = config.split(delimiter)[0]
                    length = len(first_part)
                else:
                    # Single char or fixed mapping not using range
                    length = 1

                val = dna[idx:idx+length]
                if len(val) < length:
                    raise RuleParseError(f"Expected {length} chars for class '{field_key}', got '{val}' at idx {idx}")
                results[field_key] = val
                idx += length
            elif field_type == 'numeric':
                # Numeric: fixed length 'pad'
                pad = int(config)
                val_str = dna[idx:idx+pad]
                if len(val_str) < pad or not val_str.isdigit():
                    raise RuleParseError(
                        f"Numeric parse error for '{field_key}' at idx {idx}: "
                        f"expected {pad} digits, got '{val_str}'"
                    )
                results[field_key] = int(val_str)
                idx += pad
            elif field_type == 'sign':
                # Sign: single character
                sign_char = dna[idx:idx+1]
                results[field_key] = sign_char
                idx += 1

        # Return single value if only one field, else the dict
        if len(results) == 1:
            return list(results.values())[0], idx
        return results, idx

    def _identify_fields(self, schema: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
        """
        Analyze schema keys to find field definitions and their order.
        Returns a list of (type, key_name, config) in sequence.
        """
        field_defs: List[Tuple[str, str, Any]] = []

        # 1. Suffix-based Composite detection (e.g. Frequency root/fm)
        potential_prefixes: List[str] = []
        # Use a list for prefixes and check existence to preserve schema order
        for k in schema.keys():
            for suffix in ['_pad', '_class', '_sign']:
                if k.endswith(suffix):
                    pfx = k.rsplit('_', 1)[0]
                    if pfx not in potential_prefixes:
                        potential_prefixes.append(pfx)

        if potential_prefixes:
            for pfx in potential_prefixes:
                if f"{pfx}_sign" in schema:
                    field_defs.append(('sign', pfx, schema[f"{pfx}_sign"]))
                if f"{pfx}_class" in schema:
                    field_defs.append(('class', pfx, schema[f"{pfx}_class"]))
                if f"{pfx}_pad" in schema:
                    field_defs.append(('numeric', pfx, schema[f"{pfx}_pad"]))
            return field_defs

        # 2. Standard patterns (sign, class, numeric)
        if 'sign' in schema:
            field_defs.append(('sign', 'sign', schema['sign']))

        if 'class' in schema or 'class_order' in schema:
            cfg = schema.get('class') or schema.get('class_order')
            field_defs.append(('class', 'class', cfg))

        if 'pad' in schema:
            field_defs.append(('numeric', 'value', schema['pad']))

        return field_defs

    def _serialize_subvar(self, schema: Dict[str, Any], value: Any) -> str:
        """
        Serialize a single subvar (leaf or group) given the value(s).
        """
        if 'description' in schema:
            return self._serialize_leaf(schema, value)

        parts: List[str] = []
        if not isinstance(value, dict):
             raise RuleParseError(f"Expected dict for group subvar, got {type(value)}")

        for child_name, child_schema in schema.items():
            if not isinstance(child_schema, dict):
                continue
            if child_name not in value:
                raise RuleParseError(f"Missing nested '{child_name}' in value {value} for rule '{self.variable}'")
            parts.append(self._serialize_subvar(child_schema, value[child_name]))
        return ''.join(parts)

    def _serialize_leaf(self, schema: Dict[str, Any], value: Any) -> str:
        """
        Build the exact substring corresponding to this leaf schema using identified fields.
        """
        fields = self._identify_fields(schema)
        if not fields:
            raise RuleParseError(f"Cannot serialize leaf schema: {schema}")

        parts: List[str] = []
        for field_type, field_key, config in fields:
            if len(fields) == 1:
                field_val = value
            else:
                if not isinstance(value, dict) or field_key not in value:
                    raise RuleParseError(f"Missing field '{field_key}' in value {value}")
                field_val = value[field_key]

            if field_type == 'class':
                parts.append(str(field_val))
            elif field_type == 'numeric':
                parts.append(str(field_val).zfill(int(config)))
            elif field_type == 'sign':
                parts.append(str(field_val))

        return ''.join(parts)


class DNACalculator:
    """
    Registry for SonicDNA Rules. Orchestrates parsing of any valid DNA string.
    """
    def __init__(self, rules_folder: str = 'rules'):
        self.rules: Dict[str, Rule] = {}
        abs_rules_folder = get_resource_path(rules_folder)
        self._load_rules(abs_rules_folder)

    def _load_rules(self, folder: str) -> None:
        if not os.path.isdir(folder):
            logger.error(f"Rules folder not found: '{folder}'")
            raise FileNotFoundError(f"Rules folder not found: '{folder}'")

        for fname in os.listdir(folder):
            if fname.lower().endswith('.json'):
                path = os.path.join(folder, fname)
                try:
                    rule = Rule(path)
                    if rule.prefix in self.rules:
                        raise RuleParseError(f"Duplicate prefix '{rule.prefix}' found in {fname}")
                    self.rules[rule.prefix] = rule
                except Exception as e:
                    logger.warning(f"Failed to load rule {fname}: {e}")

        logger.info(f"Loaded {len(self.rules)} DNA rules.")

    def parse(self, dna_string: str) -> Dict[str, Any]:
        """
        Identify which rule applies (by prefix), then parse.
        Returns { 'rule': variable_name, 'values': nested_dict }.
        """
        sorted_prefixes = sorted(self.rules.keys(), key=len, reverse=True)
        for prefix in sorted_prefixes:
            if dna_string.startswith(prefix):
                rule = self.rules[prefix]
                parsed = rule.parse(dna_string)
                return {'rule': rule.variable, 'values': parsed}

        raise RuleParseError(f"No matching rule for DNA '{dna_string}'")

    def serialize(self, variable_name: str, values_dict: Dict[str, Any]) -> str:
        """
        Given a variable name, find the rule and serialize values to DNA string.
        """
        for rule in self.rules.values():
            if rule.variable == variable_name:
                return rule.serialize(values_dict)
        raise RuleParseError(f"No rule found for variable '{variable_name}'")
