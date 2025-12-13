import pandas as pd
import psycopg2

print("Loading CSV file...")
df = pd.read_csv('/data/aircraftDatabase.csv').fillna('')
total = len(df)
print(f"Loaded {total} aircraft records")

# Connect via Unix socket during init (no host = Unix socket)
conn = psycopg2.connect(
    dbname='postgres',
    user='postgres'
)
cur = conn.cursor()

print("Importing records...")
for i, (_, row) in enumerate(df.iterrows()):
    cur.execute("""
        INSERT INTO aircraft_metadata VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                              %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (icao24) DO NOTHING
    """, tuple(row.values))

    if (i + 1) % 50000 == 0:
        conn.commit()
        print(f"  Imported {i + 1}/{total} records...")

conn.commit()
conn.close()
print(f"Import complete! {total} records imported.")
