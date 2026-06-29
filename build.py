#!/usr/bin/env python3
"""
build.py

Cross-platform build script for SonicDNA Studio.
Requires PyInstaller.
"""

import os
import sys
import subprocess
import shutil

def main():
    print("Starting SonicDNA Studio Build Process...")
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    # Ensure data and rules folders exist before packaging
    os.makedirs('data', exist_ok=True)
    os.makedirs('rules', exist_ok=True)
    
    # Run PyInstaller with the spec file
    print("Running PyInstaller...")
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "build.spec"])
    
    if result.returncode == 0:
        print("\nBuild successful! Binary is located in the 'dist' folder.")
        if sys.platform.startswith('linux'):
            print("To package as an AppImage or .deb, you can use tools like 'appimagetool' or 'fpm' on the dist/SonicDNA_Studio binary.")
        elif sys.platform == 'darwin':
            print("To package as a .dmg, you can use 'create-dmg' on the generated .app bundle.")
    else:
        print("\nBuild failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
