FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/darrylcauldwell/planespotter"
LABEL org.opencontainers.image.title="planespotter-adsb-sync"
LABEL org.opencontainers.image.description="Planespotter ADSB-Sync - OpenSky Network position synchronizer"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 9090

CMD ["python", "-m", "app.main"]
