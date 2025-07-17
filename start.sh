#!/bin/bash

# Add ffmpeg folder to PATH
export PATH=$PWD/bin:$PATH

# Show version (just for confirmation)
ffmpeg -version

# Start the Python app
python app.py


