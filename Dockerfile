FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
# We let playwright handle the complex dependency list for the specific OS version
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Render uses the PORT environment variable
EXPOSE 8080

# Use a shell to run the bot so environment variables are handled correctly
CMD ["python", "bot.py"]
