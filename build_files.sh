set -e
echo "BUILD START"
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear
echo "Check output directory..."
ls -la
echo "BUILD END"
