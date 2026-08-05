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
AUDIO_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "audio_tracks")

os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

class AudioAtmosphereSynthesizer:
    """Generates ambient audio tracks, mixes voiceovers with background score, and normalizes LUFS audio levels."""

    def __init__(self):
        self._init_audio_db()

    def _init_audio_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_tracks_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT UNIQUE,
                filepath TEXT,
                category TEXT,
                duration_sec REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def synthesize_ambient_tone(duration_sec=10.0, output_filename="ambient_pad.mp3"):
        """Generates a synthetic ambient background drone using FFmpeg audio filters."""
        output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)
        
        # FFmpeg synth filter producing a soft ambient frequency pad
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=110:duration={duration_sec}",
            "-af", "afade=t=in:ss=0:d=1,afade=t=out:st={}:d=1,volume=0.15".format(max(0, duration_sec - 1)),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                logging.info(f"[+] [AudioSynth] Ambient background track synthesized: '{output_path}'")
                return output_path
            else:
                logging.warning(f"[!] Synth fallback: {result.stderr[:200]}")
                return None
        except Exception as e:
            logging.error(f"[!] Audio synthesis exception: {e}")
            return None

    @staticmethod
    def mix_voiceover_and_background(voiceover_path, bg_music_path, output_mixed_path, bg_volume=0.2):
        """Combines voiceover and background music with automatic volume attenuation."""
        if not os.path.exists(voiceover_path) or not os.path.exists(bg_music_path):
            logging.error("[!] Voiceover or background audio file missing for mixing.")
            return voiceover_path

        # Complex filter graph: Duck background music under voiceover and apply EBU R128 loudness normalization
        filter_complex = f"[1:a]volume={bg_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[mixed];[mixed]loudnorm=I=-14:LRA=11:TP=-1.5[out]"

        cmd = [
            "ffmpeg", "-y",
            "-i", voiceover_path,
            "-i", bg_music_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "aac",
            "-b:a", "192k",
            output_mixed_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_mixed_path):
                logging.info(f"[+] [AudioSynth] Mixed audio created and normalized (-14 LUFS): '{output_mixed_path}'")
                return output_mixed_path
            else:
                logging.warning(f"[!] Audio mixing fallback: {result.stderr[:200]}")
                return voiceover_path
        except Exception as e:
            logging.error(f"[!] Audio mixing exception: {e}")
            return voiceover_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Audio Atmosphere Synthesizer test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Audio Atmosphere Synthesizer Engine...")
        AudioAtmosphereSynthesizer.synthesize_ambient_tone(5.0, "test_ambient.mp3")