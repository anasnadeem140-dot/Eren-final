#!/bin/bash
set -e

# Update and install Python
apt update
apt install -y python3-pip

# Go to app directory
cd /app

# Install Python dependencies
pip3 install -r requirements.txt

# Start HTTP server on port 8080 (background)
python3 -m http.server 8080 --directory /app/data &

# Start Telegram bot (foreground)
python3 bot.py
