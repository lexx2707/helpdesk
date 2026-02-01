set -e
echo "BUILD START"
python3 --version
python3 -m pip install -r requirements.txt --break-system-packages
python3 -m pip list
python3 manage.py collectstatic --noinput --clear
echo "Check output directory..."
ls -la
echo "BUILD END"
