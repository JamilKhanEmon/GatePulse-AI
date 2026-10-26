#!/usr/bin/env python3
"""Flask Web Server REST API & Static Hosting"""

import os
import sys
import site
import json
import time
import threading
import random
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

# Configure path and environment variables before importing third-party packages
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.abspath(os.path.join(_curr_dir, '..'))
for _p in [_curr_dir, os.path.join(_root_dir, 'backend'), os.path.join(_root_dir, 'ai_engine'), _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _vp in [
    os.path.join(_root_dir, 'venv', 'lib', f'python3.{sys.version_info.minor}', 'site-packages'),
    os.path.join(_root_dir, 'venv', 'lib', 'python3.14', 'site-packages'),
    os.path.join(_root_dir, 'python', 'venv', 'lib', f'python3.{sys.version_info.minor}', 'site-packages'),
]:
    if os.path.exists(_vp):
        site.addsitedir(_vp)

try:
    import env_loader
except ImportError:
    pass

from PIL import Image
import requests
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import numpy as np
import cv2

try:
    from ai_engine.ai_engine import DB_CONFIG, TOLL_RATES
except Exception:
    try:
        from ai_engine import DB_CONFIG, TOLL_RATES
    except Exception:
        DB_CONFIG = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASSWORD', ''),
            'database': os.environ.get('DB_NAME', 'gatepulse_db'),
            'port': int(os.environ.get('DB_PORT', 3306))
        }
        TOLL_RATES = {'Bike': 5, 'CNG': 10, 'Auto': 10, 'Car': 20, 'SUV': 25, 'Pickup': 20, 'Microbus': 25, 'Bus': 40, 'Truck': 50}


# Initialize Flask App
ROOT_DIR = _root_dir
FRONTEND_DIR = os.path.join(_root_dir, 'frontend') if os.path.exists(os.path.join(_root_dir, 'frontend')) else _root_dir
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app) # Enable CORS for development cross-origin requests

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('TollServer')
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.ERROR)

# Database Status
db_status = 'fallback'

# Import mysql.connector
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("mysql-connector-python not installed. Running in mock fallback mode.")

# Global state for in-memory mock data (fallback mode)
mock_records = []
mock_rates = {**TOLL_RATES}
mock_rate_history = []
mock_operator_counts = {
    'Bike': 500, 'CNG': 175, 'Auto': 118, 'Pickup': 80, 'Bus': 55, 'Truck': 38
}

# In-memory mock data generator (fallback mode)

PLATE_PREFIXES = ['Dhaka Metro Ga', 'Dhaka Metro Gha', 'Dhaka Metro Nga', 'Chatt Metro Ka', 'Sylhet Metro Ga', 'Rajshahi Metro Kha']
VEHICLE_DISTRIBUTION = {'Bike': 650, 'CNG': 180, 'Auto': 120, 'Pickup': 80, 'Bus': 60, 'Truck': 40}

def generate_mock_plate():
    prefix = random.choice(PLATE_PREFIXES)
    num1 = random.randint(11, 99)
    num2 = random.randint(1000, 9999)
    return f"{prefix}-{num1}-{num2}"

def init_mock_data():
    # Disabled mock data initialization - all data will load from database
    global mock_records
    mock_records = []
            
    # Sort descending by entry time
    mock_records.sort(key=lambda x: x['entry_time'], reverse=True)
    # Re-assign IDs sequentially
    for idx, r in enumerate(reversed(mock_records)):
        r['id'] = idx + 1
    logger.info(f"Initialized {len(mock_records)} mock records in memory (Fallback Mode)")

# Database connection utilities

from db_adapter import get_db_connection as get_raw_db_connection

def get_db_connection():
    global db_status
    try:
        conn = get_raw_db_connection()
        if conn:
            db_status = 'connected'
            return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        
    db_status = 'fallback'
    return None

def check_db_health():
    conn = get_db_connection()
    if conn:
        try:
            conn.close()
            return True
        except Exception:
            pass
    return False

# Initialize database check and seed mock data
if not check_db_health():
    init_mock_data()

# Static file routing

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    assets_dir = os.path.join(FRONTEND_DIR, 'assets')
    if not os.path.exists(assets_dir):
        assets_dir = os.path.join(ROOT_DIR, 'assets')
    return send_from_directory(assets_dir, path)

@app.route('/captured_vehicles/<path:filename>')
def serve_captured_vehicles(filename):
    return send_from_directory(os.path.join(ROOT_DIR, 'captured_vehicles'), filename)

# Live camera video streaming and NVR proxy

NVR_HOST = os.environ.get('NVR_HOST', 'localhost')
NVR_USER = os.environ.get('NVR_USER', 'admin')
NVR_PASS = os.environ.get('NVR_PASS', '')

NVR_CHANNELS = {
    1: {'channel': '101', 'name': 'Camera 1 (Ch 101 - Gate 1 Entry)', 'lane': 'Gate 1 (Entry Gate - Lane A)'},
    2: {'channel': '201', 'name': 'Camera 2 (Ch 201 - Gate 2 Exit)', 'lane': 'Gate 2 (Exit Gate - Lane B)'},
    3: {'channel': '301', 'name': 'Camera 3 (Ch 301 - Gate 3 Entry)', 'lane': 'Gate 3 (Entry Gate - Lane C)'},
    4: {'channel': '401', 'name': 'Camera 4 (Ch 401 - Gate 4 Exit)', 'lane': 'Gate 4 (Exit Gate - Lane D)'},
    5: {'channel': '501', 'name': 'Camera 5 (Ch 501 - Main Approach)', 'lane': 'Main Entrance Approach'},
    6: {'channel': '601', 'name': 'Camera 6 (Ch 601 - Exit Departure)', 'lane': 'Facility Departure Lane'},
    7: {'channel': '701', 'name': 'Camera 7 (Ch 701 - Large Vehicle Bay)', 'lane': 'Zone C (Bus & Truck Bay)'},
    8: {'channel': '801', 'name': 'Camera 8 (Ch 801 - RFID Fast Entry 1)', 'lane': 'RFID Automated Barrier 1'},
    9: {'channel': '901', 'name': 'Camera 9 (Ch 901 - RFID Fast Entry 2)', 'lane': 'RFID Automated Barrier 2'},
    10: {'channel': '1001', 'name': 'Camera 10 (Ch 1001 - Bay Zone A)', 'lane': 'Parking Zone A (Cars)'},
    11: {'channel': '1101', 'name': 'Camera 11 (Ch 1101 - Security Post 1)', 'lane': 'Security Guard Booth 1'},
    12: {'channel': '1201', 'name': 'Camera 12 (Ch 1201 - Security Post 2)', 'lane': 'Security Guard Booth 2'},
    13: {'channel': '1301', 'name': 'Camera 13 (Ch 1301 - Main Yard Overview)', 'lane': 'Central Facility Yard'},
    14: {'channel': '1501', 'name': 'Camera 14 (Ch 1501 - Perimeter Security)', 'lane': 'Perimeter Guard Post'},
}

# Active AI Cameras Multi-Select State
def _parse_active_cams(val):
    if not val:
        return [1, 2]
    if str(val).strip().lower() == 'all':
        return list(range(1, len(NVR_CHANNELS) + 1))
    cams = []
    for p in str(val).split(','):
        p = p.strip()
        if p.isdigit():
            cid = int(p)
            if 1 <= cid <= len(NVR_CHANNELS):
                cams.append(cid)
    return sorted(list(set(cams))) if cams else [1, 2]

