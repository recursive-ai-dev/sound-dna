# Quality Audit

1. **`utils/generative_engine.py` - Lines 85, 96 (Phase Accumulation Discontinuity)**
   - **Problem:** `self.fm_phase` and `self.phase` are incremented by a single step `+ 2 * np.pi * freq * (block_size / self.sample_rate)` for the *entire block*. However, inside the block, `t` resets to 0 (`np.arange(block_size) / self.sample_rate`), and `modulator` and `wave` calculate instantaneous phase as `freq * t + starting_phase`.
   - **Why it matters:** The instantaneous frequency applies correctly inside the block, but phase modulation (`modulator`) uses `self.fm_phase` which is a constant offset for the whole block, creating a massive step discontinuity in the FM signal at block boundaries (every 100ms), causing severe audio clicking.
   - **Fix:** Calculate the cumulative phase sample-by-sample for the block: `phase_accum = np.cumsum(np.full(block_size, 2 * np.pi * h_freq / self.sample_rate)) + self.phase[i]`. `self.phase[i] = phase_accum[-1] % (2 * np.pi)`. Use `np.sin(phase_accum + modulator)`. Do the same for `fm_phase`.
   - **Overlaps:** No.

2. **`main.py` - Lines 48-69 (Race Condition in File Watcher)**
   - **Problem:** The `watch_loop` does a basic check `os.path.getsize(input_file) > 0` and immediately renames `toSequence.txt`. If an external process is actively writing to the file, it will be moved mid-write.
   - **Why it matters:** Can lead to incomplete DNA strings being parsed, raising `RuleParseError` or silently producing corrupt data and causing data loss for the writer.
   - **Fix:** Implement a stability delay before renaming. Check the file size, wait a short period (e.g. 0.5s), check the size again, and only proceed if the size is stable and > 0.
   - **Overlaps:** No.

3. **`utils/dna_calculator.py` - Lines 188-196 (Hardcoded Field Detection Order)**
   - **Problem:** `_identify_fields` iterates over matching suffixes (`_pad`, `_class`, `_sign`) and appends them to `field_defs` in a hardcoded order (`sign`, `class`, `numeric`).
   - **Why it matters:** If a rule schema specifies fields in a different order (e.g., `_pad` followed by `_class`), the calculator will extract and serialize them in the wrong sequence, breaking bijective parsing and producing corrupted data.
   - **Fix:** Iterate over the `schema.keys()` directly and append the matching field types in the exact order they are defined in the schema dictionary.
   - **Overlaps:** No.

4. **`utils/dna_extractor.py` - Lines 69-70 (NaN Handling Order)**
   - **Problem:** `max_rms = np.max(rms)` is computed *before* NaNs are cleared from the `rms` array. If `rms` contains NaNs (e.g., from purely silent segments evaluated by pyin/librosa), `max_rms` evaluates to NaN.
   - **Why it matters:** A NaN `max_rms` triggers the fallback `if max_rms < 1e-6 or np.isnan(max_rms): max_rms = 1.0`. This bypasses true normalization and scales the valid RMS values incorrectly, breaking volume encoding.
   - **Fix:** Move the cleaning step `rms = np.nan_to_num(rms, nan=0.0)` to *before* calculating `max_rms = np.max(rms)`.
   - **Overlaps:** No.

5. **`utils/dna_db.py` - Lines 43-61 (Database Lock Contention)**
   - **Problem:** `save_sequence` rapidly opens and closes SQLite connections inside a `try` block without configuring `timeout` or enabling `PRAGMA journal_mode=WAL;`.
   - **Why it matters:** In a batch processing scenario or concurrent access (e.g., background watcher + GUI + agents), `sqlite3.OperationalError: database is locked` will frequently occur, silently failing to save valid sequences.
   - **Fix:** Add a timeout parameter `sqlite3.connect(self.db_path, timeout=10.0)` and enable WAL mode in `_init_db` via `cursor.execute('PRAGMA journal_mode=WAL;')`.
   - **Overlaps:** No.

6. **`utils/dna_randomizer.py` - Line 106 (Brittle Prefix Lookup Crash)**
   - **Problem:** When assembling random DNA sequences, the code uses a list comprehension `[p for p, rl in self.calculator.rules.items() if rl.variable == r][0]` to find the rule's prefix.
   - **Why it matters:** If one of the `core_rules` ("Volume", "Frequency", "Timbre") is ever missing, renamed, or fails to load, the list is empty, and `[0]` raises an `IndexError`, crashing the generative engine.
   - **Fix:** Use a safe lookup: `rule = next((rl for rl in self.calculator.rules.values() if rl.variable == r), None); if rule: frame_strs[rule.prefix] = ...`
   - **Overlaps:** No.

7. **`agents/batch/sequence.py` - Lines 137-142 (Incomplete LLM Extraction)**
   - **Problem:** The prompt instructs the LLM to generate `VOL` and `FRE` lines. However, the parsing loop `for line in lines: if line.startswith(...): extracted_dna = line; break` terminates after finding the first match.
   - **Why it matters:** Only the first DNA variable (e.g., `VOL`) is captured and saved. The requested `FRE` variable is silently discarded, resulting in incomplete DNA sequences.
   - **Fix:** Remove the `break` statement and concatenate or append all valid DNA strings found in the LLM response.
   - **Overlaps:** No.

8. **`ui/synthesis_panel.py` - Lines 100-101 (Thread Leakage)**
   - **Problem:** `self.thread = SynthesizerThread(text)` assigns a new QThread instance directly to `self.thread` and starts it without managing the previous thread.
   - **Why it matters:** Rapidly clicking "Synthesize" abandons running threads. They continue executing in the background, consuming CPU resources, leaking memory, and causing overlapping chaotic audio playbacks.
   - **Fix:** Check if the thread is active before creating a new one: `if hasattr(self, 'thread') and self.thread.isRunning(): self.thread.wait()`.
   - **Overlaps:** No.

9. **`ui/bank_panel.py` - Lines 129-130 (Thread Leakage)**
   - **Problem:** Similar to `SynthesisPanel`, `self.current_thread = SynthesizerThread(seq_json_str)` overwrites the previous thread without synchronization.
   - **Why it matters:** Rapidly playing different sounds from the bank leads to thread leakage and overlapping audio playback.
   - **Fix:** Add `if self.current_thread and self.current_thread.isRunning(): self.current_thread.wait()` before spawning a new thread.
   - **Overlaps:** No.

10. **`utils/generative_engine.py` - Line 140 (Lfilter Pop Artifact)**
    - **Problem:** `audio_out = scipy.signal.lfilter(b, a, audio_out)` uses a default initial filter state of 0.
    - **Why it matters:** If `generate_from_sequence` is ever used sequentially on chunks of a longer sequence (e.g. streaming playback or block-by-block processing), resetting the IIR filter state to 0 at the start of every chunk creates a loud, audible pop artifact.
    - **Fix:** Store the filter state (`zi`) persistently in the `GenerativeEngine` instance and pass it to `lfilter`: `audio_out, self.filter_state = scipy.signal.lfilter(b, a, audio_out, zi=self.filter_state)`.
    - **Overlaps:** No.
