#!/bin/bash
# ============================================================
#  PathLab — START SCRIPT (Linux / Mac)
#  Yahan se decide karein database kahan se load ho
# ============================================================

echo ""
echo " ╔══════════════════════════════════════════════╗"
echo " ║        PathLab Lab Management System         ║"
echo " ║           Starting... Please wait            ║"
echo " ╚══════════════════════════════════════════════╝"
echo ""

# ------------------------------------------------------------
# DB PATH CONFIGURATION
# Neeche se ek option UNCOMMENT karein (# hatao line se)
# ------------------------------------------------------------

# [OPTION 1] Default — Project folder mein hi database (sabse simple)
#   (kuch mat karein, aise hi chhod do)

# [OPTION 2] Pendrive mein database
#   (/media/Jatin/PENDRIVE ki jagah apna pendrive mount path likhein)
# export PATHLAB_DB_PATH=/media/Jatin/PENDRIVE/pathlab_data/db.sqlite3
# export PATHLAB_MEDIA_PATH=/media/Jatin/PENDRIVE/pathlab_data/media

# [OPTION 3] Network Server / NAS
# export PATHLAB_DB_PATH=/mnt/server/pathlab/db.sqlite3
# export PATHLAB_MEDIA_PATH=/mnt/server/pathlab/media

# ------------------------------------------------------------

cd "$(dirname "$0")"

echo "[1/3] Dependencies check kar raha hai..."
pip install -r requirements.txt -q

echo "[2/3] Database update kar raha hai..."
python manage.py migrate --run-syncdb -v 0

echo "[3/3] Server shuru ho raha hai..."
echo ""
echo " ✅ PathLab chalu hai!"
echo " 🌐 Browser mein kholein: http://127.0.0.1:8000"
if [ -n "$PATHLAB_DB_PATH" ]; then
    echo " 📁 Database: $PATHLAB_DB_PATH"
else
    echo " 📁 Database: Project folder (db.sqlite3)"
fi
echo ""
echo " Band karne ke liye: Ctrl+C dabayein"
echo " ─────────────────────────────────────────────"
echo ""

python manage.py runserver 0.0.0.0:8000
