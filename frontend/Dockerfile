FROM node:22-slim AS css-builder
WORKDIR /build
COPY package.json postcss.config.js ./
RUN npm install
COPY app/static/css/input.css app/static/css/input.css
COPY app/templates/ app/templates/
RUN npm run build:css

FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/darrylcauldwell/planespotter"
LABEL org.opencontainers.image.title="planespotter-frontend"
LABEL org.opencontainers.image.description="Planespotter Frontend - Web interface for aircraft tracking"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY --from=css-builder /build/app/static/css/output.css ./app/static/css/output.css

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-graceful-shutdown", "30"]
