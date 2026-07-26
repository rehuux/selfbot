FROM python:3.11-slim

# System dependencies:
# - ffmpeg: required for .music (yt-dlp audio extraction/conversion to mp3)
# - tesseract-ocr + language packs: required for .ocr (English + Hindi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
