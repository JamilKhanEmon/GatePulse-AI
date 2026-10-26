---
title: GatePulse AI — Smart Access & ANPR Vision
emoji: 🚘
colorFrom: blue
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# 🚘 GatePulse AI — Smart Access & ANPR Vision
### Enterprise Computer Vision System for Automated Vehicle Detection, ANPR, Parking Operations & Toll Management

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLO-v8%20%7C%20v11-00FFFF?style=for-the-badge&logo=ultralytics&logoColor=black)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![EasyOCR](https://img.shields.io/badge/EasyOCR-Bengali%20%26%20English-green?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-Backend%20API-black?style=for-the-badge&logo=flask&logoColor=white)
![SQLite/MySQL](https://img.shields.io/badge/Database-MySQL%20%2F%20SQLite-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## 📌 Table of Contents
1. [Overview](#-overview)
2. [Key Features & Capabilities](#-key-features--capabilities)
3. [System Architecture](#-system-architecture)
4. [How It Works (End-to-End Pipeline)](#-how-it-works-end-to-end-operational-pipeline)
5. [Supported Vehicle Classes & ANPR](#-supported-vehicle-classes--anpr)
6. [Project Directory Structure](#-project-directory-structure)
7. [Security & Public Repository Safety](#-security--public-repository-safety)
8. [Installation & Local Setup](#-installation--local-setup)
9. [Docker & Cloud Deployment](#-docker--cloud-deployment)
10. [Configuration (.env Reference)](#-configuration-env-reference)
11. [REST API Documentation](#-rest-api-documentation)
12. [Shift Timing & Reporting System](#-shift-timing--reporting-system)
13. [Troubleshooting & FAQ](#-troubleshooting--faq)
14. [License & Credits](#-license--credits)

---

## 📖 Overview

**GatePulse AI** is a production-grade, end-to-end computer vision platform designed for highway toll plazas, bridge collection booths, commercial parking facilities, and smart city checkpoints.

The platform bridges real-time computer vision inference with transactional facility management:
* **Real-time Vehicle Detection:** Powered by state-of-the-art **Ultralytics YOLOv8 / YOLO11** deep learning models running on RTSP camera streams, local webcams, or video files.
* **Automatic Number Plate Recognition (ANPR / ALPR):** High-accuracy Bengali (বাংলা) and English license plate recognition fine-tuned for Bangladesh BRTA standard formats with geometric region-of-interest (ROI) extraction and digit/metro transliteration.
* **Smart Parking & Toll Operations:** Tracks entry timestamps, exit timestamps, duration, occupancy rates, and automated fee calculations based on dynamic rate schedules.
* **Audit & Fraud Detection:** Detects discrepancies between visual vehicle classification and declared toll categories, flags duplicate plate registrations, and prevents stationary vehicle double-counting.
* **Executive Web Dashboard:** A responsive single-page application (SPA) featuring real-time statistics counters, live video streams, multi-camera grid views (up to 14 channels), interactive charts, 3-shift reports, and export options (PDF / Excel).

---

## 🌟 Key Features & Capabilities

### 1. 🎥 Real-Time Multi-Camera Streaming
* **Multi-Source Support:** Ingests feeds from RTSP IP cameras (Hikvision, Dahua, Uniview, generic ONVIF), local USB webcams, test video files (`.mp4`), or mock feeds.
* **Multi-Camera Grid:** Monitor up to 14 concurrent camera channels simultaneously in a responsive grid.
* **Low-Latency Streaming:** Efficient MJPEG multipart frame streaming with frame dropping and background threading to prevent browser buffer stalling.

### 2. 🧠 AI Vehicle Detection & Tracking
* **9+ Classified Vehicle Categories:** Specifically adapted for regional South Asian traffic mixes including Cars, Microbuses, SUVs, Trucks, Buses, Motorcycles/Bikes, and CNG Auto-rickshaws.
* **Spatial Deduplication & Stationary Suppression:** Employs Intersection-over-Union (IoU) overlap suppression and cooldown timers so stationary or slow-moving vehicles are not counted repeatedly.
* **High-Confidence Filtering:** Configurable confidence thresholds (`YOLO_CONF_THRESHOLD`) and bounding box geometric validation.

### 3. 🔍 ANPR / ALPR (Bangladeshi BRTA & International Plates)
* **Dual Language Recognition:** Recognizes both English and Bengali (বাংলা) characters (e.g., `ঢাকা মেট্রো-গ ১১-১২৩৪` $\rightarrow$ `Dhaka Metro-Ga 11-1234`).
* **District & Metro Transliteration:** Automatically normalizes recognized regional prefixes (`ঢাকা`, `চট্টগ্রাম`, `সিলেট`, `রাজশাহী`, `খুলনা`, `বরিশাল`, `রংপুর`, `ময়মনসিংহ`, `কুমিল্লা`, `গাজীপুর`, `নারায়ণগঞ্জ`).
* **Digit Normalization:** Automatically converts Bengali numeral glyphs (`০-৯`) into standard digital numerals (`0-9`).

### 4. 💰 Automated Revenue & Parking Management
* **Dual Operation Mode:** Operates as a **Toll Collection System** (fixed rate per vehicle type) or a **Smart Parking Facility** (hourly duration tracking, parking slot assignment, entry/exit gates).
* **Configurable Rate Schedules:** Manage and update tariffs per vehicle category via the web UI or API with real-time database synchronization.
* **Real-Time Financial Metrics:** Tracks daily revenue, hourly flow, peak vehicle volume, and shift-wise collection totals.

### 5. 🛡️ Fraud Detection & Discrepancy Auditing
* **Visual vs. Category Audit:** Flags instances where a heavy vehicle (e.g., Truck or Bus) is charged under a light vehicle category (e.g., Car or CNG).
* **Plate Anomaly Alerts:** Flags unregistered plates, low-confidence OCR reads, and rapid duplicate entries across different gates.

### 6. 📊 3-Shift Operational Reports & Data Export
* **Standard 8-Hour Facility Shifts:**
  * **Shift 1 (Morning):** 06:00 AM – 02:00 PM (06:00 – 14:00)
  * **Shift 2 (Evening):** 02:00 PM – 10:00 PM (14:00 – 22:00)
  * **Shift 3 (Night):** 10:00 PM – 06:00 AM (22:00 – 06:00, crosses midnight)
* **Custom Time Slot Filter:** Filter traffic records by custom date ranges and arbitrary start/end hours.
* **Export Options:** Download formatted audit reports in **PDF** (via jsPDF AutoTable) and **Excel spreadsheet** (via SheetJS).

### 7. 🧪 AI Model Inspector & Video Analyzer
* Built-in interactive testing tool in the web dashboard:
  * Upload custom video clips or plate photos.
  * Select YOLO model weights dynamically (`yolov8n.pt`, `yolov8s.pt`, or custom trained weights).
  * Run inference and view annotated bounding boxes, detected vehicle counts, and extracted plates with confidence metrics.

### 8. 🔄 Resilient Hybrid Database Architecture
* **Zero-Config SQLite Fallback:** Automatically initializes and manages a local SQLite database (`gatepulse.db`) when running in serverless, local test, or cloud environments (such as Hugging Face Spaces).
* **Enterprise MySQL Support:** Seamlessly switches to MySQL / MariaDB in production environments when host credentials are provided.

---

## 🏗️ System Architecture

```text
 ┌────────────────────────────────────────────────────────────────┐
 │                      INPUT VIDEO SOURCES                       │
 │  RTSP IP Cameras  │  NVR Channels  │  Webcams  │  MP4 Videos   │
 └──────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
 ┌────────────────────────────────────────────────────────────────┐
 │                     AI ENGINE (Python)                         │
 │                                                                │
 │  ┌──────────────────────┐        ┌──────────────────────────┐  │
 │  │ Ultralytics YOLOv8   │        │ ANPR Engine (EasyOCR)    │  │
 │  │ Vehicle Detection    ├───────►│ Plate ROI Extraction     │  │
 │  │ & Tracking           │        │ Bengali & English OCR    │  │
 │  └──────────┬───────────┘        └─────────────┬────────────┘  │
 │             │                                  │               │
 │             └─────────────────┬────────────────┘               │
 │                               ▼                                │
 │                Deduplication & Cooldown Logic                  │
 └──────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
 ┌────────────────────────────────────────────────────────────────┐
 │               DATABASE ADAPTER (db_adapter.py)                 │
 │     Primary: MySQL Server  ◄──────►  Fallback: SQLite3         │
 └──────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
 ┌────────────────────────────────────────────────────────────────┐
 │                   FLASK REST API & STREAMER                    │
 │   /api/detections  │  /api/stats  │  /api/reports  │  /stream  │
 └──────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
 ┌────────────────────────────────────────────────────────────────┐
 │                 WEB FRONTEND (SPA Dashboard)                   │
 │   HTML5 / CSS3 / Vanilla JS / Bootstrap 5 / Chart.js / jsPDF   │
 └────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ How It Works (End-to-End Operational Pipeline)

The system operates across six synchronized stages from raw camera frame ingestion to real-time dashboard analytics:

```text
 1. Video Ingestion ──► 2. YOLO AI Detect ──► 3. ANPR OCR ──► 4. Dual Mode Logic ──► 5. Database ──► 6. Live Dashboard
    (RTSP/Webcam/MP4)    (9 Categories)       (BRTA Plates)     (Free vs Paid Mode)      (MySQL/SQLite)   (14-Cam / Reports)
```

### Stage 1: Video Ingestion & Multi-Camera Polling
* **Video Sources:** Ingests live video from RTSP IP cameras (NVR channels 1–14), local USB webcams (`/dev/video0`), or `.mp4` video files.
* **Non-Blocking Architecture:** Dedicated background threads continuously poll frames into an in-memory queue. This prevents video buffer accumulation and guarantees sub-second latency across all channels.
* **Dynamic Stream Routing:** The web dashboard can dynamically subscribe to any camera channel via low-overhead MJPEG multipart streams (`/api/camera/<id>/stream`).

### Stage 2: AI Vehicle Detection & Tracking (YOLOv8 / YOLO11)
* **Model Inference:** Each video frame is processed through fine-tuned YOLO object detection models (`best.pt`, `yolov8s.pt`, or `yolov8n.pt`).
* **9 Vehicle Classes:** Accurately classifies regional traffic into Bike, CNG/Auto, Car, SUV, Microbus, Pickup, Bus, Truck, and Heavy Trailer.
* **Centroid Tracking & Movement:** Tracks vehicles across successive frames to determine inbound (entry) or outbound (exit) movement.
* **Stationary Cooldown & Overlap Prevention:** Employs Intersection-over-Union (IoU) overlap filtering and a cooldown timer (`STATIONARY_COOLDOWN=120s`). When a car stops at an entrance barrier or gate, it is logged exactly once and never double-counted.

### Stage 3: Automatic Number Plate Recognition (ANPR / ALPR)
* **ROI Extraction:** Once a vehicle bounding box exceeds the confidence threshold (`YOLO_CONF_THRESHOLD`), the vehicle image is cropped and the bumper/license plate region is isolated.
* **Image Preprocessing:** Applies grayscale conversion, adaptive thresholding, and contrast normalization to enhance plate legibility under varying lighting conditions.
* **Dual-Script EasyOCR:** Recognizes both Bengali (বাংলা) and English alphanumeric characters according to Bangladesh BRTA standards (e.g., `ঢাকা মেট্রো-গ ১১-১২৩৪` $\rightarrow$ `Dhaka Metro-Ga 11-1234`).
* **Plate Deduplication:** Enforces a configurable plate cooldown (`PLATE_COOLDOWN=60s`), preventing rapid duplicate logs of the same registration number.

### Stage 4: Multi-Business Adaptation & Dual Operation Modes
The platform is designed to adapt to any business or facility profile dynamically via the web settings panel:
* 🟢 **Free Security & Vehicle Log Mode (Hospitals, Corporate Offices, Hotels, Residential Gates):**
  * Focuses purely on perimeter security, vehicle logging, and facility occupancy.
  * Records entry timestamp, exit timestamp, stay duration (e.g. `1h 45m`), plate number, and vehicle category.
  * Completely hides financial tariffs and toll fee columns from the operator view.
* 🟡 **Commercial Paid / Tariff Mode (Commercial Parking Plazas, Shopping Malls, Highway Toll Plazas):**
  * Automatically calculates parking charges or toll fees based on vehicle class, customized tariff schedules, and duration.
  * Enables revenue tracking, cashier shift audits, and fee receipt generation.
* **Dynamic White-Label Facility Branding:**
  * Admin can customize the Facility Name (e.g., *General Hospital*, *Corporate Tower*, *City Mall*), Gate Subtitle, Brand Icon, Total Slot Capacity, and Overstay Alert Threshold.
  * The entire UI (sidebar branding, topbar title, browser tab title, login window, PDF/Excel export headers) updates in real-time without code changes.

### Stage 5: Resilient Hybrid Database Storage
* **Dual-Engine Architecture:** Operates with **MySQL / MariaDB** in enterprise production setups, and automatically falls back to a zero-configuration local **SQLite3** database (`gatepulse.db`) if MySQL is offline or when running in serverless/cloud environments (e.g., Hugging Face Spaces).
* **Zero Data Loss:** All vehicle movements, timestamps, plate numbers, durations, and facility configurations persist seamlessly across restarts.

### Stage 6: Executive Web Dashboard & Shift Auditing
* **Live Overview:** Real-time counters displaying Currently Parked Vehicles, Available Slots, Total Daily Entries, Completed Exits, and Overstay Alerts.
* **Multi-Camera Matrix:** Switch between Single Focus, Dual Camera View, Quad View, and Full 14-Channel NVR Grid with live radar status indicators.
* **3-Shift Standard Reporting:**
  * **Morning Shift:** 06:00 AM – 02:00 PM
  * **Evening Shift:** 02:00 PM – 10:00 PM
  * **Night Shift:** 10:00 PM – 06:00 AM (crosses midnight)
* **Instant Export:** Generate official audit-ready reports in **PDF** (via jsPDF AutoTable) and **Excel** (via SheetJS) with dynamic facility branding.


---

## 🚙 Supported Vehicle Classes & ANPR

### Vehicle Classifications
| Vehicle Class | Description | Standard Rate (BDT/Sample) |
| :--- | :--- | :--- |
| **Bike** | Motorcycle, Scooter, Two-wheeler | ৳ 20 |
| **CNG / Auto** | 3-Wheeler Auto-rickshaw (CNG, Mishuk, Easybike) | ৳ 30 |
| **Car** | Sedan, Hatchback, Taxi | ৳ 80 |
| **SUV** | Jeep, Compact SUV, Station Wagon | ৳ 100 |
| **Microbus** | HiAce, Minivan, Noah, Passenger Van | ৳ 100 |
| **Pickup** | Small commercial transport truck, Pickup van | ৳ 120 |
| **Bus** | City Bus, Inter-district Coach, Minibus | ৳ 150 |
| **Truck** | Commercial Cargo Truck (2/3/4 axle) | ৳ 200 |
| **Trailer / Heavy** | Multi-axle Heavy Transport, Container Carrier | ৳ 300 |

### License Plate Format Support
* **Bangladesh BRTA Format:** `[Metro/District] [Category Letter] [Series]-[Registration Number]`
  * Example: `Dhaka Metro-Ga 11-4821` / `ঢাকা মেট্রো-গ ১১-৪৮২১`
* **Transliteration Engine:** Converts Bengali script characters to standardized English database records while preserving the original image crop for legal audit trails.

---

## 📁 Project Directory Structure

```text
tole/
├── frontend/                     # Modern Single-Page Application (SPA)
│   ├── index.html                # Main executive dashboard
│   └── assets/                   # Static design system & modules
│       ├── css/
│       │   └── style.css         # Dark-themed enterprise styling
│       ├── js/                   # Modular client-side architecture
│       │   ├── app.js            # Router, authentication, toasts
│       │   ├── dashboard.js      # Metrics counter & live polling
│       │   ├── detection-table.js# Live vehicle detection feed
│       │   ├── charts.js         # Chart.js analytics visualizations
│       │   ├── fraud.js          # Discrepancy & fraud auditing
│       │   ├── rates.js          # Vehicle tariff schedule manager
│       │   ├── reports.js        # 3-Shift reporting & PDF/Excel export
│       │   ├── inspector.js      # Video analysis & ANPR verification
│       │   └── data-generator.js # In-browser client simulation
│       └── img/                  # UI branding & vehicle visuals
│
├── backend/                      # High-Performance Flask Backend & APIs
│   ├── server.py                 # REST APIs, MJPEG camera streamer & auth
│   ├── db_adapter.py             # Resilient hybrid database (MySQL + SQLite)
│   ├── env_loader.py             # 12-Factor environment loader
│   ├── schema.sql                # Relational database schema
│   ├── demo_data_generator.py    # Database seeder for demo visits
│   └── test_connection.py       # Database connectivity diagnostic tool
│
├── ai_engine/                    # Computer Vision & Deep Learning Core
│   ├── ai_engine.py              # YOLOv8 vehicle detection & tracking loop
│   ├── anpr_engine.py            # Bengali & English OCR transliteration
│   └── train.py                  # Custom YOLO training & fine-tuning script
│
├── docs/                         # Extended Deployment & Planning Guides
│   ├── DEPLOYMENT.md             # On-premise Linux & cloud server deployment
│   ├── HUGGINGFACE.md            # Hugging Face Spaces Docker setup
│   └── plane.md                  # Project implementation plan
│
├── .env.example                  # Environment configuration template
├── .gitignore                    # Production-grade git exclusion rules
├── Dockerfile                    # Container configuration
├── entrypoint.sh                 # Container & service initialization runner
├── requirements.txt              # Top-level Python dependencies
└── README.md                     # System documentation
```

---

## 🔒 Security & Public Repository Safety

When publishing this repository to **GitHub**, **GitLab**, or **Hugging Face**, follow these security best practices:

1. **No Hardcoded Secrets:**
   * Passwords, API tokens, secret keys, and database passwords are **never** committed to version control.
   * Authentication credentials are read strictly from `.env` or system environment variables.
2. **Ignored Sensitive Files:**
   * `.gitignore` is pre-configured to strictly ignore `.env`, `.env.*` (except `.env.example`), `*.log`, `*.db`, `*.sqlite`, `*.pem`, `*.key`, and `captured_vehicles/`.
3. **Heavy Binary & Media Protection:**
   * Large PyTorch weights (`*.pt`, `*.bin`, `*.weights`) and video recordings (`*.mp4`, `*.avi`) are excluded from Git to prevent repository bloat and potential intellectual property leaks.
4. **Git Remote Token Notice:**
   * Avoid embedding personal access tokens directly inside Git remote URLs (e.g., `https://token@git-provider.com/...`). Use standard SSH keys or credential managers instead.

---

## 💻 Installation & Local Setup

### Prerequisites
* **Python:** 3.10 or higher recommended.
* **Operating System:** Linux, macOS, or Windows (WSL2 recommended for Windows).
* **Hardware:** Minimum 4GB RAM (CPU inference supported). NVIDIA GPU with CUDA recommended for high-FPS multi-stream setups.

### Step 1: Clone Repository
```bash
git clone <your-repository-url>
cd <project-folder>
```

### Step 2: Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment
Copy the sample environment file to create your local `.env`:
```bash
cp .env.example .env
```
Open `.env` and set your preferred admin password and camera sources (default credentials provided below):
```ini
ADMIN_EMAIL=admin@smartfacility.com
ADMIN_PASSWORD=Admin@2026Secure!
PORT=5002
CAM1_SOURCE=0               # 0 = Default webcam, or path to an MP4 video file
```
> [!NOTE]
> Use `admin@smartfacility.com` and `Admin@2026Secure!` to log into the administrator portal on your first launch. You can change these credentials at any time in `.env`.


### Step 5: (Optional) Set up MySQL Database
If you wish to use MySQL instead of the automatic SQLite database:
```bash
mysql -u root -p < backend/schema.sql
```
Update `DB_HOST`, `DB_USER`, `DB_PASSWORD` in your `.env`.

### Step 6: Launch Application
You can run the web server and the AI engine together or separately:

**Option A — Automated Runner:**
```bash
chmod +x entrypoint.sh
./entrypoint.sh
```

**Option B — Run Services in Separate Terminals:**

*Terminal 1 (Web & API Server):*
```bash
python backend/server.py
```

*Terminal 2 (AI Vision Engine):*
```bash
python ai_engine/ai_engine.py --source 0 --model yolov8s.pt
# Or use a video file:
# python ai_engine/ai_engine.py --source traffic.mp4 --model yolov8s.pt
```

Open your browser and navigate to:
```
http://localhost:5002
```

---

## 🐳 Docker & Cloud Deployment

### Run via Docker Locally
```bash
# Build the Docker image
docker build -t smartpark-ai .

# Run container on port 7860
docker run -d -p 7860:7860 \
  -e ADMIN_EMAIL=admin@facility.local \
  -e ADMIN_PASSWORD=StrongPassword123 \
  smartpark-ai
```
Visit `http://localhost:7860` in your web browser.

### Deploy to Hugging Face Spaces
This repository includes native Hugging Face Spaces configuration:
1. Create a new Space on [Hugging Face](https://huggingface.co/new-space).
2. Select **Docker** SDK with the **Blank** template.
3. Push your repository:
   ```bash
   git remote add hf <your-space-git-url>
   git push -u hf master
   ```
4. The space will automatically build using `Dockerfile`, set up the SQLite database, and launch the real-time AI loop.

---

## ⚙️ Configuration (.env Reference)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5002` | Port for Flask web server (`7860` for Hugging Face Spaces). |
| `ADMIN_EMAIL` | `admin@facility.local` | Primary email for dashboard login. |
| `ADMIN_PASSWORD` | *(None)* | Password for dashboard login. Must be set in `.env`. |
| `SECRET_KEY` | *(Random)* | Secret key used for signing session tokens. |
| `DB_HOST` | `localhost` | MySQL host address (if MySQL is running). |
| `DB_PORT` | `3306` | MySQL port number. |
| `DB_NAME` | `gatepulse_db` | Target database name. |
| `DB_USER` | `root` | Database username. |
| `DB_PASSWORD` | `""` | Database password. |
| `CAM1_SOURCE` | `0` | Camera 1 source: `0` for webcam, file path (`traffic.mp4`), or `rtsp://...` |
| `CAM2_SOURCE` | `0` | Camera 2 source. |
| `ACTIVE_CAMERAS` | `1` | Comma-separated list of active camera IDs (`1`, `1,2`, etc.). |
| `YOLO_MODEL` | `yolov8s.pt` | Ultralytics model weights file (`yolov8n.pt`, `yolov8s.pt`, `best.pt`). |
| `YOLO_CONF_THRESHOLD` | `0.16` | Minimum confidence score for vehicle detections. |
| `PLATE_COOLDOWN` | `60` | Cooldown period (in seconds) to avoid duplicate plate detection entries. |
| `STATIONARY_COOLDOWN` | `120` | Cooldown period (in seconds) to suppress stationary vehicles. |

---

## 🔌 REST API Documentation

### Authentication Endpoints
* `POST /api/auth/login` — Authenticates credentials and issues a session token.
* `GET /api/auth/me` — Verifies current session token validity.
* `POST /api/auth/logout` — Invalidates active session token.

### Camera & Video Streaming
* `GET /api/camera/<id>/stream` — Live MJPEG video stream with bounding boxes and HUD overlays.
* `GET /api/camera/<id>/snapshot` — Current high-resolution JPEG frame.
* `GET /api/camera/channels` — Status list of all available camera feeds (1 to 14).
* `POST /api/ai/cameras` — Dynamically toggle which camera feeds are actively processed by the AI engine.

### Detection & Operational Data
* `GET /api/detections` — Paginated list of recent vehicle detections with plate, type, timestamp, and crop URL.
* `GET /api/stats` — Overall statistics: total vehicles, revenue, category breakdown, today's totals.
* `GET /api/charts/hourly` — Hourly vehicle counts and revenue distribution for Chart.js.
* `GET /api/rates` — Current toll tariff structure per vehicle class.
* `PUT /api/rates` — Update tariff for a specific vehicle class.

### Reports & Auditing
* `GET /api/reports/shift` — Query vehicle records and revenue totals by Shift (Morning / Evening / Night) or custom date-time window.
* `GET /api/fraud` — Discrepancy records flagged for administrative audit.
* `POST /api/fraud/<id>/resolve` — Mark a flagged anomaly as reviewed or dismissed.

### AI Model Inspector & ANPR Test
* `GET /api/models` — List of available YOLO model weight files in the repository.
* `POST /api/inspect/video` — Upload and process a video clip through a chosen model.
* `POST /api/ocr/test-plate` — Test EasyOCR directly on an uploaded license plate image crop.

---

## ⏰ Shift Timing & Reporting System

Toll plazas and parking facilities operate continuously on a standard 3-shift rotation. The platform calculates analytics across these defined operational shifts:

```text
 ┌─────────────────┬──────────────────────┬───────────────────────────────┐
 │ Shift Name      │ Operational Hours    │ Description                   │
 ├─────────────────┼──────────────────────┼───────────────────────────────┤
 │ Shift 1         │ 06:00 AM – 02:00 PM  │ Morning rush & daytime flow   │
 │ Shift 2         │ 02:00 PM – 10:00 PM  │ Afternoon & evening commute   │
 │ Shift 3         │ 10:00 PM – 06:00 AM  │ Overnight commercial freight  │
 └─────────────────┴──────────────────────┴───────────────────────────────┘
```

The system correctly handles the midnight crossing for Shift 3 (22:00 to 06:00 next day) and allows filtering by custom calendar dates or custom hourly windows.

---

## 🛠️ Troubleshooting & FAQ

#### 1. Why is the camera feed black or showing offline?
* If using a webcam, ensure `CAM1_SOURCE=0` and no other application (Zoom, Skype, etc.) is using the webcam.
* If using an RTSP IP camera, verify network reachability using `ping` or test the stream with `ffplay rtsp://user:pass@camera_ip:554/stream`.
* When no camera is available, the system falls back to processing `traffic.mp4`.

#### 2. How does the database work without MySQL installed?
* `db_adapter.py` automatically detects when MySQL is unreachable and initializes a local SQLite database (`gatepulse.db`). All queries, views, and data storage continue uninterrupted.

#### 3. How to improve OCR plate recognition accuracy?
* Ensure camera angles are positioned at 15°–30° relative to oncoming traffic.
* Ensure adequate night-time illumination or infrared (IR) cameras.
* Higher resolution weights (e.g., `yolov8s.pt` or `yolov8m.pt`) provide sharper ROI crops for EasyOCR.

---

## 📄 License & Credits

* **Core Engine:** Ultralytics YOLOv8 / YOLO11, EasyOCR, OpenCV.
* **Architecture & Implementation:** Smart City & Intelligent Facility Management Platform.
* **License:** Licensed under the MIT License — feel free to use and adapt for commercial or educational purposes.
