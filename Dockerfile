FROM python:3.11-slim

WORKDIR /app

# Install basic dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render will provide the PORT env var, we just expose a default
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
