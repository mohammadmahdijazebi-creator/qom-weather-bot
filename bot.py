"""
Telegram & Bale Weather Bot for Qom Province
Handles multi-source forecasting, meteogram generation, synoptic analysis,
and scheduled reporting across Telegram and Bale channels.
"""

import os
import sys
import json
import logging
import subprocess
import requests
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Credentials & Configurations from GitHub Secrets / Env Vars
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
BALE_CHAT_ID = os.getenv("BALE_CHAT_ID")

STATE_FILE = "weather_state.json"
FORECAST_TEXT_FILE = "forecast_text.txt"

# Stations configuration matching meteogram_qom.py
STATIONS = [
    {
        "key": "qom",
        "name_fa": "قم",
        "name_en": "Qom",
        "output": "meteogram_qom.png"
    },
    {
        "key": "kahak",
        "name_fa": "کهک",
        "name_en": "Kahak",
        "output": "meteogram_kahak.png"
    },
    {
        "key": "dastjerd",
        "name_fa": "دستجرد",
        "name_en": "Dastjerd",
        "output": "meteogram_dastjerd.png"
    },
    {
        "key": "salafchegan",
        "name_fa": "سلفچگان",
        "name_en": "Salafchegan",
        "output": "meteogram_salafchegan.png"
    },
    {
        "key": "qahan",
        "name_fa": "قهان",
        "name_en": "Qahan",
        "output": "meteogram_qahan.png"
    }
]


def send_telegram_message(text: str, reply_markup=None):
    """Send text message to Telegram channel/chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set. Skipping Telegram text.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(url, json=payload, timeout=25)
        r.raise_for_status()
        logger.info("Telegram text message sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


def send_bale_message(text: str):
    """Send text message to Bale channel/chat."""
    if not BALE_BOT_TOKEN or not BALE_CHAT_ID:
        logger.warning("Bale credentials not set. Skipping Bale text.")
        return False

    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": BALE_CHAT_ID,
        "text": text
    }

    try:
        r = requests.post(url, json=payload, timeout=25)
        r.raise_for_status()
        logger.info("Bale text message sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Error sending Bale message: {e}")
        return False


def send_media(method: str, media_type: str, file_path: str, caption: str = ""):
    """Send media (photo/document) to both Telegram and Bale."""
    if not os.path.exists(file_path):
        logger.error(f"Media file not found: {file_path}")
        return False

    # 1. Telegram Media Delivery
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
        try:
            with open(file_path, "rb") as f:
                files = {media_type: f}
                data = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                r = requests.post(tg_url, data=data, files=files, timeout=40)
                r.raise_for_status()
                logger.info(f"Telegram media ({file_path}) sent successfully.")
        except Exception as e:
            logger.error(f"Error sending media to Telegram: {e}")

    # 2. Bale Media Delivery
    if BALE_BOT_TOKEN and BALE_CHAT_ID:
        bale_method = "sendPhoto" if media_type == "photo" else "sendDocument"
        bale_url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{bale_method}"
        try:
            with open(file_path, "rb") as f:
                files = {media_type: f}
                data = {
                    "chat_id": BALE_CHAT_ID,
                    "caption": caption
                }
                r = requests.post(bale_url, data=data, files=files, timeout=40)
                r.raise_for_status()
                logger.info(f"Bale media ({file_path}) sent successfully.")
        except Exception as e:
            logger.error(f"Error sending media to Bale: {e}")

    return True


def run_meteogram_generation():
    """Execute meteogram_qom.py script to produce all station meteograms."""
    logger.info("Starting meteogram generation via meteogram_qom.py...")
    try:
        result = subprocess.run(
            [sys.executable, "meteogram_qom.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"meteogram_qom.py stdout:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"meteogram_qom.py failed with code {e.returncode}:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running meteogram_qom.py: {e}")
        return False


def capture_and_send_custom_meteograms():
    """Generate and dispatch multi-station meteograms."""
    success = run_meteogram_generation()
    if not success:
        logger.error("Skipping meteogram dispatch due to generation failure.")
        return

    for target in STATIONS:
        out_file = target["output"]
        name_fa = target["name_fa"]
        name_en = target["name_en"]

        if os.path.exists(out_file):
            caption = (
                f"📊 <b>متئوگرام پیش‌بینی ۱۰ روزه چندمدله ایستگاه {name_fa} ({name_en})</b>\n\n"
                f"🔹 مقایسه ۴ مدل معتبر: ECMWF ،GFS ،ICON و GEM\n"
                f"🔹 پنل ۱: روند دما + بازه انسامبل ECMWF (10-90%)\n"
                f"🔹 پنل ۲: بارش تجمیعی مدل‌ها (میلی‌متر)\n"
                f"🔹 پنل ۳: جهت و سرعت باد ۱۰ متری (گره)\n\n"
                f"کانال هواشناسی استان قم | علی جزبی"
            )
            logger.info(f"Sending meteogram for {name_fa}...")
            # FIXED: parenthesis correctly closed here
            send_media("sendPhoto", "photo", out_file, caption=caption)
        else:
            logger.warning(f"Meteogram output file not found: {out_file}")


def send_forecast_text_if_available():
    """Send text forecast if forecast_text.txt is available."""
    if os.path.exists(FORECAST_TEXT_FILE):
        try:
            with open(FORECAST_TEXT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                logger.info("Sending forecast bulletin text...")
                send_telegram_message(content)
                send_bale_message(content)
        except Exception as e:
            logger.error(f"Error reading {FORECAST_TEXT_FILE}: {e}")


def main():
    logger.info("=== Starting Qom Weather Bot Run ===")
    
    # 1. Dispatch multi-model meteograms for all stations
    capture_and_send_custom_meteograms()

    # 2. Dispatch forecast bulletin if available
    send_forecast_text_if_available()

    logger.info("=== Bot Run Completed Successfully ===")


if __name__ == "__main__":
    main()
