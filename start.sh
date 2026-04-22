#!/bin/bash
set -e

# Update and install dependencies
apt update
apt install -y git python3-pip

# Clone the repo (ensures latest code)
git clone https://github.com/anasnadeem140-dot/Eren-final.git /app
cd /app

# Install Python dependencies
pip3 install -r requirements.txt

# Start a simple HTTP server on port 8080 (background)
python3 -m http.server 8080 --directory /app/data &

# Start the Telegram bot (foreground)
python3 bot.py