active_ai_cameras = _parse_active_cams(os.environ.get('ACTIVE_CAMERAS', '1,2'))

nvr_session = requests.Session()
nvr_session.auth = HTTPDigestAuth(NVR_USER, NVR_PASS)
nvr_session.mount('http://', HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=0))

# In-memory store for the latest JPEG frame of each camera (from AI engine)
latest_frames = {}
latest_frame_times = {}
nvr_frame_cache = {}
nvr_frame_cache_times = {}
nvr_fail_times = {}

_placeholder_cache = None

def get_placeholder_bytes():
    global _placeholder_cache
    if _placeholder_cache:
        return _placeholder_cache
    placeholder_path = os.path.join(FRONTEND_DIR, 'assets', 'img', 'vehicles', 'toll_plaza.png')
    if not os.path.exists(placeholder_path):
        placeholder_path = os.path.join(ROOT_DIR, 'assets', 'img', 'vehicles', 'toll_plaza.png')
    if os.path.exists(placeholder_path):
        try:
            im = Image.open(placeholder_path)
            if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                im = im.convert('RGB')
            out = BytesIO()
            im.save(out, format='JPEG', quality=80)
            _placeholder_cache = out.getvalue()
            return _placeholder_cache
        except Exception as e:
            logger.error(f"Error converting placeholder to JPEG: {e}")
            
def get_camera_placeholder(cam_id):
    """Generate a clean visual 'Camera Offline' placeholder with camera metadata."""
    try:
        from PIL import ImageDraw
        im = Image.new('RGB', (640, 360), color='#090d16')
        draw = ImageDraw.Draw(im)
        ch_info = NVR_CHANNELS.get(cam_id, {})
        lane = ch_info.get('lane', 'Toll Lane')
        ch = ch_info.get('channel', '---')
        
        # Grid frame
        draw.rectangle([(15, 15), (625, 345)], outline='#1e293b', width=2)
        draw.text((320, 140), f"CAM {cam_id} · NO SIGNAL", fill='#ef4444', anchor='mm')
        draw.text((320, 175), f"NVR Channel {ch} (Hardware Offline)", fill='#94a3b8', anchor='mm')
        draw.text((320, 205), lane, fill='#64748b', anchor='mm')
        out = BytesIO()
        im.save(out, format='JPEG', quality=75)
        return out.getvalue()
    except Exception:
        return get_placeholder_bytes()

def _poll_single_cam(item):
    cam_id, ch_info = item
    ch = ch_info['channel']
    url = f"http://{NVR_HOST}/ISAPI/Streaming/channels/{ch}/picture"
    try:
        resp = nvr_session.get(url, timeout=2.0)
        if resp.status_code == 200 and resp.content and len(resp.content) > 1000:
            nvr_frame_cache[cam_id] = resp.content
            nvr_frame_cache_times[cam_id] = time.time()
        elif resp.status_code == 503:
            if cam_id not in nvr_frame_cache:
                nvr_frame_cache[cam_id] = get_camera_placeholder(cam_id)
    except Exception:
        if cam_id not in nvr_frame_cache:
            nvr_frame_cache[cam_id] = get_camera_placeholder(cam_id)

def _background_nvr_poller():
    """Continuously poll NVR cameras concurrently in background with zero streaming lag."""
    logger.info("📡 Starting concurrent background NVR multi-camera poller...")
    pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="NVRPoller")
    while True:
        try:
            list(pool.map(_poll_single_cam, list(NVR_CHANNELS.items())))
        except Exception as e:
            logger.debug(f"NVR poller batch notice: {e}")
        time.sleep(0.35)

# Start background poller thread
nvr_poller_thread = threading.Thread(target=_background_nvr_poller, daemon=True)
nvr_poller_thread.start()

def fetch_nvr_snapshot(camera_id, max_age=15.0):
    """Fetch live JPEG snapshot from AI Engine or cached NVR frame."""
    now = time.time()
    # 1. Prefer AI engine processed frame if available and recent
    if camera_id in latest_frames and (now - latest_frame_times.get(camera_id, 0) < 6.0):
        return latest_frames[camera_id]

    # 2. Return cached NVR frame from background poller
    if camera_id in nvr_frame_cache:
        return nvr_frame_cache[camera_id]

    # 3. Fallback placeholder
    return get_camera_placeholder(camera_id)

@app.route('/api/camera/<int:camera_id>/frame', methods=['POST'])
def upload_camera_frame(camera_id):
    latest_frames[camera_id] = request.data
    latest_frame_times[camera_id] = time.time()
    return jsonify({'success': True})

@app.route('/api/cameras/broadcast_frame', methods=['POST'])
def broadcast_camera_frames():
    """Ultra-fast zero-overhead endpoint for AI Engine to update all camera frames in one request."""
    data = request.data
    cam_ids_header = request.headers.get('X-Camera-IDs', '')
    now = time.time()
    if cam_ids_header:
        try:
            cam_ids = [int(c.strip()) for c in cam_ids_header.split(',') if c.strip().isdigit()]
        except Exception:
            cam_ids = list(NVR_CHANNELS.keys())
    else:
        cam_ids = list(NVR_CHANNELS.keys())
    
    for cid in cam_ids:
        latest_frames[cid] = data
        latest_frame_times[cid] = now
        
    return jsonify({'success': True, 'count': len(cam_ids)})

# In-memory store for raw client webcam uploads (for remote AI processing)
latest_raw_frames = {}
latest_raw_frame_times = {}

@app.route('/api/camera/<int:camera_id>/raw_upload', methods=['POST'])
def upload_raw_frame(camera_id):
    latest_raw_frames[camera_id] = request.data
    latest_raw_frame_times[camera_id] = time.time()
    return jsonify({'success': True})

@app.route('/api/camera/<int:camera_id>/raw_download', methods=['GET'])
def download_raw_frame(camera_id):
    t = latest_raw_frame_times.get(camera_id, 0)
    # Consider frame valid if uploaded within last 3.5 seconds
    if time.time() - t < 3.5 and camera_id in latest_raw_frames:
        return latest_raw_frames[camera_id], 200, {'Content-Type': 'image/jpeg'}
    return jsonify({'error': 'No recent raw frame'}), 404

@app.route('/api/camera/raw_active_frame', methods=['GET'])
def get_raw_active_frame():
    """Return the freshest client webcam frame across all channels in one shot, or 204 if none."""
    now = time.time()
    for cid, t in list(latest_raw_frame_times.items()):
        if now - t < 3.0 and cid in latest_raw_frames:
            return Response(
                latest_raw_frames[cid],
                mimetype='image/jpeg',
                headers={'X-Camera-ID': str(cid)}
            )
    return ('', 204)

def generate_video_stream(camera_id):
    placeholder_bytes = get_placeholder_bytes()
    last_sent_ts = 0.0

    while True:
        now = time.time()
        ai_time = latest_frame_times.get(camera_id, 0.0)
        nvr_time = nvr_frame_cache_times.get(camera_id, 0.0)
        curr_ts = max(ai_time, nvr_time)

        # Only push frame if it's genuinely new or as a heartbeat every 1.5s
        if curr_ts > last_sent_ts or (now - last_sent_ts) > 1.5:
            frame_bytes = fetch_nvr_snapshot(camera_id, max_age=0.2)
            if not frame_bytes:
                frame_bytes = placeholder_bytes

            if frame_bytes:
                last_sent_ts = curr_ts if curr_ts > 0 else now
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.025)  # 40Hz check for minimal latency (<25ms)

