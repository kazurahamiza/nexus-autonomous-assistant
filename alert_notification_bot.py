import os
import sys
import time
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure Webhook URL via environment variable or default
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

class AlertNotificationEngine:
    """Dispatches real-time push notifications for system errors, renders, and security events."""

    @staticmethod
    def send_alert(title, message, level="INFO"):
        """Sends a structured payload to the target notification webhook."""
        if not WEBHOOK_URL:
            logging.info(f"[*] [AlertBot] [{level}] {title}: {message} (Webhook URL not set, logged locally)")
            return False

        color_map = {
            "INFO": 3447003,      # Blue
            "SUCCESS": 3066993,   # Green
            "WARNING": 16776960,  # Yellow
            "CRITICAL": 15158332  # Red
        }

        payload = {
            "embeds": [{
                "title": f"⚡ Apex AI Alert: {title}",
                "description": message,
                "color": color_map.get(level, 3447003),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }]
        }

        try:
            res = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if res.status_code in (200, 204):
                logging.info(f"[+] [AlertBot] Notification sent successfully: '{title}'")
                return True
            else:
                logging.warning(f"[!] [AlertBot] Webhook delivery failed (HTTP {res.status_code})")
        except Exception as e:
            logging.error(f"[!] [AlertBot] Exception sending alert: {e}")
        return False

    @staticmethod
    def notify_render_complete(video_filename, duration_sec):
        return AlertNotificationEngine.send_alert(
            title="Video Render Completed",
            message=f"File: `{video_filename}`\nDuration: {duration_sec}s\nStatus: Ready for Publishing",
            level="SUCCESS"
        )

    @staticmethod
    def notify_security_anomaly(filename):
        return AlertNotificationEngine.send_alert(
            title="SECURITY INTEGRITY ALERT",
            message=f"Unauthorized file modification detected in core file: `{filename}`",
            level="CRITICAL"
        )

if __name__ == "__main__":
    logging.info("[*] Testing Alert Notification Engine...")
    AlertNotificationEngine.send_alert("System Startup", "Alert Notification Bot engine online.", level="INFO")