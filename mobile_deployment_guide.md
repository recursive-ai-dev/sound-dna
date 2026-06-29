# SonicDNA Mobile Deployment Guide

While the application is currently optimized for Desktop usage (Linux, Windows, macOS), the PySide6 UI has been architecturally prepared for mobile viewports using responsive layout algorithms (`QBoxLayout` resizing based on width).

To deploy SonicDNA Studio to an Android or iOS device, you must use the official `pyside6-android-deploy` or Qt iOS toolchains. PyInstaller **cannot** compile mobile APKs or IPAs.

## Prerequisites for Android

1. **Java Development Kit (JDK) 11 or 17**
2. **Android SDK & NDK**: Installed via Android Studio.
3. **pyside6-android-deploy**: A tool provided by the Qt for Python team.

## Android Build Steps

1. Install the deployment tool:
   ```bash
   pip install pyside6-android-deploy
   ```

2. Generate the Android manifest and template:
   ```bash
   pyside6-android-deploy --init
   ```
   This generates an `android` folder. You will need to edit `AndroidManifest.xml` to request Audio/Microphone and Storage permissions, which are required for `librosa` file loading and `sounddevice` playback.

3. Build the APK:
   ```bash
   pyside6-android-deploy --wheel-path /path/to/pyside6/wheels --name SonicDNA --main main.py
   ```
   *(Note: The exact command flags depend on your specific Qt version and NDK paths. Refer to the Qt for Python Android documentation).*

## Prerequisites for iOS

iOS compilation with PySide6 is significantly more experimental and requires a macOS host machine with Xcode installed.

1. You must cross-compile the Python interpreter for iOS.
2. Use CMake and the `Qt6` iOS libraries to build a native bridge.
3. Pure Python execution on iOS is restricted by Apple's JIT limitations, so `pyside6-deploy` will AOT (Ahead-of-Time) compile parts of the framework.

## Mobile Architecture Notes

- **File System Limits**: On mobile, you cannot write to arbitrary directories like `data/sonic_bank.db` easily. You must dynamically fetch the application's local app data directory using `QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)` and route the SQLite DB and extracted WAV files there.
- **Librosa / SoundDevice**: These libraries depend on C-extensions (libsndfile, portaudio) which must be compiled for ARM64/Android. You may need to write a custom recipe using tools like `Buildozer` or `python-for-android` if the standard `pyside6-android-deploy` fails to link them.
