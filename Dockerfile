FROM python:3.11-slim

# System dependencies:
# - tesseract-ocr + language packs: required for .ocr (English + Hindi)
# - iputils-ping: required for .net (network monitor ping check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