@app.route('/api/camera/<int:camera_id>/stream')
def get_camera_stream(camera_id):
    return Response(
        generate_video_stream(camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/camera/<int:camera_id>/snapshot')
def get_camera_snapshot(camera_id):
    snap = fetch_nvr_snapshot(camera_id, max_age=0.4)
    if snap:
        return Response(snap, mimetype='image/jpeg', headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})
    placeholder_bytes = get_placeholder_bytes()
    return Response(placeholder_bytes, mimetype='image/jpeg', headers={'Cache-Control': 'no-cache'})

@app.route('/api/camera/<int:camera_id>/raw_nvr_frame')
def get_raw_nvr_frame(camera_id):
    """Return the raw unannotated frame from NVR for AI detection."""
    if camera_id in nvr_frame_cache and nvr_frame_cache[camera_id]:
        return Response(nvr_frame_cache[camera_id], mimetype='image/jpeg', headers={'Cache-Control': 'no-cache'})
    return ('', 404)

@app.route('/api/camera/channels')
def get_camera_channels():
    cams = [
        {
            'id': cam_id,
            'name': info['name'],
            'lane': info['lane'],
            'channel': info['channel'],
            'stream_url': f'/api/camera/{cam_id}/stream',
            'snapshot_url': f'/api/camera/{cam_id}/snapshot',
            'ai_enabled': (cam_id in active_ai_cameras)
        }
        for cam_id, info in NVR_CHANNELS.items()
    ]
    return jsonify(cams)

# User authentication and session management
import secrets

def get_admin_credentials():
    """Retrieve administrator email and password strictly from environment / .env."""
    email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    password = os.environ.get('ADMIN_PASSWORD', '').strip()
    return email, password

# Active in-memory session tokens: token -> { email, name, role, login_time }
active_auth_tokens = {}

def create_auth_token(email):
    token = secrets.token_hex(24)
    active_auth_tokens[token] = {
        'email': email,
        'name': 'Admin Officer',
        'role': 'Super Admin',
        'login_time': time.time()
    }
    return token

def verify_auth_token(token):
    if not token:
        return None
    session_info = active_auth_tokens.get(token)
    if session_info:
        # Valid for 30 days
        if time.time() - session_info.get('login_time', 0) < 30 * 86400:
            return session_info
        else:
            active_auth_tokens.pop(token, None)
    return None

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Authenticate user with email and password strictly configured in .env."""
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    admin_email, admin_password = get_admin_credentials()

    # Reject if no admin password is configured in .env or password input is empty
    if not admin_password or not password:
        return jsonify({
            'success': False,
            'error': 'Invalid email or password.'
        }), 401

    valid_emails = {admin_email}
    if admin_email and '@' in admin_email:
        valid_emails.add(admin_email.split('@')[0])
    valid_emails.add('admin')

    if email in valid_emails and password == admin_password:
        user_email = admin_email or email
        token = create_auth_token(user_email)
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'email': user_email,
                'name': 'Admin Officer',
                'role': 'Super Admin'
            }
        })
    return jsonify({
        'success': False,
        'error': 'Invalid email or password.'
    }), 401

@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    """Check session token validity."""
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    elif 'token' in request.args:
        token = request.args.get('token')

    session = verify_auth_token(token)
    if session:
        return jsonify({
            'authenticated': True,
            'user': session
        })
    return jsonify({'authenticated': False}), 401

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Sign out user and invalidate session."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
        active_auth_tokens.pop(token, None)
    return jsonify({'success': True})

# AI Engine camera channel selection endpoint

@app.route('/api/ai/cameras', methods=['GET', 'POST'])
def manage_ai_cameras():
    global active_ai_cameras
    if request.method == 'POST':
        data = request.get_json() or {}
        if 'toggle' in data:
            try:
                cid = int(data['toggle'])
                if cid in active_ai_cameras:
                    active_ai_cameras.remove(cid)
                elif 1 <= cid <= len(NVR_CHANNELS):
                    active_ai_cameras.append(cid)
                    active_ai_cameras.sort()
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        elif 'cameras' in data:
            raw_cams = data.get('cameras', [])
            cleaned = []
            for c in raw_cams:
                if str(c).isdigit():
                    cid = int(c)
                    if 1 <= cid <= len(NVR_CHANNELS):
                        cleaned.append(cid)
            active_ai_cameras = sorted(list(set(cleaned)))
            
        logger.info(f"Updated active AI Cameras: {active_ai_cameras}")
        return jsonify({
            'success': True,
            'active_cameras': active_ai_cameras,
            'count': len(active_ai_cameras)
        })

    return jsonify({
        'active_cameras': active_ai_cameras,
        'count': len(active_ai_cameras),
        'total_available': len(NVR_CHANNELS)
    })

# Facility Profile Configuration (Multi-Business Adaptation)
FACILITY_CONFIG_FILE = os.path.join(_curr_dir, 'facility_config.json')

DEFAULT_FACILITY_CONFIG = {
    'name': 'GatePulse AI',
    'subtitle': 'Smart Access & ANPR Vision',
    'icon': '🚘',
    'business_type': 'parking',
    'operation_mode': 'free',
    'total_capacity': 150,
    'overstay_hours': 12
}

def load_facility_config():
    if os.path.exists(FACILITY_CONFIG_FILE):
        try:
            with open(FACILITY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                res = DEFAULT_FACILITY_CONFIG.copy()
                res.update(data)
                return res
        except Exception as e:
            logger.warning(f"Failed to read facility config: {e}")
    return DEFAULT_FACILITY_CONFIG.copy()

def save_facility_config(config):
    try:
        with open(FACILITY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save facility config: {e}")
        return False

# REST API endpoints

@app.route('/api/facility', methods=['GET', 'POST'])
def api_facility():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        current = load_facility_config()
        for key in ['name', 'subtitle', 'icon', 'business_type', 'operation_mode', 'total_capacity', 'overstay_hours']:
            if key in data:
                current[key] = data[key]
        save_facility_config(current)
        return jsonify({'status': 'success', 'facility': current})
    return jsonify(load_facility_config())

@app.route('/api/config', methods=['GET'])
def get_config():
    # Attempt to reconnect if currently in fallback
    global db_status
    if db_status == 'fallback':
        if check_db_health():
            db_status = 'connected'
            
    cameras_list = [
        {
            'id': cam_id,
            'name': info['name'],
            'lane': info['lane'],
            'channel': info['channel'],
            'stream_url': f'/api/camera/{cam_id}/stream',
            'snapshot_url': f'/api/camera/{cam_id}/snapshot',
            'ai_enabled': (cam_id in active_ai_cameras)
        }
        for cam_id, info in NVR_CHANNELS.items()
    ]
    return jsonify({
        'db_status': db_status,
        'db_host': DB_CONFIG['host'],
        'db_database': DB_CONFIG['database'],
        'camera_ids': list(NVR_CHANNELS.keys()),
        'cameras': cameras_list,
        'active_ai_cameras': active_ai_cameras,
        'total_cameras': len(NVR_CHANNELS)
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    total_capacity = 150

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # 1. Vehicles currently parked inside
            cursor.execute("SELECT COUNT(*) as count FROM parking_sessions WHERE status = 'PARKED'")
            currently_parked = (cursor.fetchone() or {}).get('count', 0)

            # 2. Today's entries
            cursor.execute("SELECT COUNT(*) as count FROM parking_sessions WHERE DATE(entry_time) = CURDATE()")
            today_entries = (cursor.fetchone() or {}).get('count', 0)

            # 3. Today's completed exits
            cursor.execute("SELECT COUNT(*) as count FROM parking_sessions WHERE DATE(exit_time) = CURDATE() AND status = 'EXITED'")
            today_exits = (cursor.fetchone() or {}).get('count', 0)

            # 4. Average stay duration today for completed visits (minutes)
            cursor.execute("SELECT AVG(duration_minutes) as avg_m FROM parking_sessions WHERE DATE(exit_time) = CURDATE() AND status = 'EXITED'")
            row_avg = cursor.fetchone() or {}
            avg_m = int(row_avg.get('avg_m') or 0)
            if avg_m == 0:
                cursor.execute("SELECT AVG(duration_minutes) as avg_m FROM parking_sessions WHERE duration_minutes > 0")
                row_avg = cursor.fetchone() or {}
                avg_m = int(row_avg.get('avg_m') or 180)

            # 5. Overstay alerts (> 12 hours)
            cursor.execute("""
                SELECT COUNT(*) as count FROM parking_sessions 
                WHERE status = 'PARKED' AND duration_minutes >= 720
            """)
            overstay_alerts = (cursor.fetchone() or {}).get('count', 0)

            # 6. Breakdown by type currently inside
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN vehicle_type = 'Car' THEN 1 ELSE 0 END) as cars,
                    SUM(CASE WHEN vehicle_type = 'Bike' THEN 1 ELSE 0 END) as bikes,
                    SUM(CASE WHEN vehicle_type = 'SUV' THEN 1 ELSE 0 END) as suvs,
                    SUM(CASE WHEN vehicle_type = 'Microbus' THEN 1 ELSE 0 END) as microbuses
                FROM parking_sessions
                WHERE status = 'PARKED'
            """)
            types = cursor.fetchone() or {}

            cursor.close()
            conn.close()

            available_slots = max(0, total_capacity - currently_parked)
            occupancy_pct = round((currently_parked / total_capacity) * 100, 1)

            dur_str = f"{avg_m // 60}h {avg_m % 60}m" if avg_m >= 60 else f"{avg_m}m"

            return jsonify({
                'currently_parked': currently_parked,
                'today_entries': today_entries,
                'today_exits': today_exits,
                'total_capacity': total_capacity,
                'available_slots': available_slots,
                'occupancy_pct': occupancy_pct,
                'avg_duration_minutes': avg_m,
                'avg_duration_str': dur_str,
                'overstay_alerts': overstay_alerts,
                'cars_inside': types.get('cars') or 0,
                'bikes_inside': types.get('bikes') or 0,
                'suvs_inside': types.get('suvs') or 0,
                # Compatibility fields for legacy frontend widgets
                'total_vehicles': today_entries,
                'total_revenue': 0,
                'bike_count': types.get('bikes') or 0,
                'bus_count': types.get('cars') or 0,
                'truck_count': types.get('suvs') or 0,
                'fraud_alerts': overstay_alerts
            })
        except Exception as e:
            logger.error(f"Error executing parking stats query: {e}")
            if conn: conn.close()

    # Fallback response
    return jsonify({
        'currently_parked': 30,
        'today_entries': 100,
        'today_exits': 70,
        'total_capacity': 150,
        'available_slots': 120,
        'occupancy_pct': 20.0,
        'avg_duration_minutes': 245,
        'avg_duration_str': "4h 05m",
        'overstay_alerts': 2,
        'total_vehicles': 100,
        'total_revenue': 0,
        'bike_count': 10,
        'bus_count': 18,
        'truck_count': 2,
    })

