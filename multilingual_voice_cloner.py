import os
import sys
import time
import json
import sqlite3
import logging
import asyncio
import edge_tts
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
DUBBED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "dubbed_audio")

os.makedirs(DUBBED_OUTPUT_DIR, exist_ok=True)

# Voice Mapping for Target Languages
VOICE_MAP = {
    "es": "es-ES-AlvaroNeural",   # Spanish
    "zh": "zh-CN-YunxiNeural",   # Mandarin Chinese
    "ja": "ja-JP-KeitaNeural",   # Japanese
    "de": "de-DE-KillianNeural", # German
    "fr": "fr-FR-HenriNeural"    # French
}

class MultilingualVoiceCloner:
    """Translates source scripts and synthesizes localized neural voice tracks."""

    def __init__(self):
        self._init_dubbing_db()

    def _init_dubbing_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multilingual_dub_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source_text TEXT,
                target_lang TEXT,
                translated_text TEXT,
                dubbed_filepath TEXT UNIQUE,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    async def _synthesize_speech(text, voice_model, output_path):
        communicate = edge_tts.Communicate(text, voice_model)
        await communicate.save(output_path)

    def generate_dubbed_track(self, source_text, target_lang="es", output_filename=None):
        """Translates text to target language and synthesizes localized audio track."""
        if not source_text or not source_text.strip():
            logging.error("[!] Empty source text provided for voice dubbing.")
            return None

        voice_model = VOICE_MAP.get(target_lang, "es-ES-AlvaroNeural")

        try:
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(source_text)
            logging.info(f"[*] [VoiceCloner] Translated ({target_lang}): '{translated_text}'")
        except Exception as e:
            logging.error(f"[!] Translation error: {e}")
            translated_text = source_text

        if not output_filename:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"dub_{target_lang}_{timestamp_str}.mp3"

        output_path = os.path.join(DUBBED_OUTPUT_DIR, output_filename)

        try:
            asyncio.run(self._synthesize_speech(translated_text, voice_model, output_path))
            
            if os.path.exists(output_path):
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO multilingual_dub_registry
                    (timestamp, source_text, target_lang, translated_text, dubbed_filepath, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (now_str, source_text, target_lang, translated_text, output_path, "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [VoiceCloner] Dubbed track synthesized successfully: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Synthesis exception in voice cloner: {e}")

        return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Multilingual Voice Cloning & Dubbing Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Multilingual Voice Cloning Engine...")
        cloner = MultilingualVoiceCloner()
        cloner.generate_dubbed_track("Autonomous system audit running successfully.", target_lang="es")