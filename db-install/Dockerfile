FROM postgres:15

LABEL org.opencontainers.image.source="https://github.com/darrylcauldwell/planespotter"
LABEL org.opencontainers.image.title="planespotter-db-install"
LABEL org.opencontainers.image.description="Planespotter Database - PostgreSQL with OpenSky aircraft data"
LABEL org.opencontainers.image.licenses="MIT"

ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=postgres

# Install Python and dependencies for data import
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl && \
    pip3 install --break-system-packages pandas psycopg2-binary && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download the OpenSky aircraft database
RUN mkdir -p /data && \
    curl -L -o /data/aircraftDatabase.csv \
    https://opensky-network.org/datasets/metadata/aircraftDatabase.csv

# Copy initialization files
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY import.py /import.py
COPY --chmod=755 import-data.sh /docker-entrypoint-initdb.d/02-import-data.sh
