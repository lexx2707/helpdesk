set -e
echo "BUILD START"
echo "Current directory: $(pwd)"
echo "Directory entries:"
ls -la

# Get script directory to safely locate requirements.txt
SCRIPT_DIR=$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)
echo "Script directory: $SCRIPT_DIR"

python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages
python3 -m pip list
python3 manage.py collectstatic --noinput --clear
echo "Check output directory..."
ls -la
echo "BUILD END"