# Time slot and shift calculation helpers

def parse_slot_boundaries(target_date_str, slot_name, custom_start_time=None, custom_end_time=None):
    """Calculate (start_datetime, end_datetime, label) based on 8-hour shift or custom inputs."""
    if not target_date_str:
        target_date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        base_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    except Exception:
        base_date = datetime.now()
        target_date_str = base_date.strftime('%Y-%m-%d')

    if slot_name == 'slot1':  # Morning Shift 06:00 - 14:00 (8 hrs)
        start_dt = base_date.replace(hour=6, minute=0, second=0)
        end_dt = base_date.replace(hour=13, minute=59, second=59)
        label = f"Slot 1: Morning Shift (06:00 AM – 02:00 PM) · {target_date_str}"
    elif slot_name == 'slot2':  # Evening Shift 14:00 - 22:00 (8 hrs / 2 PM - 10 PM)
        start_dt = base_date.replace(hour=14, minute=0, second=0)
        end_dt = base_date.replace(hour=21, minute=59, second=59)
        label = f"Slot 2: Evening Shift (02:00 PM – 10:00 PM) · {target_date_str}"
    elif slot_name == 'slot3':  # Night Shift 22:00 - 06:00 (8 hrs / crosses midnight)
        start_dt = base_date.replace(hour=22, minute=0, second=0)
        next_day = base_date + timedelta(days=1)
        end_dt = next_day.replace(hour=5, minute=59, second=59)
        label = f"Slot 3: Night Shift (10:00 PM – 06:00 AM) · {target_date_str}"
    elif slot_name == 'custom' or (custom_start_time and custom_end_time):
        sh, sm = map(int, (custom_start_time or '00:00').split(':')[:2])
        eh, em = map(int, (custom_end_time or '23:59').split(':')[:2])
        start_dt = base_date.replace(hour=sh, minute=sm, second=0)
        if eh < sh or (eh == sh and em < sm):
            end_dt = (base_date + timedelta(days=1)).replace(hour=eh, minute=em, second=59)
        else:
            end_dt = base_date.replace(hour=eh, minute=em, second=59)
        label = f"Custom Slot ({custom_start_time or '00:00'} – {custom_end_time or '23:59'}) · {target_date_str}"
    else:
        start_dt = base_date.replace(hour=0, minute=0, second=0)
        end_dt = base_date.replace(hour=23, minute=59, second=59)
        label = f"Full Day · {target_date_str}"

    return start_dt, end_dt, label

@app.route('/api/detections', methods=['GET'])
def get_detections():
    since_id = request.args.get('since_id', default=0, type=int)
    limit = request.args.get('limit', default=50, type=int)
    target_date = request.args.get('date', default=None)
    status_filter = request.args.get('status', default=None)
    search_query = request.args.get('search', default=None)
    vehicle_type_filter = request.args.get('vehicle_type', default=None)
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            where_clauses = ["id > %s"]
            params = [since_id]

            if status_filter and status_filter.upper() in ('PARKED', 'EXITED'):
                where_clauses.append("status = %s")
                params.append(status_filter.upper())

            if search_query:
                where_clauses.append("(plate_number LIKE %s OR vehicle_type LIKE %s)")
                params.extend([f"%{search_query}%", f"%{search_query}%"])

            if target_date:
                where_clauses.append("DATE(entry_time) = %s")
                params.append(target_date)

            if vehicle_type_filter:
                where_clauses.append("vehicle_type = %s")
                params.append(vehicle_type_filter)

            where_sql = " AND ".join(where_clauses)
            query = f"""
                SELECT id, plate_number, vehicle_type, entry_time, exit_time, 
                       duration_minutes, status, entry_gate, exit_gate, entry_image, exit_image,
                       confidence, plate_conf, slot_number
                FROM parking_sessions
                WHERE {where_sql}
                ORDER BY entry_time DESC
                LIMIT %s
            """
            params.append(limit)
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            now = datetime.now()
            formatted = []
            for r in results:
                entry_dt = r['entry_time']
                if isinstance(entry_dt, str):
                    try:
                        entry_dt = datetime.fromisoformat(entry_dt)
                    except Exception:
                        pass

                is_parked = (r['status'] == 'PARKED')
                if is_parked and isinstance(entry_dt, datetime):
                    curr_mins = max(1, int((now - entry_dt).total_seconds() / 60))
                else:
                    curr_mins = int(r.get('duration_minutes') or 0)

                if curr_mins >= 60:
                    dur_str = f"{curr_mins // 60}h {curr_mins % 60:02d}m"
                else:
                    dur_str = f"{curr_mins}m"

                entry_str = str(r['entry_time'])
                exit_str = str(r['exit_time']) if r.get('exit_time') else 'Parked Inside'

                formatted.append({
                    'id': r['id'],
                    'plate_number': r['plate_number'] or 'UNREGISTERED',
                    'vehicle_type': r['vehicle_type'] or 'Car',
                    'entry_time': entry_str,
                    'exit_time': exit_str,
                    'duration_minutes': curr_mins,
                    'duration_str': dur_str,
                    'status': r['status'],
                    'entry_gate': r.get('entry_gate') or 'Gate 1 (Entry)',
                    'exit_gate': r.get('exit_gate') or ('Gate 2 (Exit)' if not is_parked else '—'),
                    'slot_number': r.get('slot_number') or 'Unassigned',
                    'image_path': r.get('entry_image') or None,
                    'exit_image': r.get('exit_image') or None,
                    'confidence': float(r.get('confidence') or 95.0),
                    'plate_conf': float(r.get('plate_conf') or 90.0),
                    'toll_amount': 0.00 # Compatibility
                })
                
            cursor.close()
            conn.close()
            return jsonify(formatted)
        except Exception as e:
            logger.error(f"Error querying parking sessions: {e}")
            if conn: conn.close()

    return jsonify([])

