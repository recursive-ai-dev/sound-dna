import sqlite3
import json
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("DNADatabase")

class DNADatabase:
    """
    SQLite wrapper to store encoded SonicDNA sequences into a reference bank.
    """
    def __init__(self, db_path: str = 'data/sonic_bank.db'):
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sound_bank (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    sequence_hash TEXT UNIQUE NOT NULL,
                    dna_sequence TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            
    def _hash_sequence(self, sequence: List[Dict[str, str]]) -> str:
        """
        Produce a deterministic hash of the sequence for novelty checking.
        """
        # Convert sequence to canonical JSON string
        canon = json.dumps(sequence, sort_keys=True)
        return hashlib.sha256(canon.encode('utf-8')).hexdigest()

    def save_sequence(self, name: str, sequence: List[Dict[str, str]]) -> bool:
        """
        Saves a DNA sequence to the bank. 
        Returns True if saved, False if it was a duplicate (not novel).
        """
        seq_hash = self._hash_sequence(sequence)
        seq_json = json.dumps(sequence)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sound_bank (name, sequence_hash, dna_sequence)
                    VALUES (?, ?, ?)
                ''', (name, seq_hash, seq_json))
                conn.commit()
            logger.info(f"Saved sequence '{name}' to bank.")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Sequence '{name}' is already in the bank (duplicate).")
            return False

    def is_novel(self, sequence: List[Dict[str, str]]) -> bool:
        """
        Checks if the exact sequence exists in the bank.
        """
        seq_hash = self._hash_sequence(sequence)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM sound_bank WHERE sequence_hash = ?', (seq_hash,))
            return cursor.fetchone() is None
            
    def get_all_sequences(self) -> List[Dict[str, Any]]:
        """
        Retrieve all sequences from the bank.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, dna_sequence, created_at FROM sound_bank')
            rows = cursor.fetchall()
            
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'name': row[1],
                'sequence': json.loads(row[2]),
                'created_at': row[3]
            })
        return results

    def delete_sequence(self, seq_id: int) -> bool:
        """
        Delete a sequence from the bank by its integer ID.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sound_bank WHERE id = ?', (seq_id,))
            conn.commit()
            return cursor.rowcount > 0
