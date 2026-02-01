#!/bin/bash
set -e

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "BUILD START"
echo "Working directory: $(pwd)"
echo "Files in current directory:"
ls -la

echo "Installing Python packages..."
python3 -m pip install -r requirements.txt --break-system-packages

echo "Installed packages:"
python3 -m pip list

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Output directory contents:"
ls -la staticfiles/

echo "BUILD END"