@app.route('/api/parking/active', methods=['GET'])
def get_active_parked():
    """Returns vehicles currently parked inside the facility."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, plate_number, vehicle_type, entry_time, entry_gate, entry_image, slot_number, confidence
                FROM parking_sessions
                WHERE status = 'PARKED'
                ORDER BY entry_time DESC
            """)
            rows = cursor.fetchall()
            now = datetime.now()
            for r in rows:
                entry_dt = r['entry_time']
                if isinstance(entry_dt, str):
                    try:
                        entry_dt = datetime.fromisoformat(entry_dt)
                    except Exception:
                        pass
                if isinstance(entry_dt, datetime):
                    mins = max(1, int((now - entry_dt).total_seconds() / 60))
                else:
                    mins = 30
                r['duration_minutes'] = mins
                r['duration_str'] = f"{mins // 60}h {mins % 60:02d}m" if mins >= 60 else f"{mins}m"
                r['entry_time'] = str(r['entry_time'])
            cursor.close()
            conn.close()
            return jsonify(rows)
        except Exception as e:
            logger.error(f"Error getting active parked cars: {e}")
            if conn: conn.close()
    return jsonify([])

@app.route('/api/parking/movement', methods=['POST'])
def log_parking_movement():
    """
    Automated / Manual vehicle movement event:
    Checks if vehicle with same plate is currently PARKED.
    If yes -> Records EXIT, calculates stay duration.
    If no  -> Records ENTRY, assigns status 'PARKED'.
    """
    data = request.json or {}
    plate = data.get('plate_number', '').strip()
    vtype = data.get('vehicle_type', 'Car').strip()
    gate = data.get('gate', 'Gate 1 (Inbound)')
    img_path = data.get('image_path', '')
    conf = float(data.get('confidence', 95.0))
    plate_conf = float(data.get('plate_conf', 90.0))

    if not plate:
        return jsonify({'success': False, 'error': 'Plate number required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database unavailable'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        # Check if vehicle is already parked inside
        cursor.execute("""
            SELECT id, entry_time, slot_number FROM parking_sessions
            WHERE plate_number = %s AND status = 'PARKED'
            ORDER BY id DESC LIMIT 1
        """, (plate,))
        existing = cursor.fetchone()

        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        if existing:
            # Vehicle is exiting!
            entry_dt = existing['entry_time']
            if isinstance(entry_dt, str):
                entry_dt = datetime.fromisoformat(entry_dt)
            duration_mins = max(1, int((now - entry_dt).total_seconds() / 60))
            dur_str = f"{duration_mins // 60}h {duration_mins % 60:02d}m" if duration_mins >= 60 else f"{duration_mins}m"

            cursor.execute("""
                UPDATE parking_sessions
                SET exit_time = %s, duration_minutes = %s, status = 'EXITED',
                    exit_gate = %s, exit_image = %s, updated_at = %s
                WHERE id = %s
            """, (now_str, duration_mins, gate, img_path, now_str, existing['id']))
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'action': 'EXIT',
                'plate_number': plate,
                'vehicle_type': vtype,
                'entry_time': str(existing['entry_time']),
                'exit_time': now_str,
                'duration_minutes': duration_mins,
                'duration_str': dur_str,
                'message': f"Vehicle {plate} EXITED. Total stay: {dur_str}."
            })
        else:
            # Vehicle is entering!
            slot = f"{random.choice(['A','B','C'])}-{random.randint(1, 50):02d}"
            cursor.execute("""
                INSERT INTO parking_sessions
                (plate_number, vehicle_type, entry_time, status, entry_gate, entry_image, confidence, plate_conf, slot_number)
                VALUES (%s, %s, %s, 'PARKED', %s, %s, %s, %s, %s)
            """, (plate, vtype, now_str, gate, img_path, conf, plate_conf, slot))
            conn.commit()
            session_id = cursor.lastrowid
            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'action': 'ENTRY',
                'session_id': session_id,
                'plate_number': plate,
                'vehicle_type': vtype,
                'entry_time': now_str,
                'slot_number': slot,
                'message': f"Vehicle {plate} ENTERED. Assigned slot: {slot}."
            })
    except Exception as e:
        logger.error(f"Error logging parking movement: {e}")
        if conn: conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

    # Fallback Logic
    # Filter by since_id
    filtered = [r for r in mock_records if r['id'] > since_id]
    # Take top limit
    sliced = filtered[:limit]
    
    # Format dates
    formatted = []
    for r in sliced:
        formatted.append({
            **r,
            'entry_time': r['entry_time'].isoformat()
        })
    return jsonify(formatted)

@app.route('/api/detections', methods=['DELETE'])
def delete_detections():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM parking_sessions")
            try:
                cursor.execute("DELETE FROM vehicle_detections")
            except Exception:
                pass
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'All parking records cleared successfully.'})
        except Exception as e:
            logger.error(f"Error clearing parking detections: {e}")
            if conn: conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
            
    # Fallback
    global mock_records
    mock_records.clear()
    return jsonify({'success': True, 'message': 'All fallback detection logs deleted.'})

@app.route('/api/charts/distribution', methods=['GET'])
def get_chart_distribution():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT vehicle_type, COUNT(*) as count
                FROM parking_sessions
                GROUP BY vehicle_type
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            distribution = {}
            for r in results:
                distribution[r['vehicle_type']] = {
                    'count': r['count'],
                    'revenue': 0.0 # Toll fee skipped
                }
                
            cursor.close()
            conn.close()
            return jsonify(distribution)
        except Exception as e:
            logger.error(f"Error getting distribution chart data: {e}")
            if conn: conn.close()

    distribution = {'Car': {'count': 45, 'revenue': 0}, 'Bike': {'count': 22, 'revenue': 0}, 'SUV': {'count': 18, 'revenue': 0}}
    return jsonify(distribution)

