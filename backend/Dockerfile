FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema (libgomp para CTranslate2/faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

EXPOSE 8000

# Migraciones + arranque
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
