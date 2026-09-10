# שלב 1: בנייה והתקנת ספריות
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir --prefix=/install -r requirements.txt

# שלב 2: אימג' סופי וקל לריצה
FROM python:3.11-slim
WORKDIR /app

# העתקת הספריות שהותקנו בשלב הקודם
COPY --from=builder /install /usr/local

# יצירת משתמש עם UID 1000 - חובה עבור Hugging Face Spaces!
RUN useradd -m -u 1000 appuser
# העתקת הקוד והגדרת בעלות למשתמש החדש
COPY --chown=appuser . /app

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

# הגדרת הפורט הרשמי של Hugging Face (ליתר ביטחון)
ENV PORT=7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '7860') + '/ping', timeout=3)"

# הרצה ישירה של הבוט שלך (מכיוון שהוא בוט טלגרם ולא שרת אינטרנט)
CMD ["python", "main.py"]