@app.route('/api/charts/hourly', methods=['GET'])
def get_chart_hourly():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT HOUR(entry_time) as hour, COUNT(*) as count
                FROM parking_sessions
                WHERE DATE(entry_time) = CURDATE()
                GROUP BY HOUR(entry_time)
                ORDER BY hour
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            hours = [{'hour': i, 'count': 0, 'revenue': 0.0} for i in range(24)]
            for r in results:
                hr = r['hour']
                if 0 <= hr < 24:
                    hours[hr]['count'] = r['count']
                    hours[hr]['revenue'] = 0.0
                    
            cursor.close()
            conn.close()
            return jsonify(hours)
        except Exception as e:
            logger.error(f"Error fetching hourly data: {e}")
            if conn: conn.close()

    hours = [{'hour': i, 'count': random.randint(1, 8), 'revenue': 0.0} for i in range(24)]
    return jsonify(hours)

@app.route('/api/charts/trend', methods=['GET'])
def get_chart_trend():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Today hourly counts
            cursor.execute("""
                SELECT HOUR(entry_time) as hour, COUNT(*) as count
                FROM parking_sessions
                WHERE DATE(entry_time) = CURDATE()
                GROUP BY HOUR(entry_time)
                ORDER BY hour
            """)
            today_res = cursor.fetchall()
            
            # Yesterday hourly counts
            cursor.execute("""
                SELECT HOUR(entry_time) as hour, COUNT(*) as count
                FROM parking_sessions
                WHERE DATE(entry_time) = SUBDATE(CURDATE(), 1)
                GROUP BY HOUR(entry_time)
                ORDER BY hour
            """)
            yest_res = cursor.fetchall()
            
            today = [0] * 24
            yesterday = [0] * 24
            
            for r in today_res:
                today[r['hour']] = int(r['count'])
            for r in yest_res:
                yesterday[r['hour']] = int(r['count'])
                
            cursor.close()
            conn.close()
            return jsonify({
                'today': today,
                'yesterday': yesterday
            })
        except Exception as e:
            logger.error(f"Error fetching trend data: {e}")
            if conn: conn.close()

    return jsonify({
        'today': [random.randint(1, 10) for _ in range(24)],
        'yesterday': [random.randint(1, 8) for _ in range(24)]
    })

@app.route('/api/fraud', methods=['GET'])
def get_fraud_data():
    """Returns parking overstay tracking data (>12h alerts and bay occupancy)."""
    conn = get_db_connection()
    data = {}
    overstay_count = 0

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT vehicle_type,
                       SUM(CASE WHEN status = 'PARKED' THEN 1 ELSE 0 END) as parked,
                       SUM(CASE WHEN status = 'EXITED' THEN 1 ELSE 0 END) as exited,
                       SUM(CASE WHEN status = 'PARKED' AND (strftime('%s', 'now') - strftime('%s', entry_time)) > 43200 THEN 1 ELSE 0 END) as overstay
                FROM parking_sessions
                GROUP BY vehicle_type
            """)
            rows = cursor.fetchall()
            for r in rows:
                t = r['vehicle_type']
                ov = int(r.get('overstay') or 0)
                overstay_count += ov
                data[t] = {
                    'parked': int(r.get('parked') or 0),
                    'exited': int(r.get('exited') or 0),
                    'overstay': ov
                }
            cursor.close()
            conn.close()

            if data:
                return jsonify({
                    'data': data,
                    'overstay_count': overstay_count
                })
        except Exception as e:
            logger.error(f"Error querying parking overstay: {e}")
            if conn: conn.close()

    # Fallback default values
    return jsonify({
        'data': {
            'Car':    {'parked': 14, 'exited': 32, 'overstay': 1},
            'Bike':   {'parked': 8,  'exited': 20, 'overstay': 0},
            'CNG':    {'parked': 4,  'exited': 10, 'overstay': 1},
            'Auto':   {'parked': 2,  'exited': 4,  'overstay': 0},
            'Pickup': {'parked': 1,  'exited': 3,  'overstay': 1},
            'Bus':    {'parked': 1,  'exited': 1,  'overstay': 0}
        },
        'overstay_count': 3
    })

@app.route('/api/rates', methods=['GET'])
def get_rates():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT vehicle_type, rate_amount FROM toll_rates")
            rows = cursor.fetchall()
            
            rates = {r['vehicle_type']: float(r['rate_amount']) for r in rows}
            
            cursor.close()
            conn.close()
            
            # Fill missing types
            for k, v in mock_rates.items():
                if k not in rates:
                    rates[k] = v
                    
            return jsonify(rates)
        except Exception as e:
            logger.error(f"Error fetching rates: {e}")
            if conn: conn.close()
            
    return jsonify(mock_rates)

@app.route('/api/rates', methods=['POST'])
def save_rate():
    data = request.json
    if not data or 'vehicle_type' not in data or 'rate_amount' not in data:
        return jsonify({'success': False, 'message': 'Missing data'}), 400
        
    v_type = data['vehicle_type']
    new_rate = float(data['rate_amount'])
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Get old rate
            cursor.execute("SELECT rate_amount FROM toll_rates WHERE vehicle_type = %s", (v_type,))
            old_row = cursor.fetchone()
            old_rate = float(old_row['rate_amount']) if old_row else TOLL_RATES.get(v_type, 0)
            
            # Update rates
            cursor.execute("""
                INSERT INTO toll_rates (vehicle_type, rate_amount, effective_from, updated_by)
                VALUES (%s, %s, CURDATE(), 'Admin')
                ON DUPLICATE KEY UPDATE rate_amount = %s, updated_by = 'Admin'
            """, (v_type, new_rate, new_rate))
            
            # Audit log
            cursor.execute("""
                INSERT INTO rate_audit_log (vehicle_type, old_rate, new_rate, changed_by)
                VALUES (%s, %s, %s, 'Admin')
            """, (v_type, old_rate, new_rate))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Updated rate for {v_type}: ৳{old_rate} -> ৳{new_rate}")
            return jsonify({'success': True, 'message': f'Updated {v_type} toll rate successfully'})
        except Exception as e:
            logger.error(f"Error updating rate: {e}")
            if conn: conn.close()
            
    # Fallback Logic
    old_rate = mock_rates.get(v_type, 0)
    mock_rates[v_type] = new_rate
    mock_rate_history.insert(0, {
        'type': v_type,
        'oldRate': old_rate,
        'newRate': new_rate,
        'time': datetime.now().strftime('%h:%i %p')
    })
    
    # Update local in-memory records to match new toll rate
    for r in mock_records:
        if r['vehicle_type'] == v_type:
            r['toll_amount'] = new_rate
            
    logger.info(f"[Fallback Mode] Updated rate for {v_type}: ৳{old_rate} -> ৳{new_rate}")
    return jsonify({'success': True, 'message': f'Updated {v_type} rate to ৳{new_rate} (Mock fallback)'})

@app.route('/api/rates/history', methods=['GET'])
def get_rate_history():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT vehicle_type as type, old_rate as oldRate, new_rate as newRate,
                       changed_by as user, DATE_FORMAT(changed_at, '%h:%i %p') as time
                FROM rate_audit_log
                ORDER BY changed_at DESC
                LIMIT 15
            """)
            history = cursor.fetchall()
            
            # Convert decimals to float
            for h in history:
                h['oldRate'] = float(h['oldRate'])
                h['newRate'] = float(h['newRate'])
                
            cursor.close()
            conn.close()
            return jsonify(history)
        except Exception as e:
            logger.error(f"Error querying rate log: {e}")
            if conn: conn.close()
            
    return jsonify(mock_rate_history[:15])

