# OpenSky PostgreSQL Container

A Docker image with a PostgreSQL database preloaded with aircraft metadata from the [OpenSky Network](https://opensky-network.org/).

It automates the process of:
- Downloading the latest `aircraftDatabase.csv`
- Creating a PostgreSQL table for aircraft metadata
- Loading the CSV into the database at container initialization

📦 Project Contents

- `Dockerfile` — Builds a PostgreSQL image and loads data.
- `init.sql` — SQL schema to create the `aircraft_metadata` table.
- `import.py` — Python script that imports the CSV into the database using `psycopg2` and `pandas`.

## Data Source

The metadata is pulled from the official OpenSky dataset:

📄 [Aircraft Metadata CSV](https://opensky-network.org/datasets/metadata/aircraftDatabase.csv)

Fields include:
- `icao24` (hex ID)
- `registration` (tail number)
- `model`, `manufacturer`, `typecode`
- `operator`, `callsign`, `built`, `adsb`, `acars`, etc.


## 🐳 Build & Run

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/darrylcauldwell/adsb-db:latest --push .

docker pull ghcr.io/darrylcauldwell/adsb-db:latest

docker run -d --network adsb --name adsb-db -p 5432:5432 ghcr.io/darrylcauldwell/adsb-db:latest

docker exec -it adsb-db /usr/bin/psql -U postgres -c "SELECT COUNT(*) FROM aircraft_metadata;"
```

## License

Data provided by OpenSky Network. Check their [Terms of Use](https://opensky-network.org/about/terms-of-use) before use in production.
