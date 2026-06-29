import os
from setuptools import setup, find_packages

setup(
    name="SonicDNA",
    version="0.1.0",
    py_modules=["main"],
    packages=find_packages(),
    install_requires=[
        "PySide6",
        "torch",
        "torchaudio",
        "numpy",
        "scipy",
        "sounddevice",
        "watchdog",
        "requests",
        "librosa",
        "soundfile"
    ],
    entry_points={
        "console_scripts": [
            "sonicdna = main:main"
        ]
    },
    author="BirchStag Studios",
    author_email="birchstagstudios@gmail.com",
    description="A project for developing a structured data-driven approach to audio representation and generative synthesis.",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
)