@app.route('/api/reports', methods=['GET'])
def get_report():
    report_type = request.args.get('type', default='daily')
    slot_name = request.args.get('slot', default=None)
    target_date = request.args.get('date', default=None)
    custom_start = request.args.get('start_time', default=None)
    custom_end = request.args.get('end_time', default=None)
    days_back = 0
    if report_type == 'weekly':
        days_back = 7
    elif report_type == 'monthly':
        days_back = 30
        
    conn = get_db_connection()
    report_label = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Query from parking_sessions
            query = """
                SELECT 
                    vehicle_type,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'PARKED' THEN 1 ELSE 0 END) as parked,
                    SUM(CASE WHEN status = 'EXITED' THEN 1 ELSE 0 END) as exited
                FROM parking_sessions
                GROUP BY vehicle_type
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()

            rows = []
            total_count = 0
            for r in results:
                t = r['vehicle_type']
                c = int(r.get('count') or 0)
                rows.append({
                    'vehicle_type': t,
                    'count': c,
                    'parked': int(r.get('parked') or 0),
                    'exited': int(r.get('exited') or 0),
                    'rate': 0,
                    'revenue': 0
                })
                total_count += c

            if rows:
                return jsonify({
                    'rows': rows,
                    'totalCount': total_count,
                    'totalRevenue': 0,
                    'label': report_label,
                    'type': report_type,
                    'slot': slot_name,
                    'date': target_date
                })
        except Exception as e:
            logger.error(f"Error compiling parking report: {e}")
            if conn: conn.close()

    # Fallback Logic
    multiplier = 1
    if report_type == 'weekly':
        multiplier = 7
    elif report_type == 'monthly':
        multiplier = 30
        
    rows = [
        {'vehicle_type': 'Car', 'count': 46 * multiplier, 'parked': 14, 'exited': 32, 'rate': 0, 'revenue': 0},
        {'vehicle_type': 'Bike', 'count': 28 * multiplier, 'parked': 8, 'exited': 20, 'rate': 0, 'revenue': 0},
        {'vehicle_type': 'CNG', 'count': 14 * multiplier, 'parked': 4, 'exited': 10, 'rate': 0, 'revenue': 0},
        {'vehicle_type': 'Auto', 'count': 6 * multiplier, 'parked': 2, 'exited': 4, 'rate': 0, 'revenue': 0},
        {'vehicle_type': 'Pickup', 'count': 4 * multiplier, 'parked': 1, 'exited': 3, 'rate': 0, 'revenue': 0},
        {'vehicle_type': 'Bus', 'count': 2 * multiplier, 'parked': 1, 'exited': 1, 'rate': 0, 'revenue': 0}
    ]
    total_count = sum(r['count'] for r in rows)
        
    return jsonify({
        'rows': rows,
        'totalCount': total_count,
        'totalRevenue': 0
    })

# Video Upload & AI Model Testing Inspection Endpoints

INSPECTION_DIR = os.path.join(ROOT_DIR, 'captured_vehicles', 'inspections')
os.makedirs(INSPECTION_DIR, exist_ok=True)

loaded_yolo_models = {}

def get_yolo_model(model_name='best.pt'):
    clean_name = os.path.basename(model_name)
    model_path = os.path.join(ROOT_DIR, clean_name)
    if not os.path.exists(model_path):
        model_path = os.path.join(ROOT_DIR, 'yolov8s.pt')
        if not os.path.exists(model_path):
            model_path = os.path.join(ROOT_DIR, 'yolov8n.pt')
        clean_name = os.path.basename(model_path)
    if clean_name not in loaded_yolo_models:
        from ultralytics import YOLO
        logger.info(f"Loading YOLO model for inspection: {clean_name}")
        loaded_yolo_models[clean_name] = YOLO(model_path)
    return loaded_yolo_models[clean_name], clean_name

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Returns available YOLO models found in the workspace."""
    models = []
    try:
        for f in os.listdir(ROOT_DIR):
            if f.endswith('.pt') and not f.startswith('.'):
                p = os.path.join(ROOT_DIR, f)
                size_mb = round(os.path.getsize(p) / (1024 * 1024), 1)
                desc = "YOLO Model"
                if f == 'best.pt':
                    desc = "Custom Fine-Tuned Traffic Weights (Recommended)"
                elif f == 'yolov8s.pt':
                    desc = "YOLOv8 Small (Pre-trained Balanced)"
                elif f == 'yolov8n.pt':
                    desc = "YOLOv8 Nano (Ultra-Fast)"
                models.append({
                    'name': f,
                    'size_mb': size_mb,
                    'description': desc,
                    'recommended': (f == 'best.pt')
                })
        models.sort(key=lambda m: (0 if m['name'] == 'best.pt' else 1, m['name']))
    except Exception as e:
        logger.error(f"Error scanning models: {e}")

    default_model = 'best.pt' if any(m['name'] == 'best.pt' for m in models) else (models[0]['name'] if models else 'yolov8s.pt')
    return jsonify({
        'models': models,
        'default': default_model
    })

