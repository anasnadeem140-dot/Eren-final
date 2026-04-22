FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start both HTTP server and bot
CMD ["sh", "-c", "python3 -m http.server 8080 --directory /app/data & python3 bot.py"]
