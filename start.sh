#!/bin/bash

# Exit on error
set -e

# Step 1: Install dependencies
echo "[*] Installing dependencies..."
sudo apt update
sudo apt install -y torsocks ffmpeg tor python3-pip

# Step 2: Upgrade yt-dlp
echo "[*] Installing yt-dlp..."
pip install -U yt-dlp

# Step 3: Start Tor in the background
echo "[*] Starting Tor..."
tor &

# Give Tor a few seconds to initialize
sleep 10

# Step 4: Launch your Python app
echo "[*] Starting your app..."
torsocks python3 app.py
