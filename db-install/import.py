import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Every connection setting comes from libpq's PG* environment variables. During the image's
# first start none are set, so this connects over the Unix socket as postgres; run as a seed job
# against another server, such as a Data Services Manager database, they name it.
conn = psycopg2.connect("")
cur = conn.cursor()

# The load is one transaction, so data in the table means a finished load: a second run, such as
# a Kubernetes Job retried after the load committed, has nothing to do.
cur.execute("SELECT EXISTS (SELECT 1 FROM aircraft_metadata)")
if cur.fetchone()[0]:
    print("aircraft_metadata already holds data; nothing to import.")
    conn.close()
    raise SystemExit(0)

print("Loading CSV file...")
# Every column is read as text: pandas would make an all-empty column float, and filling a float
# column with '' is deprecated. Missing fields, and text pandas reads as missing such as "N/A",
# are still stored as empty strings, as every earlier load did.
df = pd.read_csv('/data/aircraftDatabase.csv', dtype=str).fillna('')
total = len(df)
print(f"Loaded {total} aircraft records")

# In pages of rows rather than one statement per row: over a network each statement costs a
# round trip, and there are half a million rows.
print("Importing records...")
execute_values(
    cur,
    "INSERT INTO aircraft_metadata VALUES %s ON CONFLICT (icao24) DO NOTHING",
    (tuple(row.values) for _, row in df.iterrows()),
    page_size=5000,
)

conn.commit()
conn.close()
print(f"Import complete! {total} records imported.")
