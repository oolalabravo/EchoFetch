#!/bin/bash

# Exit on error
set -e

# Step 1: Install dependencies
echo "[*] Installing dependencies..."
apt-get update
apt-get install -y tor ffmpeg

apt update
apt install -y  ffmpeg  python3-pip

# Step 2: Upgrade yt-dlp
echo "[*] Installing yt-dlp..."
pip install -U yt-dlp





# Step 4: Launch your Python app via torsocks
echo "[*] Starting your app..."
python3 app.py
