#!/bin/bash

echo "Starting TollAI Monitor..."

# Load local environment file if available
if [ -f ".env" ]; then
    set -a
    . ./.env 2>/dev/null || true
    set +a
fi

# Determine python executable (prefer venv if present)
PYTHON_BIN="python"
if [ -d "venv" ]; then
    PYTHON_BIN="./venv/bin/python"
elif [ -d "python/venv" ]; then
    PYTHON_BIN="./python/venv/bin/python"
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/backend:$(pwd)/ai_engine:$(pwd)"

echo "Cleaning up old AI Engine processes..."
if command -v pkill >/dev/null 2>&1; then
    pkill -f "ai_engine/ai_engine.py" 2>/dev/null || true
    pkill -f "python/ai_engine.py" 2>/dev/null || true
fi

# 1. Start the Flask server in the background
# Default PORT to 7860 (Hugging Face) or 5002 locally
export PORT=${PORT:-7860}
echo "Starting Flask web server on port $PORT..."
SERVER_SCRIPT="backend/server.py"
if [ ! -f "$SERVER_SCRIPT" ]; then
    SERVER_SCRIPT="python/server.py"
fi
$PYTHON_BIN $SERVER_SCRIPT &
SERVER_PID=$!
trap 'kill $SERVER_PID $AI_PID 2>/dev/null' EXIT INT TERM

# 2. Wait for the Flask server to initialize
sleep 4


# 3. Start AI Engine camera stream
# Priority: CAM1_SOURCE > NVR streams (if reachable) > traffic.mp4 > webcam
NVR_ONLINE=0
if [ -n "$NVR_HOST" ] && [ -n "$NVR_PASS" ]; then
    if $PYTHON_BIN -c "
import requests, sys, os
from requests.auth import HTTPDigestAuth
host = os.environ.get('NVR_HOST', '')
user = os.environ.get('NVR_USER', 'admin')
pwd = os.environ.get('NVR_PASS', '')
if not host or not pwd:
    sys.exit(1)
try:
    r = requests.get(f'http://{host}/ISAPI/Streaming/channels/101/picture', auth=HTTPDigestAuth(user, pwd), timeout=2.5)
    sys.exit(0 if r.status_code == 200 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        NVR_ONLINE=1
    fi
fi

if [ -n "$CAM1_SOURCE" ]; then
    SOURCE="$CAM1_SOURCE"
elif [ "$NVR_ONLINE" -eq 1 ]; then
    echo "Real NVR at $NVR_HOST is ONLINE. Using real multi-camera NVR streams."
    SOURCE="nvr"
elif [ -f "traffic.mp4" ]; then
    SOURCE="traffic.mp4"
elif [ -f "ai_engine/traffic.mp4" ]; then
    SOURCE="ai_engine/traffic.mp4"
elif [ -f "python/traffic.mp4" ]; then
    SOURCE="python/traffic.mp4"
elif [ -e "/dev/video0" ]; then
    SOURCE="0"
else
    if [ -f "traffic.mp4" ]; then
        SOURCE="traffic.mp4"
    elif [ -f "ai_engine/traffic.mp4" ]; then
        SOURCE="ai_engine/traffic.mp4"
    else
        SOURCE="0"
    fi
fi

export ACTIVE_CAMERAS=${ACTIVE_CAMERAS:-"1,2"}

AI_SCRIPT="ai_engine/ai_engine.py"
if [ ! -f "$AI_SCRIPT" ]; then
    AI_SCRIPT="python/ai_engine.py"
fi

echo "Starting YOLO AI engine with source: $SOURCE on Active Cameras: $ACTIVE_CAMERAS"
# Run in headless mode without showing cv2 display window
$PYTHON_BIN $AI_SCRIPT --source "$SOURCE" --cameras "$ACTIVE_CAMERAS" --no-window \
    --model "${YOLO_MODEL:-yolov8n.pt}" &
AI_PID=$!

# 4. Wait for the main Flask server process to keep the container active
wait $SERVER_PID
