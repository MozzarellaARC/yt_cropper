#!/usr/bin/env python3
"""
YouTube Multi Trim + Cropper
Main application entry point
"""

from yt_backend import YouTubeCropperBackend
from yt_gui import YouTubeCropperGUI


def main():
    # Create backend instance
    backend = YouTubeCropperBackend()
    
    # Create and run GUI
    app = YouTubeCropperGUI(backend)
    app.run()


if __name__ == "__main__":
    main()