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
SUBTITLES_DIR = os.path.join(BASE_DIR, "outputs", "subtitles")

os.makedirs(SUBTITLES_DIR, exist_ok=True)

class AutoCaptionGenerator:
    """Generates timed SRT subtitle tracks and burns structured captions onto video files."""

    def __init__(self):
        self._init_caption_db()

    def _init_caption_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caption_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                video_filename TEXT UNIQUE,
                srt_filepath TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def generate_dummy_srt(text_content, duration_sec, output_srt_path):
        """Generates a timed SRT file based on text line split and audio duration."""
        words = text_content.split()
        if not words:
            words = ["System", "Audit", "Sequence", "Active"]

        chunk_size = max(1, len(words) // 3)
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        
        time_per_chunk = duration_sec / max(1, len(chunks))

        srt_lines = []
        for idx, chunk in enumerate(chunks):
            start_time = idx * time_per_chunk
            end_time = (idx + 1) * time_per_chunk

            start_str = time.strftime('%H:%M:%S,000', time.gmtime(start_time))
            end_str = time.strftime('%H:%M:%S,000', time.gmtime(end_time))

            srt_lines.append(f"{idx + 1}\n{start_str} --> {end_str}\n{chunk}\n")

        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        logging.info(f"[+] [CaptionGenerator] Timed SRT generated: '{output_srt_path}'")
        return output_srt_path

    @staticmethod
    def burn_subtitles_to_video(video_path, srt_path, output_video_path):
        """Uses FFmpeg to burn subtitles directly onto the video stream."""
        if not os.path.exists(video_path) or not os.path.exists(srt_path):
            logging.error("[!] Video or SRT path missing for subtitle burn-in.")
            return None

        srt_path_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        filter_arg = f"subtitles='{srt_path_escaped}':force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3'"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", filter_arg,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            output_video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_video_path):
                logging.info(f"[+] [CaptionGenerator] Subtitles burned successfully: '{output_video_path}'")
                return output_video_path
            else:
                logging.warning(f"[!] Subtitle burn-in fallback: {result.stderr[:200]}")
                return video_path
        except Exception as e:
            logging.error(f"[!] Subtitle burn-in exception: {e}")
            return video_path

if __name__ == "__main__":
    logging.info("[*] Testing Automated Caption & Subtitle Generator Engine...")
    test_srt = os.path.join(SUBTITLES_DIR, "test_subtitles.srt")
    AutoCaptionGenerator.generate_dummy_srt("Master system audit sequence running across all cores.", 6.0, test_srt)