@app.route('/api/model/inspect-video', methods=['POST'])
def inspect_uploaded_video():
    """
    Analyzes an uploaded or sample video with the selected YOLO model & ANPR OCR,
    outputs the annotated video and detailed vehicle detection analytics.
    """
    import cv2
    from anpr_engine import get_anpr_engine

    model_name = request.form.get('model', 'best.pt')
    conf_threshold = float(request.form.get('confidence', 0.20))
    enable_ocr = request.form.get('enable_ocr', 'true').lower() == 'true'
    max_frames = int(request.form.get('max_frames', 350))
    frame_step = max(1, int(request.form.get('frame_step', 2)))

    task_id = f"inspect_{int(time.time())}_{random.randint(100, 999)}"
    temp_input = None

    # Handle file upload or sample video
    if 'video' in request.files and request.files['video'].filename:
        vfile = request.files['video']
        ext = os.path.splitext(vfile.filename)[1] or '.mp4'
        temp_input = os.path.join(INSPECTION_DIR, f"input_{task_id}{ext}")
        vfile.save(temp_input)
        video_source = temp_input
    else:
        sample_name = request.form.get('sample_video', 'traffic.mp4')
        sample_path = os.path.join(ROOT_DIR, sample_name)
        if not os.path.exists(sample_path):
            sample_path = os.path.join(ROOT_DIR, 'ai_engine', sample_name)
        if not os.path.exists(sample_path):
            sample_path = os.path.join(ROOT_DIR, 'python', sample_name)
        if not os.path.exists(sample_path):
            return jsonify({'success': False, 'error': f"Sample video '{sample_name}' not found"}), 400
        video_source = sample_path

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        return jsonify({'success': False, 'error': 'Could not open video file.'}), 400

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_file_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Target resolution for fast web playback (maximum 960x540)
    out_w = min(orig_w, 960)
    out_h = int(orig_h * (out_w / orig_w))
    out_h = out_h if out_h % 2 == 0 else out_h + 1
    out_w = out_w if out_w % 2 == 0 else out_w + 1

    out_filename = f"annotated_{task_id}.mp4"
    out_path = os.path.join(INSPECTION_DIR, out_filename)

    # Try browser-compatible H.264 codec (avc1) first, fallback to mp4v
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out_writer = cv2.VideoWriter(out_path, fourcc, max(10.0, fps / frame_step), (out_w, out_h))
    if not out_writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(out_path, fourcc, max(10.0, fps / frame_step), (out_w, out_h))

    yolo, actual_model_name = get_yolo_model(model_name)
    anpr = get_anpr_engine() if enable_ocr else None

    # Color palette per vehicle type
    color_map = {
        'Bike':        (241, 102, 99),
        'CNG':         (50, 205, 50),
        'Auto':        (0, 190, 230),
        'Pickup':      (0, 215, 255),
        'Car':         (246, 130, 59),
        'Covered Van': (230, 150, 0),
        'Bus':         (255, 165, 0),
        'Truck':       (68, 68, 239),
        'Lorry':       (252, 132, 192),
        'Unknown':     (148, 163, 184)
    }

    from ai_engine import classify_vehicle

    detections = []
    vehicle_counts = {}
    total_plates_read = 0
    processed_count = 0
    frame_idx = 0
    t_start = time.time()

    # Track seen vehicles to avoid duplicate recording in analytics
    tracked_plate_history = set()

    while cap.isOpened() and processed_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % frame_step != 0:
            continue

        processed_count += 1
        resized_frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)

        # Run inference
        results = yolo(resized_frame, conf=conf_threshold, verbose=False)
        frame_detections = []

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                score = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = results[0].names.get(cls_id, 'vehicle')

                v_type = classify_vehicle(cls_name, cls_id, xyxy)
                x1, y1, x2, y2 = map(int, xyxy)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(out_w, x2), min(out_h, y2)

                # Plate extraction & ANPR
                plate_num = ""
                plate_score = 0.0
                if anpr and (x2 - x1) > 40 and (y2 - y1) > 40:
                    plate_roi = anpr.extract_plate_region(resized_frame, (x1, y1, x2, y2))
                    if plate_roi is not None and plate_roi.size > 0:
                        ocr_res = anpr.recognize_plate(plate_roi)
                        if ocr_res.get('success'):
                            plate_num = ocr_res.get('plate_number', '')
                            plate_score = ocr_res.get('confidence', 0.0)

                # Save a high-quality crop of the vehicle
                crop_rel_path = ""
                if (x2 - x1) > 30 and (y2 - y1) > 30 and (len(detections) < 50):
                    crop_img = resized_frame[y1:y2, x1:x2]
                    if crop_img.size > 0:
                        crop_fname = f"crop_{task_id}_{processed_count}_{len(frame_detections)}.jpg"
                        crop_fpath = os.path.join(INSPECTION_DIR, crop_fname)
                        cv2.imwrite(crop_fpath, crop_img)
                        crop_rel_path = f"/captured_vehicles/inspections/{crop_fname}"

                det_info = {
                    'frame': processed_count,
                    'timestamp_sec': round(frame_idx / fps, 1),
                    'time_str': f"{int(frame_idx/fps//60):02d}:{int(frame_idx/fps%60):02d}.{int((frame_idx/fps%1)*10)}",
                    'vehicle_type': v_type,
                    'confidence': round(score * 100, 1),
                    'status': 'VERIFIED' if plate_num else 'TRACKED',
                    'plate_number': plate_num or f"UNREGISTERED-{random.randint(100,999)}",
                    'plate_confidence': plate_score,
                    'crop_url': crop_rel_path,
                    'bbox': [x1, y1, x2, y2]
                }
                frame_detections.append(det_info)

                # Update global stats
                p_key = f"{v_type}_{plate_num or (x1 // 60)}"
                if p_key not in tracked_plate_history:
                    tracked_plate_history.add(p_key)
                    vehicle_counts[v_type] = vehicle_counts.get(v_type, 0) + 1
                    if plate_num:
                        total_plates_read += 1
                    detections.append(det_info)

                # Visual annotation on frame
                box_color = color_map.get(v_type, (0, 255, 0))
                cv2.rectangle(resized_frame, (x1, y1), (x2, y2), box_color, 2)

                # Label text
                label = f"{v_type} ({int(score*100)}%)"
                if plate_num:
                    label += f" | {plate_num}"

                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(resized_frame, (x1, max(0, y1 - lh - 8)), (x1 + lw + 6, max(0, y1)), box_color, -1)
                cv2.putText(resized_frame, label, (x1 + 3, max(10, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw top HUD info banner
        hud_text = f"GatePulse AI: {actual_model_name} | Frame: {processed_count} | Detected Vehicles: {len(tracked_plate_history)}"
        cv2.rectangle(resized_frame, (0, 0), (out_w, 28), (15, 23, 42), -1)
        cv2.putText(resized_frame, hud_text, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (56, 189, 248), 1, cv2.LINE_AA)

        out_writer.write(resized_frame)

    cap.release()
    out_writer.release()

    duration = round(time.time() - t_start, 2)
    infer_fps = round(processed_count / max(0.1, duration), 1)

    # Clean up uploaded input file
    if temp_input and os.path.exists(temp_input):
        try:
            os.remove(temp_input)
        except Exception:
            pass

    return jsonify({
        'success': True,
        'video_url': f"/captured_vehicles/inspections/{out_filename}",
        'download_url': f"/captured_vehicles/inspections/{out_filename}",
        'stats': {
            'model_used': actual_model_name,
            'conf_threshold': conf_threshold,
            'total_source_frames': total_file_frames,
            'processed_frames': processed_count,
            'processing_time_sec': duration,
            'fps': infer_fps,
            'total_vehicles': len(tracked_plate_history),
            'plates_recognized': total_plates_read,
            'by_type': vehicle_counts
        },
        'detections': detections[:60]
    })

@app.route('/api/ocr/test-plate', methods=['POST'])
def test_plate_ocr():
    """Direct ANPR / OCR testing endpoint on uploaded license plate image."""
    try:
        from anpr_engine import get_anpr_engine
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided in upload.'}), 400

        img_file = request.files['image']
        if not img_file.filename:
            return jsonify({'success': False, 'error': 'Empty image filename.'}), 400

        file_bytes = np.frombuffer(img_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'success': False, 'error': 'Could not decode image. Please upload a valid JPG or PNG.'}), 400

        anpr = get_anpr_engine()
        # 1. Try recognition on whole uploaded image
        res = anpr.recognize_plate(img)

        # 2. If nothing found and image is a larger vehicle shot, try lower half (standard plate position)
        if not res.get('success') and img.shape[0] > 120 and img.shape[1] > 150:
            h, w = img.shape[:2]
            lower_half = img[int(h * 0.45):h, int(w * 0.05):int(w * 0.95)]
            res_lower = anpr.recognize_plate(lower_half)
            if res_lower.get('success') and res_lower.get('confidence', 0) > res.get('confidence', 0):
                res = res_lower

        plate_num = res.get('plate_number', '')
        conf = res.get('confidence', 0.0)
        raw = res.get('raw_text', '')

        if not plate_num and raw == 'OCR_UNAVAILABLE':
            return jsonify({
                'success': False,
                'plate_number': 'OCR Engine Initializing',
                'confidence': 0.0,
                'raw_text': 'EasyOCR model is initializing or not installed.',
                'error': 'OCR engine is not ready.'
            })

        return jsonify({
            'success': bool(plate_num),
            'plate_number': plate_num or 'No License Plate Detected',
            'confidence': conf,
            'raw_text': raw or 'No clear alphanumeric characters identified',
            'error': None if plate_num else 'Could not detect clear license plate numbers in this image. Please upload a closer, higher-contrast crop of the vehicle plate.'
        })
    except Exception as e:
        logger.error(f"test_plate_ocr error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'plate_number': 'Processing Error',
            'confidence': 0.0,
            'raw_text': '',
            'error': f'ANPR processing error: {str(e)}'
        }), 500

# Application server execution

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Serving AI Toll Monitor web files from: {ROOT_DIR}")
    logger.info(f"Starting Flask server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

