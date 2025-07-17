#!/bin/bash

# Step 1: Update and install FFmpeg
apt update && apt install ffmpeg -y

# Step 2: Start your app
python app.py
