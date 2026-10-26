#!/usr/bin/env python3
"""License Plate Recognition (ANPR / ALPR) Engine"""

import os
import re
import cv2
import numpy as np
import logging

logger = logging.getLogger('ANPREngine')

import sys
import site

# Ensure local venv site-packages are accessible even when run via Anaconda / system Python
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for vp in [
    os.path.join(ROOT_DIR, 'venv', 'lib', f'python3.{sys.version_info.minor}', 'site-packages'),
    os.path.join(ROOT_DIR, 'python', 'venv', 'lib', f'python3.{sys.version_info.minor}', 'site-packages'),
    os.path.join(ROOT_DIR, 'venv', 'lib', 'python3.14', 'site-packages'),
]:
    if os.path.exists(vp):
        site.addsitedir(vp)

# Try importing EasyOCR
try:
    import easyocr
    EASYOCR_INSTALLED = True
    logger.info(f"EasyOCR successfully loaded from: {easyocr.__file__}")
except ImportError:
    easyocr = None
    EASYOCR_INSTALLED = False

# Bengali to English digit translation map
BN_TO_EN_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

# Bengali to English district / metro transliteration map
BN_METRO_MAP = {
    'ঢাকা': 'Dhaka',
    'মেট্রো': 'Metro',
    'মেট্রো': 'Metro',
    'চট্টগ্রাম': 'Chatt',
    'চট্ট': 'Chatt',
    'সিলেট': 'Sylhet',
    'রাজশাহী': 'Rajshahi',
    'খুলনা': 'Khulna',
    'বরিশাল': 'Barishal',
    'রংপুর': 'Rangpur',
    'ময়মনসিংহ': 'Mymensingh',
    'ময়মন': 'Mymensingh',
    'গাজীপুর': 'Gazipur',
    'কুমিল্লা': 'Cumilla',
    'নারায়ণগঞ্জ': 'Narayanganj',
    'নারায়ণ': 'Narayanganj',
    'যশোর': 'Jashore',
    'বগুড়া': 'Bogura',
    'পাবনা': 'Pabna',
    'ফরিদপুর': 'Faridpur',
    'টাঙ্গাইল': 'Tangail',
    'দিনাজপুর': 'Dinajpur',
    'নোয়াখালী': 'Noakhali',
    'ফেনী': 'Feni',
    'কক্সবাজার': 'Coxsbazar',
}

# Bengali to English vehicle registration series letters
BN_SERIES_MAP = {
    'ক': 'Ka', 'খ': 'Kha', 'গ': 'Ga', 'ঘ': 'Gha', 'ঙ': 'Nga',
    'চ': 'Cha', 'ছ': 'Chha', 'জ': 'Ja', 'ঝ': 'Jha',
    'ট': 'Ta', 'ঠ': 'Tha', 'ড': 'Da', 'ঢ': 'Dha',
    'ত': 'Ta', 'থ': 'Tha', 'দ': 'Da', 'ধ': 'Dha', 'ন': 'Na',
    'প': 'Pa', 'ফ': 'Pha', 'ব': 'Ba', 'ভ': 'Bha', 'ম': 'Ma',
    'য': 'Ya', 'র': 'Ra', 'ল': 'La', 'শ': 'Sha', 'ষ': 'Sha', 'স': 'Sa', 'হ': 'Ha',
    'ড': 'Da', 'ঢ': 'Dha', 'ড়': 'Rra', 'ঢ়': 'Rha', 'য়': 'Ya'
}

def convert_bengali_digits(text: str) -> str:
    """Translate Bengali numerals (০-৯) to Arabic numerals (0-9)."""
    for bn, en in BN_TO_EN_DIGITS.items():
        text = text.replace(bn, en)
    return text

def convert_bengali_text(text: str) -> str:
    """Translate Bengali district/metro and series tokens to English standard."""
    converted = text
    for bn, en in BN_METRO_MAP.items():
        converted = re.sub(r'\b' + re.escape(bn) + r'\b', en, converted)
        converted = converted.replace(bn, en)

    for bn, en in BN_SERIES_MAP.items():
        converted = re.sub(r'(?<=[-\s])' + re.escape(bn) + r'(?=[-\s\d]|$)', en, converted)
        converted = converted.replace(bn, en)

    return converted

def enhance_plate_image(roi: np.ndarray) -> list[np.ndarray]:
    """
    Produce a set of enhanced candidate images for OCR:
    1. Grayscale + CLAHE (Contrast-Limited Adaptive Histogram Equalization)
    2. Sharpened high-contrast grayscale
    3. Adaptive threshold binary (black-on-white text)
    """
    candidates = []
    if roi is None or roi.size == 0:
        return candidates

    h, w = roi.shape[:2]
    # Resize up if plate is small
    target_h = 100
    if h < target_h:
        scale = target_h / float(h)
        roi = cv2.resize(roi, (int(w * scale), target_h), interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi.copy()

    # Candidate 1: Bilateral filter + CLAHE
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced_clahe = clahe.apply(denoised)
    candidates.append(enhanced_clahe)

    # Candidate 2: Sharpened
    kernel_sharpen = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]], dtype=np.float32)
    sharpened = cv2.filter2D(enhanced_clahe, -1, kernel_sharpen)
    candidates.append(sharpened)

    # Candidate 3: Morphological contrast
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT, kernel)
    blackhat = cv2.morphologyEx(denoised, cv2.MORPH_BLACKHAT, kernel)
    morph_enhanced = cv2.add(cv2.subtract(denoised, blackhat), tophat)
    candidates.append(morph_enhanced)

    return candidates

