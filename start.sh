#!/bin/bash

# Exit on error
set -e

# Step 1: Install dependencies
echo "[*] Installing dependencies..."
apt update
apt install -y torsocks ffmpeg tor python3-pip

# Step 2: Upgrade yt-dlp
echo "[*] Installing yt-dlp..."
pip install -U yt-dlp

# Step 3: Start Tor in the background
echo "[*] Starting Tor..."
tor &

# Wait for Tor to initialize
sleep 10

# Step 4: Launch your Python app via torsocks
echo "[*] Starting your app..."
torsocks python3 app.py
