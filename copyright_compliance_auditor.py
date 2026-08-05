import os
import sys
import time
import json
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
AUDIT_LOG_FILE = os.path.join(BASE_DIR, "compliance_audit_log.json")

class CopyrightComplianceAuditor:
    """Audits video and audio assets for copyright compliance, watermarks, and licensing tags."""

    def __init__(self):
        self._init_audit_db()

    def _init_audit_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_audit_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT UNIQUE,
                filepath TEXT,
                compliance_score REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def inspect_file_compliance(filepath):
        """Inspects metadata tags and flags potentially non-compliant media assets."""
        if not os.path.exists(filepath):
            return 0.0, "FILE_NOT_FOUND"

        score = 100.0
        status = "PASSED"

        # Check file extension and metadata via ffprobe
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                meta = json.loads(result.stdout)
                tags = meta.get("format", {}).get("tags", {})
                
                # Check for restrictive copyright tags
                copyright_tag = str(tags.get("copyright", "")).lower()
                if "all rights reserved" in copyright_tag or "protected" in copyright_tag:
                    score -= 50.0
                    status = "WARNING_RESTRICTED"
        except Exception as e:
            logging.warning(f"[!] Metadata probe error for {filepath}: {e}")

        return score, status

    def audit_all_assets(self):
        """Scans all registered database assets and records audit reports."""
        if not os.path.exists(DB_PATH):
            logging.warning("[!] Database not found. Skipping compliance audit.")
            return 0

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, filepath FROM assets")
        records = cursor.fetchall()
        conn.close()

        audited_count = 0
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        audit_results = []
        for filename, filepath in records:
            if filepath and os.path.exists(filepath):
                score, status = self.inspect_file_compliance(filepath)
                cursor.execute('''
                    INSERT OR REPLACE INTO compliance_audit_registry (timestamp, filename, filepath, compliance_score, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now_str, filename, filepath, score, status))
                
                audit_results.append({
                    "filename": filename,
                    "filepath": filepath,
                    "compliance_score": score,
                    "status": status,
                    "audited_at": now_str
                })
                audited_count += 1

        conn.commit()
        conn.close()

        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(audit_results, f, indent=4)

        logging.info(f"[+] [ComplianceAuditor] Audit complete. Total Assets Scanned: {audited_count}")
        return audited_count

if __name__ == "__main__":
    logging.info("[*] Testing Copyright & Compliance Audit Engine...")
    auditor = CopyrightComplianceAuditor()
    auditor.audit_all_assets()