def format_bangladeshi_plate(raw_lines: list[str]) -> tuple[str, float]:
    """
    Combines detected OCR text lines and standardizes into BRTA format:
    Example: 'Dhaka Metro-Ga 11-2345'
    """
    joined = ' '.join(raw_lines)
    # Convert numerals
    converted = convert_bengali_digits(joined)
    # Convert Bengali words
    converted = convert_bengali_text(converted)

    # Clean punctuation, keep alphanumeric, hyphen, space
    cleaned = re.sub(r'[^a-zA-Z0-9\s\-]', ' ', converted)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Look for patterns: District Metro Series XX-XXXX
    # e.g., Dhaka Metro Ga 11 2345 or DHAKA METRO-GA 11-2345
    tokens = cleaned.split()
    if not tokens:
        return ('', 0.0)

    # Extract digits
    digits = [t for t in tokens if re.search(r'\d', t)]
    all_digits_str = ''.join(re.findall(r'\d+', ' '.join(digits)))

    # Detect district
    metro_name = "Dhaka Metro"
    for d in ["Chatt", "Sylhet", "Rajshahi", "Khulna", "Barishal", "Rangpur", "Cumilla", "Gazipur"]:
        if any(d.lower() in t.lower() for t in tokens):
            metro_name = f"{d} Metro"
            break

    # Detect series letter (Ka, Kha, Ga, Gha, Cha, La, etc.)
    series_candidates = ['Ga', 'Gha', 'Ka', 'Kha', 'Cha', 'Chha', 'Ja', 'Ta', 'Tha', 'Da', 'Na', 'Pa', 'Ba', 'Ma', 'La', 'Ha']
    chosen_series = 'Ga'
    for sc in series_candidates:
        if any(sc.lower() == t.lower() for t in tokens):
            chosen_series = sc
            break

    # Format digits: normally 2 digits series-num and 4 digits vehicle-num
    if len(all_digits_str) >= 6:
        n1 = all_digits_str[:2]
        n2 = all_digits_str[2:6]
        formatted = f"{metro_name}-{chosen_series} {n1}-{n2}"
        return (formatted, 92.0)
    elif len(all_digits_str) >= 4:
        n = all_digits_str[-4:]
        formatted = f"{metro_name}-{chosen_series} 11-{n}"
        return (formatted, 82.0)
    elif len(cleaned) >= 5:
        # Fallback to cleaned uppercase string
        return (cleaned.upper()[:22], 75.0)

    return (cleaned.upper(), 50.0)

class BangladeshiANPR:
    def __init__(self, languages=['en', 'bn'], use_gpu=False):
        self.reader = None
        self.available = False
        if EASYOCR_INSTALLED:
            try:
                # Initialize EasyOCR with English and Bengali
                self.reader = easyocr.Reader(languages, gpu=use_gpu, verbose=False)
                self.available = True
                logger.info("EasyOCR initialized successfully with languages: %s", languages)
            except Exception as e:
                # Fallback to English only if Bengali model fails to load
                try:
                    self.reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False)
                    self.available = True
                    logger.info("EasyOCR fallback to English only: %s", e)
                except Exception as ex:
                    logger.warning("Could not initialize EasyOCR: %s", ex)

    def extract_plate_region(self, frame: np.ndarray, bbox) -> np.ndarray | None:
        """Locates the probable license plate region from vehicle bounding box."""
        if frame is None or bbox is None:
            return None
        x1, y1, x2, y2 = map(int, bbox)
        vh = y2 - y1
        vw = x2 - x1
        if vh <= 0 or vw <= 0:
            return None

        # Lower 35% of vehicle body
        py1 = max(0, y1 + int(vh * 0.62))
        py2 = min(frame.shape[0], y2)
        # Margin
        margin = int(vw * 0.08)
        px1 = max(0, x1 + margin)
        px2 = min(frame.shape[1], x2 - margin)

        roi = frame[py1:py2, px1:px2]
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 20:
            return None
        return roi

    def recognize_plate(self, plate_roi: np.ndarray) -> dict:
        """
        Runs multi-pass OCR on license plate ROI and returns structured result.
        """
        if plate_roi is None or plate_roi.size == 0:
            return {
                'success': False,
                'plate_number': '',
                'confidence': 0.0,
                'raw_text': ''
            }

        if not self.available or self.reader is None:
            return {
                'success': False,
                'plate_number': '',
                'confidence': 0.0,
                'raw_text': 'OCR_UNAVAILABLE'
            }

        candidates = enhance_plate_image(plate_roi)
        best_plate = ""
        best_conf = 0.0
        best_raw = ""

        for candidate in candidates:
            try:
                results = self.reader.readtext(candidate, detail=1, paragraph=False)
                if not results:
                    continue

                # Sort detections vertically (top to bottom)
                sorted_results = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
                raw_lines = [r[1] for r in sorted_results if r[1].strip()]
                conf_scores = [float(r[2]) for r in sorted_results]
                avg_score = (sum(conf_scores) / len(conf_scores) * 100) if conf_scores else 0.0

                formatted_plate, format_conf = format_bangladeshi_plate(raw_lines)
                combined_conf = round(avg_score * 0.6 + format_conf * 0.4, 2)

                if combined_conf > best_conf and len(formatted_plate) >= 4:
                    best_conf = combined_conf
                    best_plate = formatted_plate
                    best_raw = ' | '.join(raw_lines)

                # Stop early if very confident
                if best_conf >= 90.0:
                    break
            except Exception as e:
                logger.debug(f"OCR pass error: {e}")

        return {
            'success': bool(best_plate),
            'plate_number': best_plate,
            'confidence': best_conf,
            'raw_text': best_raw
        }

# Global singleton ANPR instance
anpr_instance = None

def get_anpr_engine() -> BangladeshiANPR:
    global anpr_instance
    if anpr_instance is None:
        anpr_instance = BangladeshiANPR()
    return anpr_instance
