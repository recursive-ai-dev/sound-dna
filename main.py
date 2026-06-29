#!/usr/bin/env python3
"""
main.py

– Launch PySide6 GUI (ui/main_window.py)
– Start background watcher for data/raw/toSequence.txt
– CLI support for one-time batch parsing
"""

import os
import sys
import time
import threading
import argparse
import uuid
import logging
from typing import Optional

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.dna_ui import main as run_batch, ensure_folder

try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    logging.warning("PySide6 not found. GUI mode will be unavailable.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("SonicDNA_Main")

# Global flag for stopping the watcher thread
stop_event = threading.Event()

def watch_loop(script_dir: str) -> None:
    """
    Continuously watch data/raw/toSequence.txt. Whenever content appears:
    1. Atomic 'Rotate': Move toSequence.txt to a unique temp file.
    2. Run the batch parser on that temp file.
    3. Delete temp file.
    """
    raw_folder = os.path.join(script_dir, 'data', 'raw')
    work_folder = os.path.join(raw_folder, 'work')
    ensure_folder(raw_folder)
    ensure_folder(work_folder)

    input_file = os.path.join(raw_folder, 'toSequence.txt')

    logger.info(f"Watcher started. Monitoring {input_file} for new DNA lines...")

    try:
        while not stop_event.is_set():
            # Check if file exists and has content
            if os.path.isfile(input_file) and os.path.getsize(input_file) > 0:
                # 1. Atomic Rotate: Move file to a processing name to prevent torn writes
                processing_file = f"{input_file}.{uuid.uuid4()}.tmp"
                try:
                    # os.rename is atomic on Unix and Windows (if target doesn't exist)
                    os.rename(input_file, processing_file)
                    logger.info(f"New DNA detected -> Processing {processing_file}...")

                    # 2. Move to work folder where dna_ui looks for it
                    work_file = os.path.join(work_folder, 'toSequence.txt')
                    os.rename(processing_file, work_file)

                    try:
                        run_batch()
                    except Exception as e:
                        logger.error(f"Error during parsing: {e}")
                    finally:
                        if os.path.exists(work_file):
                            os.remove(work_file)

                    logger.info("Parsing complete. Snapshot cleared.")

                except Exception as e:
                    logger.error(f"Failed to rotate/process: {e}")

            time.sleep(1.0)

    except Exception as e:
        logger.error(f"Watcher loop encountered an error: {e}")
    finally:
        logger.info("Watcher loop exiting.")

def process_once() -> None:
    """Run the batch parser exactly once."""
    logger.info("One-time run: Processing all DNA strings once...")
    try:
        run_batch()
        logger.info("One-time run complete.")
    except Exception as e:
        logger.error(f"One-time run error: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="SonicDNA Parser + GUI Launcher")
    parser.add_argument("--once", action="store_true", help="Run the DNA batch parser exactly once.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if args.once:
        process_once()
        return

    if not GUI_AVAILABLE:
        logger.error("GUI mode requested but PySide6 is not installed. Use --once for CLI mode.")
        sys.exit(1)

    # Start watcher in a daemon thread
    watcher_thread = threading.Thread(target=watch_loop, args=(script_dir,), daemon=True)
    watcher_thread.start()
    logger.info("Watcher thread started in background.")

    # Initialize and run the GUI
    app = QApplication(sys.argv)
    app.setApplicationName("SonicDNA Studio")

    try:
        win = MainWindow()
        win.show()
        exit_code = app.exec()
    except Exception as e:
        logger.critical(f"Failed to launch GUI: {e}")
        exit_code = 1
    finally:
        stop_event.set()
        # Give the watcher thread a moment to shut down gracefully
        watcher_thread.join(timeout=2.0)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
