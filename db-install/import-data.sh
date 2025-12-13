#!/bin/bash
set -e

echo "Importing OpenSky aircraft database..."
python3 /import.py
echo "Import complete!"
