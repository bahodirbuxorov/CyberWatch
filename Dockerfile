FROM python:3.11-slim

# Non-root user yaratish (security best practice)
RUN groupadd -r botuser && useradd -r -g botuser -m botuser

# Ishchi papka
WORKDIR /app

# Dependencies o'rnatish
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod nusxalash
COPY src/ src/

# Data va logs papkalarini yaratish
RUN mkdir -p /app/data /app/logs && \
    chown -R botuser:botuser /app/data /app/logs

# Volume mount points
VOLUME ["/app/data", "/app/logs"]

# Non-root user ga o'tish
USER botuser

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import src.config" || exit 1

# Bot ni ishga tushirish
CMD ["python", "-m", "src.main"]
