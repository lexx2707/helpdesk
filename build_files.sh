#!/bin/bash
set -e

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "BUILD START"
echo "Working directory: $(pwd)"
echo "Files in current directory:"
ls -la

echo "Installing Python packages..."
# Install packages one by one to identify which one pulls in pycairo
python3 -m pip install Django>=5.0 --break-system-packages --no-cache-dir || { echo "Django failed"; exit 1; }
python3 -m pip install whitenoise --break-system-packages --no-cache-dir || { echo "whitenoise failed"; exit 1; }
python3 -m pip install gunicorn --break-system-packages --no-cache-dir || { echo "gunicorn failed"; exit 1; }
python3 -m pip install markdown --break-system-packages --no-cache-dir || { echo "markdown failed"; exit 1; }
python3 -m pip install python-dateutil --break-system-packages --no-cache-dir || { echo "python-dateutil failed"; exit 1; }
python3 -m pip install pytz --break-system-packages --no-cache-dir || { echo "pytz failed"; exit 1; }
# Install Pillow last - if this fails, we know it's the culprit
python3 -m pip install "Pillow>=10.0.0" --break-system-packages --no-cache-dir || { echo "Pillow failed but continuing"; }

echo "Installed packages:"
python3 -m pip list

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Output directory contents:"
ls -la staticfiles/

echo "BUILD END"
