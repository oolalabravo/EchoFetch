#!/bin/bash


# Step 1: Update and install FFmpeg
apt update && apt install ffmpeg -y
apt-get update && apt-get install -y ffmpeg
pip install -U yt-dlp
# Step 2: Start your app
python app.py
